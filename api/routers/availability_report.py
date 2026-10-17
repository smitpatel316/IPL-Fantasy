"""League-wide availability / injury report (P5-W29).

GET /api/leagues/{id}/availability-report — every rostered player
whose curated player_roles.status is not active (the P5-W6
availability seam), grouped by status (out, retired) and owning team;
IL occupancy per team (current slot assignment: week-1 saved lineup
else construction roster, the P5-W12 seam); and flagged unrostered
free agents listed separately so waiver shoppers see the risk.
Read-only; no new mutation path — moves still flow through the
validated lineup PUT.
"""

import sqlite3

from fastapi import APIRouter, Depends

from .. import schemas
from ..database import get_db
from . import availability_from_status, get_league, owned_map

router = APIRouter()


@router.get("/{league_id}/availability-report",
            response_model=schemas.AvailabilityReportOut)
def availability_report(league_id: int,
                        con: sqlite3.Connection = Depends(get_db)):
    league = get_league(con, league_id)  # 404 if missing
    owned = owned_map(con, league_id)
    teams = {t["id"]: t["name"] for t in con.execute(
        "SELECT id, name FROM teams WHERE league_id = ?", (league_id,))}

    # Current IL occupants: week-1 saved slots win, else construction.
    il_by_team: dict[int, str] = {}
    for source_week in ("1", "NULL"):
        cond = "rs.week_no = 1" if source_week == "1" else "rs.week_no IS NULL"
        for r in con.execute(
                f"""SELECT rs.team_id, p.name FROM roster_slots rs
                    JOIN players p ON p.id = rs.player_id
                    WHERE rs.slot = 'IL' AND {cond}"""):
            if r["team_id"] in teams and r["team_id"] not in il_by_team:
                il_by_team[r["team_id"]] = r["name"]
    il_player_ids = {}
    for r in con.execute(
            """SELECT rs.team_id, rs.player_id FROM roster_slots rs
               WHERE rs.slot = 'IL' AND rs.week_no IS NULL"""):
        il_player_ids[r["player_id"]] = r["team_id"]

    grouped: dict[str, dict[int, list]] = {"out": {}, "retired": {}}
    free_agents: list[schemas.AvailabilityReportPlayerOut] = []
    for r in con.execute(
            """SELECT p.id, p.name, pr.role, pr.ipl_team_code, pr.status
               FROM players p JOIN player_roles pr
                 ON pr.player_id = p.id AND pr.season = p.season
               WHERE p.season = ? ORDER BY p.name""", (league["season"],)):
        avail = availability_from_status(r["status"])
        if avail == "active":
            continue
        entry = schemas.AvailabilityReportPlayerOut(
            id=r["id"], name=r["name"], role=r["role"],
            ipl_team_code=r["ipl_team_code"], availability=avail,
            on_il=il_player_ids.get(r["id"]) == owned.get(r["id"]))
        owner = owned.get(r["id"])
        if owner is None:
            free_agents.append(entry)
        elif owner in teams:
            grouped[avail].setdefault(owner, []).append(entry)
    groups = [
        schemas.AvailabilityGroupOut(
            availability=avail,
            teams=[schemas.AvailabilityReportTeamOut(
                       team_id=tid, team_name=teams[tid], players=players)
                   for tid, players in sorted(
                       by_team.items(), key=lambda kv: teams[kv[0]])])
        for avail, by_team in grouped.items() if by_team
    ]
    return schemas.AvailabilityReportOut(
        league_id=league_id, groups=groups,
        il_occupancy=[schemas.ILOccupancyOut(
            team_id=tid, team_name=name,
            il_player_name=il_by_team.get(tid))
            for tid, name in sorted(teams.items(), key=lambda kv: kv[1])],
        free_agents=free_agents)
