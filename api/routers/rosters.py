"""All-teams roster view (P5-W12): read-only league-wide rosters.

GET /api/leagues/{id}/rosters projects every team's roster grouped
by slot. Slot assignment comes from the team's saved week-1 lineup
when one exists (the current slot assignment), else from the
construction roster rows the draft wrote. overseas_starters counts
overseas players in starter slots only (WK/BAT/AR/BOWL/UTIL — BN and
IL never count, per D8's "applies to the 11 starters"). Fully
read-only: no mutation path exists here.
"""

import sqlite3

from fastapi import APIRouter, Depends

from .. import schemas
from ..database import get_db
from . import availability_from_status, get_league

router = APIRouter()

SLOT_ORDER = ["WK", "BAT", "AR", "BOWL", "UTIL", "BN", "IL"]
NON_STARTER = {"BN", "IL"}


def _team_roster(con: sqlite3.Connection, league: dict,
                 team: sqlite3.Row) -> schemas.RosterTeamOut:
    tid = team["id"]
    rows = con.execute(
        """SELECT rs.slot, rs.player_id, p.name, p.season,
                  pr.role, pr.is_overseas, pr.ipl_team_code, pr.status
           FROM roster_slots rs
           JOIN players p ON p.id = rs.player_id
           LEFT JOIN player_roles pr
             ON pr.player_id = p.id AND pr.season = p.season
           WHERE rs.team_id = ? AND rs.week_no = 1 AND p.season = ?""",
        (tid, league["season"])).fetchall()
    if not rows:
        rows = con.execute(
            """SELECT rs.slot, rs.player_id, p.name, p.season,
                      pr.role, pr.is_overseas, pr.ipl_team_code, pr.status
               FROM roster_slots rs
               JOIN players p ON p.id = rs.player_id
               LEFT JOIN player_roles pr
                 ON pr.player_id = p.id AND pr.season = p.season
               WHERE rs.team_id = ? AND rs.week_no IS NULL
                 AND p.season = ?""",
            (tid, league["season"])).fetchall()
    slots: dict[str, list[schemas.RosterPlayerOut]] = {s: [] for s in SLOT_ORDER}
    overseas_starters = 0
    total = 0
    for r in rows:
        slot = r["slot"] if r["slot"] in slots else "BN"
        slots[slot].append(schemas.RosterPlayerOut(
            id=r["player_id"], name=r["name"], role=r["role"],
            is_overseas=bool(r["is_overseas"] or 0),
            ipl_team_code=r["ipl_team_code"],
            availability=availability_from_status(r["status"])))
        total += 1
        if slot not in NON_STARTER and r["is_overseas"]:
            overseas_starters += 1
    return schemas.RosterTeamOut(
        team_id=tid, team_name=team["name"],
        faab_remaining=team["faab_remaining"],
        overseas_starters=overseas_starters, roster_size=total,
        slots=slots)


@router.get("/{league_id}/rosters", response_model=schemas.RostersOut)
def get_rosters(league_id: int, con: sqlite3.Connection = Depends(get_db)):
    league = get_league(con, league_id)  # 404 if missing
    teams = con.execute(
        "SELECT id, name, faab_remaining FROM teams"
        " WHERE league_id = ? ORDER BY name", (league_id,)).fetchall()
    return schemas.RostersOut(
        league_id=league_id,
        teams=[_team_roster(con, league, t) for t in teams])
