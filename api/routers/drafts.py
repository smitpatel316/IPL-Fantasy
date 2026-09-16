"""Drafts: engine-backed (P3-A2). Snake draft via api.engine.draft_engine.

The draft state machine (snake order, 14 rounds per D7, pick clock + auto-pick,
DND, starters-before-bench, D8 guardrail) lives in api/engine/draft_engine.py;
api/services.py persists it in the engine_state table and projects picks into
draft_picks / roster_slots. Clock expiry auto-fires on the next pick request;
the draft-room WebSocket (api/draft_ws.py) also runs a 1s sweeper that fires
expired clocks and broadcasts to the room."""

import json
import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from .. import schemas, services
from ..database import get_db

router = APIRouter()


def _draft_out(d: dict) -> schemas.DraftOut:
    return schemas.DraftOut(
        id=d["id"], league_id=d["league_id"], rounds=d["rounds"],
        status=d["status"], current_pick_no=d["current_pick_no"],
        draft_order=d["draft_order"],
        on_clock_team_id=d.get("on_clock_team_id"),
    )


@router.get("/{draft_id}", response_model=schemas.DraftOut)
def get_draft(draft_id: int, con: sqlite3.Connection = Depends(get_db)):
    # services._draft_row computes on_clock_team_id (1-indexed pick_no).
    return _draft_out(services._draft_row(con, draft_id))


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


@router.post("/{draft_id}/pick", response_model=schemas.DraftPickOut)
def make_pick(draft_id: int, body: schemas.PickCreate,
              con: sqlite3.Connection = Depends(get_db)):
    if not con.execute("SELECT 1 FROM drafts WHERE id = ?", (draft_id,)).fetchone():
        raise HTTPException(404, f"draft {draft_id} not found")
    p = services.make_pick(con, draft_id, body.team_id, body.player_id)
    return schemas.DraftPickOut(**p)


@router.post("/{draft_id}/dnd", response_model=schemas.DndOut)
def add_dnd(draft_id: int, body: schemas.DndIn,
            con: sqlite3.Connection = Depends(get_db)):
    """Add a player to a team's do-not-draft list (live draft only)."""
    if not con.execute("SELECT 1 FROM drafts WHERE id = ?", (draft_id,)).fetchone():
        raise HTTPException(404, f"draft {draft_id} not found")
    return schemas.DndOut(**services.set_dnd(
        con, draft_id, body.team_id, body.player_id, blocked=True))


@router.delete("/{draft_id}/dnd", response_model=schemas.DndOut)
def remove_dnd(draft_id: int, body: schemas.DndIn,
               con: sqlite3.Connection = Depends(get_db)):
    """Remove a player from a team's do-not-draft list (live draft only)."""
    if not con.execute("SELECT 1 FROM drafts WHERE id = ?", (draft_id,)).fetchone():
        raise HTTPException(404, f"draft {draft_id} not found")
    return schemas.DndOut(**services.set_dnd(
        con, draft_id, body.team_id, body.player_id, blocked=False))
