"""Drafts: state reads are live; the engine (start/pick/auto-pick/clock) is P2-L1.

SEAM (league-core): implement start_draft() and execute_pick() in a new
api/services/draft_engine.py, then wire the 501 stubs below to it. The snake
order, 15 rounds, pick clock + auto-pick, do-not-draft list, and
starters-before-bench fill all live behind these two endpoints."""

import json
import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from .. import schemas
from ..database import get_db
from . import get_league, row_dict

router = APIRouter()

TRACK = "P2-L1"


def _draft_out(d: dict) -> schemas.DraftOut:
    return schemas.DraftOut(
        id=d["id"], league_id=d["league_id"], rounds=d["rounds"],
        status=d["status"], current_pick_no=d["current_pick_no"],
        draft_order=json.loads(d["draft_order"] or "[]"),
    )


@router.post("/leagues/{league_id}/draft/start", response_model=schemas.NotImplementedOut, status_code=501)
def start_draft(league_id: int, con: sqlite3.Connection = Depends(get_db)):
    get_league(con, league_id)
    # P2-L1: create drafts row (snake order from randomized team order),
    # set league status='drafting', open the WebSocket room.
    return schemas.NotImplementedOut(detail="draft engine not implemented in scaffold", track=TRACK)


@router.get("/{draft_id}", response_model=schemas.DraftOut)
def get_draft(draft_id: int, con: sqlite3.Connection = Depends(get_db)):
    row = con.execute("SELECT * FROM drafts WHERE id = ?", (draft_id,)).fetchone()
    if not row:
        raise HTTPException(404, f"draft {draft_id} not found")
    return _draft_out(row_dict(row))


@router.get("/{draft_id}/picks", response_model=list[schemas.DraftPickOut])
def list_picks(draft_id: int, con: sqlite3.Connection = Depends(get_db)):
    if not con.execute("SELECT 1 FROM drafts WHERE id = ?", (draft_id,)).fetchone():
        raise HTTPException(404, f"draft {draft_id} not found")
    return [
        schemas.DraftPickOut(
            pick_no=r["pick_no"], round_no=r["round_no"], team_id=r["team_id"],
            player_id=r["player_id"], is_auto=bool(r["is_auto"]),
        )
        for r in con.execute(
            "SELECT * FROM draft_picks WHERE draft_id = ? ORDER BY pick_no", (draft_id,)
        )
    ]


@router.post("/{draft_id}/pick", response_model=schemas.NotImplementedOut, status_code=501)
def make_pick(draft_id: int, body: schemas.PickCreate, con: sqlite3.Connection = Depends(get_db)):
    if not con.execute("SELECT 1 FROM drafts WHERE id = ?", (draft_id,)).fetchone():
        raise HTTPException(404, f"draft {draft_id} not found")
    # P2-L1: validate on-clock team, player availability (exclusive ownership),
    # record pick, write roster_slots row, advance clock / auto-pick on expiry.
    return schemas.NotImplementedOut(detail="draft engine not implemented in scaffold", track=TRACK)
