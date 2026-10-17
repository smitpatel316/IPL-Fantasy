"""Team identity (P4-W18): per-team claim codes.

A team starts UNCLAIMED (mutations honor-system — how every league
works today). Claiming generates a secret code, returned exactly
once to the claimer; from then on, team-scoped mutations (lineup,
waiver claims, trade propose/accept/reject/veto) must present it in
the X-Team-Claim header (see require_team_actor). Joining a league
auto-claims the new team for its creator. Reset clears the code
(commissioner recovery for a lost code — deliberately open in v1,
like the rest of the pre-accounts surface; the league invite code
gates who can reach these endpoints at all in practice).
"""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request

from .. import schemas
from ..database import get_db
from . import get_team, new_claim_code, require_team_actor

router = APIRouter()


@router.post("/teams/{team_id}/claim", response_model=schemas.ClaimOut)
def claim_team(team_id: int, con: sqlite3.Connection = Depends(get_db)):
    team = get_team(con, team_id)
    if team.get("claim_code"):
        raise HTTPException(409, f"team '{team['name']}' is already claimed")
    code = new_claim_code()
    con.execute("UPDATE teams SET claim_code = ? WHERE id = ?", (code, team_id))
    con.commit()
    return schemas.ClaimOut(team_id=team_id, claim_code=code)


@router.patch("/teams/{team_id}", response_model=schemas.TeamOut)
def rename_team(team_id: int, body: schemas.TeamRenameIn,
                request: Request,
                con: sqlite3.Connection = Depends(get_db)):
    """Rename a team (P5-W23). Claim-aware per P4-W18: once the team
    is claimed, only a request carrying its claim code may rename it
    (require_team_actor 403s otherwise); unclaimed teams stay
    honor-system like every other mutation. The name is trimmed,
    must be non-empty, and must be unique within the league — the
    same 409 the join flow raises (teams has UNIQUE(league_id, name);
    the explicit check keeps the message identical, the IntegrityError
    catch covers a race). Everywhere the name is projected (standings,
    rosters, activity feed, matchups) reads teams.name live, so the
    new name appears league-wide with no further writes."""
    team = require_team_actor(con, team_id, request)
    name = body.name.strip()
    if not name:
        raise HTTPException(422, "team name must be non-empty")
    if name != team["name"]:
        clash = con.execute(
            "SELECT 1 FROM teams WHERE league_id = ? AND name = ? AND id != ?",
            (team["league_id"], name, team_id)).fetchone()
        if clash:
            raise HTTPException(
                409, f"team name '{name}' taken in this league")
        try:
            con.execute("UPDATE teams SET name = ? WHERE id = ?",
                        (name, team_id))
            con.commit()
        except sqlite3.IntegrityError:
            con.rollback()
            raise HTTPException(
                409, f"team name '{name}' taken in this league")
        team = get_team(con, team_id)
    return schemas.TeamOut(
        id=team["id"], league_id=team["league_id"], name=team["name"],
        owner_name=team["owner_name"], faab_remaining=team["faab_remaining"],
        claimed=bool(team.get("claim_code")),
    )


@router.post("/teams/{team_id}/reset-claim", response_model=schemas.TeamOut)
def reset_claim(team_id: int, con: sqlite3.Connection = Depends(get_db)):
    """Commissioner recovery: clear a team's claim code (the team
    becomes unclaimed/honor-system until re-claimed)."""
    team = get_team(con, team_id)
    con.execute("UPDATE teams SET claim_code = NULL WHERE id = ?", (team_id,))
    con.commit()
    return schemas.TeamOut(
        id=team["id"], league_id=team["league_id"], name=team["name"],
        owner_name=team["owner_name"], faab_remaining=team["faab_remaining"],
        claimed=False,
    )
