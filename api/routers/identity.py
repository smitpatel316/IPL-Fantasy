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

from fastapi import APIRouter, Depends, HTTPException

from .. import schemas
from ..database import get_db
from . import get_team, new_claim_code

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
