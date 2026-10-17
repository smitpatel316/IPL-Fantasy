"""Matchup preview (P5-W26): descriptive week preview.

GET /api/leagues/{id}/matchups/preview?week_no=N returns, for every
not-yet-final matchup that week, per side: the saved/carried lineup's
starter preseason-rank value total (P5-W4/W9 convention: value =
pool + 1 - consensus rank, unranked = 0), the week's game count summed
from schedule-nudges over the starters' IPL teams, availability flags
on starters (P5-W6), and the pair's prior head-to-head final result
when one exists. DESCRIPTIVE ONLY — no win probability, no projected
points, no simulation, in payload or copy. Final matchups are omitted
(their result state already renders on the matchup page). Read-only.
"""

import sqlite3

from fastapi import APIRouter, Depends, Query

from .. import schedule_games, schemas
from ..constants import TOTAL_WEEKS
from ..database import get_db
from . import availability_from_status, get_league

router = APIRouter()

STARTER_SLOTS = ("WK", "BAT", "AR", "BOWL", "UTIL")


def _starters(con, team_id: int, week_no: int) -> list[int] | None:
    """Starter player ids from the saved week lineup, else the most
    recent earlier saved week carried forward (P4-W5 seam, filtered to
    players still rostered). None when no lineup exists at all."""
    def slots_for(wk):
        out: dict[str, list[int]] = {}
        for r in con.execute(
                "SELECT slot, player_id FROM roster_slots"
                " WHERE team_id = ? AND week_no = ?", (team_id, wk)):
            out.setdefault(r["slot"], []).append(r["player_id"])
        return out

    slots = slots_for(week_no)
    if not slots:
        row = con.execute(
            "SELECT MAX(week_no) AS wk FROM roster_slots WHERE team_id = ?"
            " AND week_no IS NOT NULL AND week_no < ?",
            (team_id, week_no)).fetchone()
        if row and row["wk"] is not None:
            owned = {r["player_id"] for r in con.execute(
                "SELECT player_id FROM roster_slots WHERE team_id = ?"
                " AND week_no IS NULL", (team_id,))}
            slots = {s: [p for p in pids if p in owned]
                     for s, pids in slots_for(row["wk"]).items()}
            slots = {s: p for s, p in slots.items() if p}
    if not slots:
        return None
    return [pid for slot in STARTER_SLOTS for pid in slots.get(slot, [])]


def _side(con, league, team, week_no, ranks, pool, games_by_code,
          fixture_seen) -> schemas.MatchupPreviewSideOut:
    starters = _starters(con, team["id"], week_no)
    if starters is None:
        return schemas.MatchupPreviewSideOut(
            team_id=team["id"], team_name=team["name"], lineup_set=False)
    value = sum(pool + 1 - ranks[p] if p in ranks else 0 for p in starters)
    games = None
    flagged: list[str] = []
    if fixture_seen:
        games = 0
    for pid in starters:
        r = con.execute(
            """SELECT p.name, pr.ipl_team_code, pr.status FROM players p
               LEFT JOIN player_roles pr
                 ON pr.player_id = p.id AND pr.season = p.season
               WHERE p.id = ?""", (pid,)).fetchone()
        if r is None:
            continue
        if fixture_seen and r["ipl_team_code"]:
            games += games_by_code.get(r["ipl_team_code"], 0)
        if availability_from_status(r["status"]) != "active":
            flagged.append(r["name"])
    return schemas.MatchupPreviewSideOut(
        team_id=team["id"], team_name=team["name"], lineup_set=True,
        starters_rank_value=value, games_this_week=games,
        flagged_starters=flagged)


@router.get("/{league_id}/matchups/preview",
            response_model=schemas.MatchupPreviewOut)
def matchup_preview(league_id: int,
                    week_no: int = Query(..., ge=1, le=TOTAL_WEEKS),
                    con: sqlite3.Connection = Depends(get_db)):
    league = get_league(con, league_id)  # 404 if missing
    ranks = {
        r["player_id"]: r["rank"]
        for r in con.execute(
            """SELECT r.player_id, MIN(r.rank) AS rank FROM pre_draft_ranks r
               JOIN teams t ON t.id = r.team_id
               WHERE t.league_id = ? GROUP BY r.player_id""", (league_id,))
    }
    pool = len(ranks)
    data = schedule_games.fetch_week(con, league["season"], week_no)
    games_by_code = {g["ipl_team_code"]: g["games"] for g in data["games"]}
    fixture_seen = bool(data["games"])
    teams = {t["id"]: t for t in con.execute(
        "SELECT id, name FROM teams WHERE league_id = ?", (league_id,))}
    previews = []
    for m in con.execute(
            """SELECT * FROM matchups WHERE league_id = ? AND week_no = ?
               AND status != 'final' ORDER BY id""", (league_id, week_no)):
        prior = con.execute(
            """SELECT * FROM matchups WHERE league_id = ? AND status = 'final'
               AND week_no < ? AND ((team_a_id = ? AND team_b_id = ?)
               OR (team_a_id = ? AND team_b_id = ?))
               ORDER BY week_no DESC LIMIT 1""",
            (league_id, week_no, m["team_a_id"], m["team_b_id"],
             m["team_b_id"], m["team_a_id"])).fetchone()
        prior_out = None
        if prior:
            winner = None
            if prior["score_a"] > prior["score_b"]:
                winner = prior["team_a_id"]
            elif prior["score_b"] > prior["score_a"]:
                winner = prior["team_b_id"]
            prior_out = schemas.PriorH2HOut(
                week_no=prior["week_no"], team_a_id=prior["team_a_id"],
                team_b_id=prior["team_b_id"], score_a=prior["score_a"],
                score_b=prior["score_b"], winner_team_id=winner)
        previews.append(schemas.MatchupPreviewEntryOut(
            matchup_id=m["id"], week_no=week_no, status=m["status"],
            side_a=_side(con, league, teams[m["team_a_id"]], week_no,
                         ranks, pool, games_by_code, fixture_seen),
            side_b=_side(con, league, teams[m["team_b_id"]], week_no,
                         ranks, pool, games_by_code, fixture_seen),
            prior_h2h=prior_out))
    return schemas.MatchupPreviewOut(
        league_id=league_id, week_no=week_no, previews=previews)
