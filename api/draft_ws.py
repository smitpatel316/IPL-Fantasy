"""Draft-room WebSocket: a live snake draft on the real engine (P3-A3).

The draft state machine (snake order, 14 rounds, pick clock + auto-pick, DND,
starters-before-bench, D8 guardrail) lives in api/engine/draft_engine.py;
api/services.py persists it and projects picks into the DB. This module adds
the real-time layer on top — it never reimplements draft logic.

Endpoint:  WS /api/drafts/{draft_id}/ws?team_id={team_id}

Protocol (JSON text frames):
  client -> server:
    {"type": "pick", "player_id": int}        # draft a player (must be your turn)
    {"type": "dnd_add", "player_id": int}     # do-not-draft this player
    {"type": "dnd_remove", "player_id": int}  # un-block a player
    {"type": "ping"}
  server -> client:
    {"type": "state", ...snapshot...}                  # full room state
    {"type": "state", "event": "pick"|"clock_expired"|"dnd_updated", ...}
    {"type": "error", "detail": str}
    {"type": "pong"}

Identity is the ?team_id= query param (dev: no auth in v1). The engine still
enforces turn order — a pick from the wrong team gets an error frame.

The pick clock is driven by a process-wide sweeper (started in the app
lifespan): every second it fires services.expire_pick() for live drafts whose
deadline has passed, then broadcasts the new state to the room.
"""

import asyncio
import logging
import time

from fastapi import HTTPException, WebSocket, WebSocketDisconnect

from api import services
from api.database import connect

log = logging.getLogger("api.draft_ws")


class DraftRoomManager:
    """draft_id -> set of connected websockets."""

    def __init__(self) -> None:
        self._rooms: dict[int, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, draft_id: int, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._rooms.setdefault(draft_id, set()).add(ws)

    async def disconnect(self, draft_id: int, ws: WebSocket) -> None:
        async with self._lock:
            room = self._rooms.get(draft_id)
            if room is not None:
                room.discard(ws)
                if not room:
                    del self._rooms[draft_id]

    async def broadcast(self, draft_id: int, message: dict) -> None:
        async with self._lock:
            targets = list(self._rooms.get(draft_id, ()))
        log.info("broadcast draft %s event %s -> %d socket(s)",
                 draft_id, message.get("event"), len(targets))
        dead: list[WebSocket] = []
        for ws in targets:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.disconnect(draft_id, ws)

    def room_size(self, draft_id: int) -> int:
        return len(self._rooms.get(draft_id, ()))

    def live_drafts(self) -> list[int]:
        return list(self._rooms)


manager = DraftRoomManager()


def _snapshot(draft_id: int) -> dict:
    with connect() as con:
        return services.draft_snapshot(con, draft_id)


def _do_pick(draft_id: int, team_id: int, player_id: int) -> dict:
    with connect() as con:
        return services.make_pick(con, draft_id, team_id, player_id)


def _do_dnd(draft_id: int, team_id: int, player_id: int, blocked: bool) -> dict:
    with connect() as con:
        return services.set_dnd(con, draft_id, team_id, player_id, blocked)


async def _send_state(draft_id: int, ws: WebSocket, event: str | None = None,
                      **extra) -> None:
    snap = await asyncio.to_thread(_snapshot, draft_id)
    msg: dict = {"type": "state", **snap}
    if event:
        msg["event"] = event
    msg.update(extra)
    await ws.send_json(msg)


async def _broadcast_state(draft_id: int, event: str | None = None, **extra) -> None:
    snap = await asyncio.to_thread(_snapshot, draft_id)
    msg: dict = {"type": "state", **snap}
    if event:
        msg["event"] = event
    msg.update(extra)
    await manager.broadcast(draft_id, msg)


async def _handle_message(draft_id: int, team_id: int, ws: WebSocket,
                          msg: dict) -> None:
    mtype = msg.get("type")
    if mtype == "ping":
        await ws.send_json({"type": "pong"})
        return
    if mtype == "pick":
        player_id = msg.get("player_id")
        if not isinstance(player_id, int):
            await ws.send_json({"type": "error", "detail": "pick needs an integer player_id"})
            return
        try:
            pick = await asyncio.to_thread(_do_pick, draft_id, team_id, player_id)
        except HTTPException as e:
            await ws.send_json({"type": "error", "detail": e.detail})
            return
        await _broadcast_state(draft_id, event="pick", pick=pick)
        return
    if mtype in ("dnd_add", "dnd_remove"):
        player_id = msg.get("player_id")
        if not isinstance(player_id, int):
            await ws.send_json({"type": "error", "detail": "dnd needs an integer player_id"})
            return
        try:
            dnd = await asyncio.to_thread(
                _do_dnd, draft_id, team_id, player_id, mtype == "dnd_add")
        except HTTPException as e:
            await ws.send_json({"type": "error", "detail": e.detail})
            return
        await _broadcast_state(draft_id, event="dnd_updated", dnd_updated=dnd)
        return
    await ws.send_json({"type": "error", "detail": f"unknown message type {mtype!r}"})


async def draft_room_ws(websocket: WebSocket, draft_id: int) -> None:
    """WebSocket handler for one draft room. Mounted in api/index.py."""
    raw_team = websocket.query_params.get("team_id")
    try:
        team_id = int(raw_team)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        await websocket.close(code=4400)
        return
    try:
        snap = await asyncio.to_thread(_snapshot, draft_id)
    except HTTPException:
        await websocket.close(code=4404)
        return
    if team_id not in [t["id"] for t in snap["draft"]["teams"]]:
        await websocket.close(code=4403)
        return

    await manager.connect(draft_id, websocket)
    await websocket.send_json({"type": "state", **snap})
    try:
        while True:
            msg = await websocket.receive_json()
            if not isinstance(msg, dict):
                await websocket.send_json({"type": "error", "detail": "message must be a JSON object"})
                continue
            await _handle_message(draft_id, team_id, websocket, msg)
    except WebSocketDisconnect:
        await manager.disconnect(draft_id, websocket)


# ---------------------------------------------------------------------------
# Pick-clock sweeper: fires clock expiry for live drafts every second.
# ---------------------------------------------------------------------------

def _sweep_once() -> list[tuple[int, dict]]:
    """Fire expired pick clocks; returns [(draft_id, pick), ...]. Runs in a
    worker thread — opens its own DB connection."""
    out: list[tuple[int, dict]] = []
    with connect() as con:
        rows = con.execute(
            "SELECT id FROM drafts WHERE status = 'live'").fetchall()
        for r in rows:
            try:
                pick = services.expire_pick(con, r["id"])
            except HTTPException as e:
                log.warning("clock sweep: draft %s: %s", r["id"], e.detail)
                continue
            if pick is not None:
                out.append((r["id"], pick))
    return out


async def draft_clock_sweeper() -> None:
    """Background task (app lifespan): poll live drafts every second and
    auto-pick on clock expiry, broadcasting to each draft's room."""
    log.info("draft clock sweeper started")
    while True:
        await asyncio.sleep(1)
        try:
            expired = await asyncio.to_thread(_sweep_once)
        except Exception:
            log.exception("draft clock sweep failed")
            continue
        for draft_id, pick in expired:
            log.info("clock expired: draft %s pick %s auto-picked team %s",
                     draft_id, pick["pick_no"], pick["team_id"])
            try:
                await _broadcast_state(draft_id, event="clock_expired", pick=pick)
            except Exception:
                log.exception("broadcast failed for draft %s", draft_id)


def start_sweeper() -> asyncio.Task:
    return asyncio.create_task(draft_clock_sweeper())
