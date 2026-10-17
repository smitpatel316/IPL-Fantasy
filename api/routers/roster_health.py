"""IL / roster-health assistant (P5-W21): D7's IL rule made actionable.

GET /api/leagues/{id}/roster-health?team_id= is a READ-ONLY projection
over the managing-as team's current slot assignment (saved week-1
lineup when one exists, else the construction roster — the same
projection P5-W12 uses) joined to the curated player_roles.status:

  * move_to_il — rostered players who are IL-eligible (status is a
    non-active, non-retired designation, per P4-W4) but sit in a
    starter/BN slot; each notes the roster spot the move would free.
  * return_candidates — IL occupants whose registry status is active
    again (NULL/'active'): they no longer need the IL slot.
  * retired — rostered players flagged 'retired' (listed separately,
    never double-listed as move-to-IL candidates).

The move itself still flows through the existing validated lineup
PUT — this surface adds no mutation path and never auto-moves anyone.
Claim-gated per P4-W18 (require_team_actor): a second team sees none
of the first team's roster-health payload. Source copy is honest:
statuses come from the curated registry until live squads import
(the P5-W6 basis).
"""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from .. import schemas
from ..database import get_db
from . import get_league, require_team_actor

router = APIRouter()

BASIS = "Availability from curated registry until live squads import"


def _norm(status) -> str:
    return (status or "").strip().lower()


@router.get("/{league_id}/roster-health",
            response_model=schemas.RosterHealthOut)
def get_roster_health(league_id: int, team_id: int = Query(...),
                      request: Request = None,
                      con: sqlite3.Connection = Depends(get_db)):
    league = get_league(con, league_id)  # 404 if missing
    team = require_team_actor(con, team_id, request)
    if team["league_id"] != league_id:
        raise HTTPException(422, f"team {team_id} is not in league {league_id}")

    rows = con.execute(
        """SELECT rs.slot, rs.player_id, p.name, pr.role, pr.status
           FROM roster_slots rs
           JOIN players p ON p.id = rs.player_id
           LEFT JOIN player_roles pr
             ON pr.player_id = p.id AND pr.season = p.season
           WHERE rs.team_id = ? AND rs.week_no = 1 AND p.season = ?""",
        (team_id, league["season"])).fetchall()
    if not rows:
        rows = con.execute(
            """SELECT rs.slot, rs.player_id, p.name, pr.role, pr.status
               FROM roster_slots rs
               JOIN players p ON p.id = rs.player_id
               LEFT JOIN player_roles pr
                 ON pr.player_id = p.id AND pr.season = p.season
               WHERE rs.team_id = ? AND rs.week_no IS NULL AND p.season = ?""",
            (team_id, league["season"])).fetchall()

    move_to_il, returning, retired = [], [], []
    for r in rows:
        status = _norm(r["status"])
        entry = schemas.RosterHealthPlayerOut(
            player_id=r["player_id"], player_name=r["name"],
            role=r["role"], slot=r["slot"],
            status=r["status"] or "active")
        if status == "retired":
            retired.append(entry)
        elif r["slot"] == "IL" and status in ("", "active"):
            returning.append(entry)
        elif r["slot"] != "IL" and status not in ("", "active"):
            entry.note = "Moving to IL frees a roster spot"
            move_to_il.append(entry)

    return schemas.RosterHealthOut(
        league_id=league_id, team_id=team_id, team_name=team["name"],
        basis=BASIS, move_to_il=move_to_il,
        return_candidates=returning, retired=retired)
