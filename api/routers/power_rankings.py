"""Power rankings (P5-W9): deterministic weekly power-rank list.

Computed server-side from data already in the DB — no new scoring
model, no engine changes.

Formula (fixed; same DB state -> same ranking):
  * Player value comes from consensus pre_draft_ranks (MIN rank over
    the league's teams, the P5-W4 convention): with N ranked players,
    value = N + 1 - rank; unranked players are worth 0.
  * roster_value = sum of values over the team's 11 starters: the
    saved week-1 lineup's non-BN/IL slots when one exists, else the
    roster's top 11 by value.
  * Pre-season (no final matchups): rank by roster_value alone, and
    the response says so (basis="roster_value") — no fabricated
    points, no record.
  * Once weeks finalize (basis="record_blend"): power_score =
    standings points (2 per win, 1 per tie) + points-for share
    (team PF / league PF, in [0,1)), so the record dominates and PF
    share orders teams level on standings points. Ties in score fall
    back to PF, then team name, then team id — fully deterministic.
  * movement (rank change vs the previous computed week) is reported
    only once two final weeks exist: the previous ranking is the same
    blend computed through week-1.
"""

import sqlite3

from fastapi import APIRouter, Depends

from .. import schemas
from ..database import get_db
from . import get_league

router = APIRouter()

STARTER_SLOTS_EXCLUDED = ("BN", "IL")


def _roster_values(con: sqlite3.Connection, league_id: int,
                   season: str) -> dict[int, int]:
    ranks = {
        r["player_id"]: r["rank"]
        for r in con.execute(
            """SELECT r.player_id, MIN(r.rank) AS rank
               FROM pre_draft_ranks r JOIN teams t ON t.id = r.team_id
               WHERE t.league_id = ? GROUP BY r.player_id""", (league_id,))
    }
    pool = len(ranks)

    def value(pid: int) -> int:
        return pool + 1 - ranks[pid] if pid in ranks else 0

    out: dict[int, int] = {}
    for t in con.execute("SELECT id FROM teams WHERE league_id = ?",
                         (league_id,)):
        tid = t["id"]
        starters = [
            r["player_id"] for r in con.execute(
                """SELECT player_id FROM roster_slots
                   WHERE team_id = ? AND week_no = 1 AND slot NOT IN ('BN', 'IL')""",
                (tid,))
        ]
        if not starters:
            roster = [
                r["player_id"] for r in con.execute(
                    "SELECT player_id FROM roster_slots"
                    " WHERE team_id = ? AND week_no IS NULL", (tid,))
            ]
            starters = sorted(roster, key=lambda p: -value(p))[:11]
        out[tid] = sum(value(p) for p in starters)
    return out


def _records(con: sqlite3.Connection, league_id: int,
             through_week: int) -> dict[int, dict]:
    """team_id -> {wins, losses, ties, points_for} over final matchups
    with week_no <= through_week."""
    rec: dict[int, dict] = {
        t["id"]: {"wins": 0, "losses": 0, "ties": 0, "points_for": 0.0}
        for t in con.execute("SELECT id FROM teams WHERE league_id = ?",
                             (league_id,))
    }
    for m in con.execute(
            """SELECT team_a_id, team_b_id, score_a, score_b FROM matchups
               WHERE league_id = ? AND status = 'final' AND week_no <= ?""",
            (league_id, through_week)):
        a, b = rec.get(m["team_a_id"]), rec.get(m["team_b_id"])
        if a is None or b is None:
            continue
        a["points_for"] += m["score_a"] or 0.0
        b["points_for"] += m["score_b"] or 0.0
        if m["score_a"] > m["score_b"]:
            a["wins"] += 1
            b["losses"] += 1
        elif m["score_b"] > m["score_a"]:
            b["wins"] += 1
            a["losses"] += 1
        else:
            a["ties"] += 1
            b["ties"] += 1
    return rec


def _rank(con: sqlite3.Connection, league_id: int,
          values: dict[int, int], through_week: int) -> list[dict]:
    teams = {t["id"]: t["name"] for t in con.execute(
        "SELECT id, name FROM teams WHERE league_id = ?", (league_id,))}
    if through_week <= 0:
        rows = [
            {"team_id": tid, "team_name": name,
             "roster_value": values.get(tid, 0), "wins": 0, "losses": 0,
             "ties": 0, "points_for": 0.0,
             "power_score": float(values.get(tid, 0))}
            for tid, name in teams.items()
        ]
        rows.sort(key=lambda r: (-r["power_score"],
                                 r["team_name"].casefold(), r["team_id"]))
        return rows
    rec = _records(con, league_id, through_week)
    total_pf = sum(r["points_for"] for r in rec.values())
    rows = []
    for tid, name in teams.items():
        r = rec[tid]
        share = r["points_for"] / total_pf if total_pf > 0 else 0.0
        score = 2 * r["wins"] + r["ties"] + share
        rows.append(
            {"team_id": tid, "team_name": name,
             "roster_value": values.get(tid, 0), "wins": r["wins"],
             "losses": r["losses"], "ties": r["ties"],
             "points_for": round(r["points_for"], 1),
             "power_score": round(score, 4)})
    rows.sort(key=lambda r: (-r["power_score"], -r["points_for"],
                             r["team_name"].casefold(), r["team_id"]))
    return rows


@router.get("/{league_id}/power-rankings",
            response_model=schemas.PowerRankingsOut)
def get_power_rankings(league_id: int,
                       con: sqlite3.Connection = Depends(get_db)):
    league = get_league(con, league_id)  # 404 if missing
    values = _roster_values(con, league_id, league["season"])
    row = con.execute(
        "SELECT MAX(week_no) AS w FROM matchups"
        " WHERE league_id = ? AND status = 'final'", (league_id,)).fetchone()
    through_week = row["w"] or 0
    ranked = _rank(con, league_id, values, through_week)
    prev_rank: dict[int, int] = {}
    if through_week >= 2:
        prev = _rank(con, league_id, values, through_week - 1)
        prev_rank = {r["team_id"]: i + 1 for i, r in enumerate(prev)}
    entries = [
        schemas.PowerRankEntryOut(
            rank=i + 1, team_id=r["team_id"], team_name=r["team_name"],
            roster_value=r["roster_value"], wins=r["wins"],
            losses=r["losses"], ties=r["ties"],
            points_for=r["points_for"], power_score=r["power_score"],
            movement=(prev_rank[r["team_id"]] - (i + 1))
            if r["team_id"] in prev_rank else None)
        for i, r in enumerate(ranked)
    ]
    return schemas.PowerRankingsOut(
        league_id=league_id,
        basis="record_blend" if through_week > 0 else "roster_value",
        through_week=through_week, entries=entries)
