"""Waivers: weekly blind FAAB (D6), engine-backed (P3-A2).

Bids go to api.engine.waiver_engine (blind: only your own bids are readable);
the Wednesday run resolves highest-bid-wins with reverse-standings tiebreaks,
deducts FAAB, swaps roster_slots, and freezes drops for 2 days.
Engine state persists in engine_state; claim/run results project into
waiver_claims, teams.faab_remaining, and roster_slots."""

import sqlite3

from fastapi import APIRouter, Depends, Query

from .. import schemas, services
from ..database import get_db
from . import get_league, get_team

router = APIRouter()


@router.post("/claim", response_model=schemas.WaiverClaimOut)
def submit_claim(body: schemas.WaiverClaimCreate,
                 con: sqlite3.Connection = Depends(get_db)):
    get_league(con, body.league_id)
    get_team(con, body.team_id)
    # 15-man rosters have no open slots: a drop is required (422 otherwise).
    week_no = services.current_week(con, body.league_id)
    return schemas.WaiverClaimOut(**services.submit_waiver_claim(
        con, body.league_id, body.team_id, week_no,
        body.add_player_id, body.drop_player_id, body.bid))


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


@router.post("/run", response_model=list[schemas.WaiverRunResultOut])
def run_waivers(league_id: int = Query(...), week_no: int = Query(...),
                con: sqlite3.Connection = Depends(get_db)):
    get_league(con, league_id)
    # The Wednesday ~3am PT blind-bid run (commissioner-triggerable).
    return [schemas.WaiverRunResultOut(**r)
            for r in services.run_waivers(con, league_id, week_no)]
