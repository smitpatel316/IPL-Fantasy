"""Trades: propose/accept/reject/veto + inbox reads, engine-backed (P3-A2).

Trade legality (roster-size invariance, exclusive ownership, deadline end of
week 6, 2-day commissioner review, one-third veto) lives in
api.engine.trade_engine; api/services.py persists it in engine_state and
projects trades into the trades table. Review-closed trades auto-execute
(the roster swap) on the next trade read/write for the league.

Contract status enum: proposed | accepted | rejected | vetoed | expired.
Engine 'under_review' and 'executed' both project to 'accepted'."""

import sqlite3
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from .. import schemas, services
from ..database import get_db
from . import get_league

router = APIRouter()


def _trade_out(t: dict) -> schemas.TradeOut:
    return schemas.TradeOut(**t)


@router.post("", response_model=schemas.TradeOut)
def propose_trade(body: schemas.TradeCreate,
                  con: sqlite3.Connection = Depends(get_db)):
    get_league(con, body.league_id)
    return _trade_out(services.propose_trade(
        con, body.league_id, body.from_team_id, body.to_team_id,
        body.gives, body.receives))


@router.get("", response_model=list[schemas.TradeOut])
def list_trades(league_id: int = Query(...), status: Optional[str] = Query(None),
                con: sqlite3.Connection = Depends(get_db)):
    get_league(con, league_id)
    return [_trade_out(t) for t in services.list_trades(con, league_id, status)]


@router.post("/{trade_id}/accept", response_model=schemas.TradeOut)
def accept_trade(trade_id: int, con: sqlite3.Connection = Depends(get_db)):
    row = con.execute("SELECT league_id FROM trades WHERE id = ?",
                      (trade_id,)).fetchone()
    if not row:
        raise HTTPException(404, f"trade {trade_id} not found")
    # Only the receiving (offeree) team may accept; the engine enforces it.
    return _trade_out(services.respond_trade(con, row["league_id"], trade_id, "accept"))


@router.post("/{trade_id}/reject", response_model=schemas.TradeOut)
def reject_trade(trade_id: int, con: sqlite3.Connection = Depends(get_db)):
    row = con.execute("SELECT league_id FROM trades WHERE id = ?",
                      (trade_id,)).fetchone()
    if not row:
        raise HTTPException(404, f"trade {trade_id} not found")
    return _trade_out(services.respond_trade(con, row["league_id"], trade_id, "reject"))


@router.post("/{trade_id}/veto", response_model=schemas.TradeOut)
def veto_trade(trade_id: int, team_id: Optional[int] = Query(None),
               con: sqlite3.Connection = Depends(get_db)):
    row = con.execute("SELECT league_id FROM trades WHERE id = ?",
                      (trade_id,)).fetchone()
    if not row:
        raise HTTPException(404, f"trade {trade_id} not found")
    # Veto is cast by a non-party team during the 2-day review window.
    return _trade_out(services.respond_trade(
        con, row["league_id"], trade_id, "veto", team_id=team_id))
