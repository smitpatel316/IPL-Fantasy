"""Playoff picture + remaining strength of schedule (P5-W22).

GET /api/leagues/{id}/playoff-picture is a DESCRIPTIVE projection —
current record + remaining fixtures only. No win probability, no
projected points, no simulation: nothing here pretends to know how
the remaining games will go.

  * Seeds/records come from regular-season finals (weeks 1–6) in the
    dashboard standings order (P4-W27 key: wins, losses, ties, PF,
    name).
  * games_back is measured from the 4th (last playoff) seed with the
    standard standings formula ((W4-W) + (L-L4)) / 2 — negative means
    the team is ahead of the playoff line.
  * Remaining opponents are the not-yet-final regular-season matchup
    rows (weeks 1–6); remaining_sos is the MEAN of those opponents'
    current standings-points shares, where a team's standings points
    are 2W + T and its share is points / league total points (0 when
    no games are final yet or no games remain).

P5-W34 adds deterministic clinch math on the same bounds: a team's
final standings points lie in [pts, pts + 2*remaining] (2 per win,
1 per tie). A rival who can merely TIE a team's worst case could
still pass it on tiebreakers while either side has games left, so
a live tied bound counts as "can pass" — tied bounds never clinch
or eliminate. The one exception is a tie between two teams with
no games left: their records are final, so the projection's own
seed order settles them definitively.

  * clinched — at most 3 rivals can pass the team's min (current
    points): max > min, or max == min in a live tie (above).
  * eliminated — at least 4 rivals are guaranteed ahead of the
    team's max: min > max, or min == max between two finished
    teams with the rival seeded higher.
  * otherwise in contention.
  * magic number (in-contention teams only) — the smallest added
    standings points M with at most 3 rivals at max >= pts + M,
    i.e. M = (4th-highest rival max) + 1 - pts; null when even
    winning out (M > 2*remaining) cannot supply it on bounds alone.

Bounds arithmetic only, exactly like the rest of this projection:
no win probability, no simulation, no projected points.
"""

import sqlite3

from fastapi import APIRouter, Depends

from .. import schemas
from ..database import get_db
from . import get_league

router = APIRouter()

REGULAR_SEASON_LAST_WEEK = 6
PLAYOFF_TEAMS = 4


def _records(con: sqlite3.Connection, league_id: int) -> list[dict]:
    out = []
    for t in con.execute(
            "SELECT id, name FROM teams WHERE league_id = ?", (league_id,)):
        w = con.execute(
            """SELECT
                 SUM(CASE WHEN (team_a_id = ? AND score_a > score_b) OR (team_b_id = ? AND score_b > score_a) THEN 1 ELSE 0 END),
                 SUM(CASE WHEN (team_a_id = ? AND score_a < score_b) OR (team_b_id = ? AND score_b < score_a) THEN 1 ELSE 0 END),
                 SUM(CASE WHEN score_a = score_b AND (team_a_id = ? OR team_b_id = ?) THEN 1 ELSE 0 END),
                 SUM(CASE WHEN team_a_id = ? THEN score_a WHEN team_b_id = ? THEN score_b ELSE 0 END)
               FROM matchups
               WHERE league_id = ? AND status = 'final' AND week_no <= ?""",
            (t["id"],) * 8 + (league_id, REGULAR_SEASON_LAST_WEEK)).fetchone()
        out.append({
            "team_id": t["id"], "team_name": t["name"],
            "wins": w[0] or 0, "losses": w[1] or 0, "ties": w[2] or 0,
            "points_for": w[3] or 0.0,
        })
    out.sort(key=lambda r: (-r["wins"], r["losses"], -r["ties"],
                            -r["points_for"], r["team_name"].casefold(),
                            r["team_id"]))
    return out


@router.get("/{league_id}/playoff-picture",
            response_model=schemas.PlayoffPictureOut)
def get_playoff_picture(league_id: int,
                        con: sqlite3.Connection = Depends(get_db)):
    get_league(con, league_id)  # 404 if missing
    records = _records(con, league_id)
    names = {r["team_id"]: r["team_name"] for r in records}

    through_week = con.execute(
        "SELECT MAX(week_no) FROM matchups WHERE league_id = ?"
        " AND status = 'final' AND week_no <= ?",
        (league_id, REGULAR_SEASON_LAST_WEEK)).fetchone()[0] or 0
    remaining_rows = con.execute(
        "SELECT * FROM matchups WHERE league_id = ? AND status != 'final'"
        " AND week_no <= ? ORDER BY week_no, id",
        (league_id, REGULAR_SEASON_LAST_WEEK)).fetchall()
    rs_complete = bool(records) and not remaining_rows and through_week > 0 \
        and con.execute(
            "SELECT COUNT(*) FROM matchups WHERE league_id = ? AND week_no = ?",
            (league_id, REGULAR_SEASON_LAST_WEEK)).fetchone()[0] > 0

    total_points = sum(2 * r["wins"] + r["ties"] for r in records)
    share = {
        r["team_id"]: ((2 * r["wins"] + r["ties"]) / total_points
                       if total_points else 0.0)
        for r in records
    }

    remaining: dict[int, list[schemas.RemainingOpponentOut]] = {
        r["team_id"]: [] for r in records}
    for m in remaining_rows:
        for tid, oid in ((m["team_a_id"], m["team_b_id"]),
                         (m["team_b_id"], m["team_a_id"])):
            if tid in remaining:
                remaining[tid].append(schemas.RemainingOpponentOut(
                    week_no=m["week_no"], opponent_team_id=oid,
                    opponent_team_name=names.get(oid, f"Team {oid}")))

    # P5-W34 bounds: standings points (2W+T) and each team's
    # best/worst final totals from its remaining games.
    pts = {r["team_id"]: 2 * r["wins"] + r["ties"] for r in records}
    max_pts = {r["team_id"]: pts[r["team_id"]] + 2 * len(remaining[r["team_id"]])
               for r in records}

    seed_of = {r["team_id"]: i for i, r in enumerate(records)}
    rem_of = {r["team_id"]: len(remaining[r["team_id"]]) for r in records}

    def clinch(team_id: int) -> tuple[str, int | None]:
        rivals = [t for t in pts if t != team_id]

        def can_pass(t: int) -> bool:
            if max_pts[t] > pts[team_id]:
                return True
            if max_pts[t] < pts[team_id]:
                return False
            # Tied bound: a live tie can still flip on tiebreakers;
            # a tie between two finished teams is settled by seeds.
            return not (rem_of[t] == 0 and rem_of[team_id] == 0
                        and seed_of[team_id] < seed_of[t])

        def locked_ahead(t: int) -> bool:
            if pts[t] > max_pts[team_id]:
                return True
            if pts[t] < max_pts[team_id]:
                return False
            return (rem_of[t] == 0 and rem_of[team_id] == 0
                    and seed_of[t] < seed_of[team_id])

        if sum(1 for t in rivals if can_pass(t)) <= PLAYOFF_TEAMS - 1:
            return "clinched", None
        if sum(1 for t in rivals if locked_ahead(t)) >= PLAYOFF_TEAMS:
            return "eliminated", None
        magic = None
        if len(rivals) >= PLAYOFF_TEAMS:
            fourth_max = sorted((max_pts[t] for t in rivals),
                                reverse=True)[PLAYOFF_TEAMS - 1]
            need = fourth_max + 1 - pts[team_id]
            if 1 <= need <= 2 * len(remaining[team_id]):
                magic = need
        return "in_contention", magic

    fourth = records[PLAYOFF_TEAMS - 1] if len(records) >= PLAYOFF_TEAMS else None
    entries = []
    for i, r in enumerate(records):
        gb = None
        if fourth is not None:
            gb = ((fourth["wins"] - r["wins"])
                  + (r["losses"] - fourth["losses"])) / 2
        opps = remaining[r["team_id"]]
        sos = (round(sum(share[o.opponent_team_id] for o in opps) / len(opps), 4)
               if opps else 0.0)
        status, magic = clinch(r["team_id"])
        entries.append(schemas.PlayoffPictureEntryOut(
            seed=i + 1, team_id=r["team_id"], team_name=r["team_name"],
            wins=r["wins"], losses=r["losses"], ties=r["ties"],
            points_for=r["points_for"], games_back=gb,
            remaining_games=len(opps), remaining_opponents=opps,
            remaining_sos=sos, clinch_status=status, magic_number=magic))

    return schemas.PlayoffPictureOut(
        league_id=league_id, through_week=through_week,
        regular_season_complete=rs_complete, entries=entries)
