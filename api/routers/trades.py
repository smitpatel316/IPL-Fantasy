"""Trades: propose/accept/reject/veto + inbox reads. Engine is P2-L4.

SEAM (league-core): trade legality (roster-slot fit post-trade, exclusive
ownership, deadline end of week 6, 2-day commissioner review, one-third veto)
lives in api/services/trade_engine.py; wire the 501 stubs below to it."""

import json
import sqlite3
from typing import Optional

from fastapi import APIRouter, Depends, Query

from .. import schemas
from ..database import get_db
from . import get_league, row_dict

router = APIRouter()

TRACK = "P2-L4"


def _trade_out(r: sqlite3.Row) -> schemas.TradeOut:
    d = row_dict(r)
    return schemas.TradeOut(
        id=d["id"], league_id=d["league_id"], from_team_id=d["from_team_id"],
        to_team_id=d["to_team_id"], gives=json.loads(d["gives"] or "[]"),
        receives=json.loads(d["receives"] or "[]"), status=d["status"],
        review_deadline=d["review_deadline"],
    )


@router.post("", response_model=schemas.NotImplementedOut, status_code=501)
def propose_trade(body: schemas.TradeCreate, con: sqlite3.Connection = Depends(get_db)):
    get_league(con, body.league_id)
    # P2-L4: validate both sides own the players, rosters stay slot-legal,
    # deadline not passed; create as proposed with review_deadline = +2 days.
    return schemas.NotImplementedOut(detail="trade engine not implemented in scaffold", track=TRACK)


@router.get("", response_model=list[schemas.TradeOut])
def list_trades(league_id: int = Query(...), status: Optional[str] = Query(None),
                con: sqlite3.Connection = Depends(get_db)):
    get_league(con, league_id)
    sql = "SELECT * FROM trades WHERE league_id = ?"
    params: list = [league_id]
    if status:
        sql += " AND status = ?"
        params.append(status)
    sql += " ORDER BY created_at DESC"
    return [_trade_out(r) for r in con.execute(sql, params)]


@router.post("/{trade_id}/accept", response_model=schemas.NotImplementedOut, status_code=501)
def accept_trade(trade_id: int, con: sqlite3.Connection = Depends(get_db)):
    # P2-L4: only the receiving team accepts; swap roster_slots rows atomically.
    return schemas.NotImplementedOut(detail="trade engine not implemented in scaffold", track=TRACK)


@router.post("/{trade_id}/reject", response_model=schemas.NotImplementedOut, status_code=501)
def reject_trade(trade_id: int, con: sqlite3.Connection = Depends(get_db)):
    # P2-L4: only the receiving team rejects.
    return schemas.NotImplementedOut(detail="trade engine not implemented in scaffold", track=TRACK)


@router.post("/{trade_id}/veto", response_model=schemas.NotImplementedOut, status_code=501)
def veto_trade(trade_id: int, con: sqlite3.Connection = Depends(get_db)):
    # P2-L4: commissioner veto within the 2-day review window (one-third league veto option).
    return schemas.NotImplementedOut(detail="trade engine not implemented in scaffold", track=TRACK)
