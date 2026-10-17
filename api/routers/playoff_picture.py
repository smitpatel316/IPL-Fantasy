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
        entries.append(schemas.PlayoffPictureEntryOut(
            seed=i + 1, team_id=r["team_id"], team_name=r["team_name"],
            wins=r["wins"], losses=r["losses"], ties=r["ties"],
            points_for=r["points_for"], games_back=gb,
            remaining_games=len(opps), remaining_opponents=opps,
            remaining_sos=sos))

    return schemas.PlayoffPictureOut(
        league_id=league_id, through_week=through_week,
        regular_season_complete=rs_complete, entries=entries)
