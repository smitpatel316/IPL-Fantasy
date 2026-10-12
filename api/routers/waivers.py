"""Waivers: weekly blind FAAB (D6), engine-backed (P3-A2).

Bids go to api.engine.waiver_engine (blind: only your own bids are readable);
the Wednesday run resolves highest-bid-wins with reverse-standings tiebreaks,
deducts FAAB, swaps roster_slots, and freezes drops for 2 days.
Engine state persists in engine_state; claim/run results project into
waiver_claims, teams.faab_remaining, and roster_slots."""

import sqlite3

from fastapi import APIRouter, Depends, Query, Request

from .. import schemas, services
from ..constants import TOTAL_WEEKS
from ..database import get_db
from . import get_league, require_team_actor

router = APIRouter()


@router.post("/claim", response_model=schemas.WaiverClaimOut)
def submit_claim(body: schemas.WaiverClaimCreate, request: Request,
                 con: sqlite3.Connection = Depends(get_db)):
    get_league(con, body.league_id)
    require_team_actor(con, body.team_id, request)  # P4-W18 claim-code gate
    # 15-man rosters have no open slots: a drop is required (422 otherwise).
    week_no = services.current_week(con, body.league_id)
    return schemas.WaiverClaimOut(**services.submit_waiver_claim(
        con, body.league_id, body.team_id, week_no,
        body.add_player_id, body.drop_player_id, body.bid))


@router.get("/pending", response_model=list[schemas.WaiverClaimOut])
def pending_claims(league_id: int = Query(...),
                   week_no: int = Query(..., ge=1, le=TOTAL_WEEKS),
                   team_id: int | None = Query(None),
                   con: sqlite3.Connection = Depends(get_db)):
    """Blind FAAB (D6): bid amounts are sealed until the Wednesday run.

    With team_id: only that team's own claims, amounts visible.
    Without: all claims listed but amounts sealed (bid=null) — a
    league-activity view that can never leak a bid value.
    """
    get_league(con, league_id)
    sql = ("SELECT * FROM waiver_claims WHERE league_id = ? AND week_no = ?"
           " AND status = 'pending'")
    params: list = [league_id, week_no]
    if team_id is not None:
        get_team(con, team_id)
        sql += " AND team_id = ?"
        params.append(team_id)
    sql += " ORDER BY created_at"
    return [
        schemas.WaiverClaimOut(
            id=r["id"], week_no=r["week_no"], team_id=r["team_id"],
            add_player_id=r["add_player_id"], drop_player_id=r["drop_player_id"],
            bid=r["bid"] if team_id is not None else None, status=r["status"],
        )
        for r in con.execute(sql, params)
    ]


@router.get("/history", response_model=list[schemas.WaiverClaimOut])
def claims_history(league_id: int = Query(...),
                   week_no: int = Query(..., ge=1, le=TOTAL_WEEKS),
                   con: sqlite3.Connection = Depends(get_db)):
    """Resolved claims (won/lost) for a league+week (P4-W14). Pending
    claims stay on /pending; once the run resolves a claim its bid is
    public record, so amounts are returned as-is."""
    get_league(con, league_id)
    return [
        schemas.WaiverClaimOut(
            id=r["id"], week_no=r["week_no"], team_id=r["team_id"],
            add_player_id=r["add_player_id"], drop_player_id=r["drop_player_id"],
            bid=r["bid"], status=r["status"],
        )
        for r in con.execute(
            "SELECT * FROM waiver_claims WHERE league_id = ? AND week_no = ? AND status != 'pending'"
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
