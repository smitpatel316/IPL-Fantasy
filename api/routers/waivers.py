"""Waivers: weekly blind FAAB (D6). Claim submission + the Wednesday run are P2-L3.

SEAM (league-core): implement the blind-bid run in api/services/waiver_engine.py —
highest bid wins, ties broken by reverse standings, 2-day freeze for drops,
$100 season budget accounting — then wire the stubs below."""

import sqlite3

from fastapi import APIRouter, Depends, Query

from .. import schemas
from ..database import get_db
from . import get_league, get_team

router = APIRouter()

TRACK = "P2-L3"


@router.post("/claim", response_model=schemas.NotImplementedOut, status_code=501)
def submit_claim(body: schemas.WaiverClaimCreate, con: sqlite3.Connection = Depends(get_db)):
    get_league(con, body.league_id)
    get_team(con, body.team_id)
    # P2-L3: validate bid <= faab_remaining, add_player is a free agent,
    # drop_player (if any) is on the roster; store as pending.
    return schemas.NotImplementedOut(detail="waiver engine not implemented in scaffold", track=TRACK)


@router.get("/pending", response_model=list[schemas.WaiverClaimOut])
def pending_claims(league_id: int = Query(...), week_no: int = Query(...),
                   con: sqlite3.Connection = Depends(get_db)):
    get_league(con, league_id)
    return [
        schemas.WaiverClaimOut(
            id=r["id"], week_no=r["week_no"], team_id=r["team_id"],
            add_player_id=r["add_player_id"], drop_player_id=r["drop_player_id"],
            bid=r["bid"], status=r["status"],
        )
        for r in con.execute(
            "SELECT * FROM waiver_claims WHERE league_id = ? AND week_no = ? AND status = 'pending'"
            " ORDER BY created_at",
            (league_id, week_no),
        )
    ]


@router.post("/run", response_model=schemas.NotImplementedOut, status_code=501)
def run_waivers(league_id: int = Query(...), week_no: int = Query(...),
                con: sqlite3.Connection = Depends(get_db)):
    get_league(con, league_id)
    # P2-L3: the Wednesday ~3am PT blind-bid run (commissioner-triggerable).
    return schemas.NotImplementedOut(detail="waiver engine not implemented in scaffold", track=TRACK)
