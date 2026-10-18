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

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from .. import schemas, services
from ..database import get_db
from . import get_league, require_team_actor

router = APIRouter()


def _trade_out(t: dict) -> schemas.TradeOut:
    return schemas.TradeOut(**t)


def _csv_ids(value: str, label: str) -> list[int]:
    try:
        ids = [int(x) for x in value.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(422, f"{label} must be a comma-separated list of player ids")
    if not ids:
        raise HTTPException(422, f"{label} must list at least one player")
    return ids


@router.get("/analyze", response_model=schemas.TradeAnalysisOut)
def analyze_trade(league_id: int = Query(...),
                 from_team_id: int = Query(...),
                 to_team_id: int = Query(...),
                 gives: str = Query(..., description="comma-separated player ids from_team sends"),
                 receives: str = Query(..., description="comma-separated player ids from_team gets"),
                 con: sqlite3.Connection = Depends(get_db)):
    """Read-only trade impact projection (P5-W1).

    Computed server-side from pre_draft_ranks (league ADP proxy) and the
    P3-A6 fixture game-count table. No engine involvement, no writes."""
    get_league(con, league_id)
    return schemas.TradeAnalysisOut(**services.analyze_trade(
        con, league_id, from_team_id, to_team_id,
        _csv_ids(gives, "gives"), _csv_ids(receives, "receives")))


@router.get("/finder", response_model=schemas.TradeFinderOut)
def trade_finder(league_id: int = Query(...), team_id: int = Query(...),
                 con: sqlite3.Connection = Depends(get_db)):
    """Read-only "find a partner" suggestions (P5-W18): positional
    surplus/deficit matches across the league, composed on the trade
    block (P5-W7). No writes; propose/analyzer/veto flows untouched."""
    get_league(con, league_id)
    return schemas.TradeFinderOut(
        **services.trade_finder(con, league_id, team_id))


@router.post("", response_model=schemas.TradeOut)
def propose_trade(body: schemas.TradeCreate, request: Request,
                  con: sqlite3.Connection = Depends(get_db)):
    get_league(con, body.league_id)
    require_team_actor(con, body.from_team_id, request)  # P4-W18
    return _trade_out(services.propose_trade(
        con, body.league_id, body.from_team_id, body.to_team_id,
        body.gives, body.receives))


@router.get("", response_model=list[schemas.TradeOut])
def list_trades(league_id: int = Query(...), status: Optional[str] = Query(None),
                con: sqlite3.Connection = Depends(get_db)):
    get_league(con, league_id)
    return [_trade_out(t) for t in services.list_trades(con, league_id, status)]


@router.post("/{trade_id}/counter", response_model=schemas.TradeOut)
def counter_trade(trade_id: int, body: schemas.CounterTradeCreate,
                  request: Request,
                  con: sqlite3.Connection = Depends(get_db)):
    """Counter a pending incoming trade (P5-W36): creates a NEW
    pending trade back to the original proposer through the existing
    propose path (all validation unchanged), linked via counter_of.
    The original trade is not mutated. The countering team must be
    the original's recipient and presents its claim code if claimed
    (P4-W18), exactly like propose. League is derived from the
    original trade row, like accept/reject."""
    row = con.execute("SELECT league_id FROM trades WHERE id = ?",
                      (trade_id,)).fetchone()
    if not row:
        raise HTTPException(404, f"trade {trade_id} not found")
    require_team_actor(con, body.from_team_id, request)  # P4-W18
    return _trade_out(services.counter_trade(
        con, row["league_id"], trade_id, body.from_team_id,
        body.gives, body.receives))


@router.post("/{trade_id}/accept", response_model=schemas.TradeOut)
def accept_trade(trade_id: int, request: Request,
                 con: sqlite3.Connection = Depends(get_db)):
    row = con.execute("SELECT league_id, to_team_id FROM trades WHERE id = ?",
                      (trade_id,)).fetchone()
    if not row:
        raise HTTPException(404, f"trade {trade_id} not found")
    # Only the receiving (offeree) team may accept — and if that team is
    # claimed, only with its claim code (P4-W18).
    require_team_actor(con, row["to_team_id"], request)
    return _trade_out(services.respond_trade(con, row["league_id"], trade_id, "accept"))


@router.post("/{trade_id}/reject", response_model=schemas.TradeOut)
def reject_trade(trade_id: int, request: Request,
                 con: sqlite3.Connection = Depends(get_db)):
    row = con.execute("SELECT league_id, to_team_id FROM trades WHERE id = ?",
                      (trade_id,)).fetchone()
    if not row:
        raise HTTPException(404, f"trade {trade_id} not found")
    require_team_actor(con, row["to_team_id"], request)  # P4-W18
    return _trade_out(services.respond_trade(con, row["league_id"], trade_id, "reject"))


@router.post("/{trade_id}/veto", response_model=schemas.TradeOut)
def veto_trade(trade_id: int, request: Request, team_id: Optional[int] = Query(None),
               con: sqlite3.Connection = Depends(get_db)):
    row = con.execute("SELECT league_id FROM trades WHERE id = ?",
                      (trade_id,)).fetchone()
    if not row:
        raise HTTPException(404, f"trade {trade_id} not found")
    # Veto is cast by a non-party team during the 2-day review window;
    # the casting team must present its claim code if claimed (P4-W18).
    if team_id is not None:
        require_team_actor(con, team_id, request)
    return _trade_out(services.respond_trade(
        con, row["league_id"], trade_id, "veto", team_id=team_id))


# ---------- multi-team deals (P5-W37) ----------
def _deal_out(d: dict) -> schemas.DealOut:
    return schemas.DealOut(**d)


def _deal_row(con: sqlite3.Connection, deal_id: int) -> sqlite3.Row:
    row = con.execute("SELECT league_id FROM trades WHERE id = ?",
                      (deal_id,)).fetchone()
    if not row:
        raise HTTPException(404, f"deal {deal_id} not found")
    return row


@router.post("/deal", response_model=schemas.DealOut)
def propose_deal(body: schemas.DealCreate, request: Request,
                 con: sqlite3.Connection = Depends(get_db)):
    """Propose a multi-team deal (P5-W37): a set of directed player
    legs sharing one deal_id. The first leg's giver is the proposer —
    they present their claim code if claimed (P4-W18), exactly like
    propose — and count as accepted; every other party must accept
    before the deal enters its single 2-day review window. Guards:
    per-team roster-count invariance, the P4-W24 D8-reachability guard
    on EVERY participating team, the week-6 deadline, and the per-team
    pending cap."""
    get_league(con, body.league_id)
    if not body.legs:
        raise HTTPException(422, "a deal needs at least one leg")
    require_team_actor(con, body.legs[0].giver_id, request)  # P4-W18
    return _deal_out(services.propose_deal(
        con, body.league_id, [leg.model_dump() for leg in body.legs]))


@router.get("/deals", response_model=list[schemas.DealOut])
def list_deals(league_id: int = Query(...), status: Optional[str] = Query(None),
               con: sqlite3.Connection = Depends(get_db)):
    get_league(con, league_id)
    return [_deal_out(d) for d in services.list_deals(con, league_id, status)]


@router.get("/deal/{deal_id}", response_model=schemas.DealOut)
def get_deal(deal_id: int, con: sqlite3.Connection = Depends(get_db)):
    row = _deal_row(con, deal_id)
    return _deal_out(services.get_deal(con, row["league_id"], deal_id))


def _deal_respond(deal_id: int, team_id: int, request: Request,
                  con: sqlite3.Connection, action: str) -> schemas.DealOut:
    row = _deal_row(con, deal_id)
    # The acting team must present its claim code if claimed (P4-W18).
    require_team_actor(con, team_id, request)
    return _deal_out(services.respond_deal(
        con, row["league_id"], deal_id, action, team_id=team_id))


@router.post("/deal/{deal_id}/accept", response_model=schemas.DealOut)
def accept_deal(deal_id: int, body: schemas.DealAct, request: Request,
                con: sqlite3.Connection = Depends(get_db)):
    """A deal party accepts (P5-W37). The proposer counts as accepted
    from proposal time; when every party has accepted, the deal enters
    its single 2-day review window."""
    return _deal_respond(deal_id, body.team_id, request, con, "accept")


@router.post("/deal/{deal_id}/reject", response_model=schemas.DealOut)
def reject_deal(deal_id: int, body: schemas.DealAct, request: Request,
                con: sqlite3.Connection = Depends(get_db)):
    """Any party rejecting dissolves the entire deal (P5-W37)."""
    return _deal_respond(deal_id, body.team_id, request, con, "reject")


@router.post("/deal/{deal_id}/withdraw", response_model=schemas.DealOut)
def withdraw_deal(deal_id: int, body: schemas.DealAct, request: Request,
                  con: sqlite3.Connection = Depends(get_db)):
    """The proposer withdraws before all parties accept (P5-W37) —
    dissolves the entire deal."""
    return _deal_respond(deal_id, body.team_id, request, con, "withdraw")


@router.post("/deal/{deal_id}/veto", response_model=schemas.DealOut)
def veto_deal(deal_id: int, request: Request, team_id: Optional[int] = Query(None),
              con: sqlite3.Connection = Depends(get_db)):
    """A non-party team vetoes the deal during its 2-day review window
    (P5-W37); the casting team must present its claim code if claimed
    (P4-W18). One-third-of-league threshold, computed on the whole
    league like trades."""
    row = _deal_row(con, deal_id)
    if team_id is not None:
        require_team_actor(con, team_id, request)
    return _deal_out(services.respond_deal(
        con, row["league_id"], deal_id, "veto", team_id=team_id))
