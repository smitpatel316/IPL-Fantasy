"""League message board (P5-W5): persistent league-scoped posts.

Separate from the draft room's in-memory WS chat (P4-W20): posts live
in the league_messages table and survive restarts. Reads are open
(any visitor can read the board); posting is gated by team identity
— once a team is claimed, its claim code must ride along
(require_team_actor, P4-W18). The commissioner (the team owned by the
league's commissioner user) can soft-delete any post: deleted_at is
stamped and the row stops rendering, but is never hard-deleted.
"""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from .. import schemas
from ..database import get_db
from . import get_league, require_team_actor

router = APIRouter()


def _commissioner_team_id(con: sqlite3.Connection, league: dict):
    """The commissioner's team, for soft-delete rights. The data model
    never guarantees the commissioner user owns a team: league
    creation mints a user row, and joining mints ANOTHER user row for
    the team owner (the sandbox league's commissioner 'Smit' is user
    1; Smit's XI is owned by user 2, also named 'Smit'). Resolution:
    exact owner_id match first, then an owner whose name matches the
    commissioner user's name (the normal create-then-join flow)."""
    row = con.execute(
        "SELECT id FROM teams WHERE league_id = ? AND owner_id = ?"
        " ORDER BY id LIMIT 1",
        (league["id"], league["commissioner_id"])).fetchone()
    if row:
        return row["id"]
    row = con.execute(
        """SELECT t.id FROM teams t JOIN users u ON u.id = t.owner_id
           WHERE t.league_id = ? AND u.name = (
               SELECT name FROM users WHERE id = ?)
           ORDER BY t.id LIMIT 1""",
        (league["id"], league["commissioner_id"])).fetchone()
    return row["id"] if row else None


def _out(con: sqlite3.Connection, row: sqlite3.Row) -> schemas.MessageOut:
    team = con.execute(
        "SELECT name FROM teams WHERE id = ?", (row["team_id"],)).fetchone()
    cols = row.keys() if isinstance(row, sqlite3.Row) else []
    pinned_at = row["pinned_at"] if "pinned_at" in cols else None
    return schemas.MessageOut(
        id=row["id"], league_id=row["league_id"], team_id=row["team_id"],
        team_name=team["name"] if team else "",
        body=row["body"], created_at=row["created_at"],
        pinned_at=pinned_at)


def _pinned_row(con: sqlite3.Connection, league_id: int):
    """The one active pinned post for a league (None when no pin).
    Soft-deleted posts never count — deleting a pinned post clears
    the strip. At most one active pin is enforced by the pin endpoint;
    take the latest in case of legacy drift."""
    return con.execute(
        "SELECT * FROM league_messages"
        " WHERE league_id = ? AND deleted_at IS NULL AND pinned_at IS NOT NULL"
        " ORDER BY pinned_at DESC LIMIT 1", (league_id,)).fetchone()


def _require_commissioner_actor(con, league, team_id: int, request, action: str):
    """Gate shared by delete/pin/unpin: the acting team must be the
    commissioner's team (and pass the P4-W18 claim gate)."""
    actor = require_team_actor(con, team_id, request)
    if actor["league_id"] != league["id"]:
        raise HTTPException(
            422, f"team {team_id} is not in league {league['id']}")
    if team_id != _commissioner_team_id(con, league):
        raise HTTPException(
            403, f"only the commissioner's team can {action}")
    return actor


@router.get("/{league_id}/messages",
            response_model=schemas.MessageBoardOut)
def list_messages(league_id: int, limit: int = Query(50, ge=1, le=100),
                  offset: int = Query(0, ge=0),
                  con: sqlite3.Connection = Depends(get_db)):
    """Newest first, soft-deleted posts excluded. The pinned post (if
    any) is returned separately as `pinned_message` and excluded from
    the feed so it renders in the strip above it. `total` counts the
    visible feed posts so the UI can page older ones in."""
    league = get_league(con, league_id)  # 404 if missing
    pinned = _pinned_row(con, league_id)
    pinned_id = pinned["id"] if pinned else None
    total = con.execute(
        "SELECT COUNT(*) FROM league_messages"
        " WHERE league_id = ? AND deleted_at IS NULL"
        " AND (? IS NULL OR id != ?)",
        (league_id, pinned_id, pinned_id)).fetchone()[0]
    rows = con.execute(
        "SELECT * FROM league_messages"
        " WHERE league_id = ? AND deleted_at IS NULL"
        " AND (? IS NULL OR id != ?)"
        " ORDER BY id DESC LIMIT ? OFFSET ?",
        (league_id, pinned_id, pinned_id, limit, offset)).fetchall()
    return schemas.MessageBoardOut(
        league_id=league_id,
        commissioner_team_id=_commissioner_team_id(con, league),
        total=total,
        pinned_message=_out(con, pinned) if pinned else None,
        messages=[_out(con, r) for r in rows])


@router.post("/{league_id}/messages", status_code=201,
             response_model=schemas.MessageOut)
def post_message(league_id: int, body: schemas.MessageCreate,
                 request: Request,
                 con: sqlite3.Connection = Depends(get_db)):
    """Post as a team. Claim-aware: a claimed team needs its code."""
    get_league(con, league_id)  # 404 if missing
    team = require_team_actor(con, body.team_id, request)  # P4-W18 gate
    if team["league_id"] != league_id:
        raise HTTPException(
            422, f"team {body.team_id} is not in league {league_id}")
    text = body.body.strip()
    if not text:
        raise HTTPException(422, "message body must not be empty")
    cur = con.execute(
        "INSERT INTO league_messages (league_id, team_id, body)"
        " VALUES (?, ?, ?)", (league_id, body.team_id, text))
    con.commit()
    row = con.execute(
        "SELECT * FROM league_messages WHERE id = ?",
        (cur.lastrowid,)).fetchone()
    return _out(con, row)


@router.delete("/{league_id}/messages/{message_id}", status_code=204)
def delete_message(league_id: int, message_id: int, request: Request,
                   team_id: int = Query(...),
                   con: sqlite3.Connection = Depends(get_db)):
    """Commissioner soft-delete. The acting team must be the
    commissioner's team (and pass the P4-W18 claim gate). Deleting a
    pinned post clears the strip (soft-deleted rows never count as
    pinned)."""
    league = get_league(con, league_id)  # 404 if missing
    _require_commissioner_actor(con, league, team_id, request, "remove board posts")
    row = con.execute(
        "SELECT id FROM league_messages"
        " WHERE id = ? AND league_id = ? AND deleted_at IS NULL",
        (message_id, league_id)).fetchone()
    if not row:
        raise HTTPException(404, f"message {message_id} not found")
    con.execute(
        "UPDATE league_messages SET deleted_at = datetime('now')"
        " WHERE id = ?", (message_id,))
    con.commit()
    return Response(status_code=204)


@router.post("/{league_id}/messages/{message_id}/pin",
             response_model=schemas.MessageOut)
def pin_message(league_id: int, message_id: int, request: Request,
                team_id: int = Query(...),
                con: sqlite3.Connection = Depends(get_db)):
    """Pin a commissioner announcement (P5-W39). Only the
    commissioner's team (P4-W18 claim gate) can pin, and only its OWN
    posts are pinnable. One active pin per league: pinning a new post
    unpins the old one. Deleted posts cannot be pinned."""
    league = get_league(con, league_id)  # 404 if missing
    _require_commissioner_actor(con, league, team_id, request, "pin board posts")
    comm_team = _commissioner_team_id(con, league)
    row = con.execute(
        "SELECT * FROM league_messages"
        " WHERE id = ? AND league_id = ? AND deleted_at IS NULL",
        (message_id, league_id)).fetchone()
    if not row:
        raise HTTPException(404, f"message {message_id} not found")
    if row["team_id"] != comm_team:
        raise HTTPException(
            422, "only the commissioner's own posts can be pinned")
    con.execute(
        "UPDATE league_messages SET pinned_at = NULL"
        " WHERE league_id = ? AND pinned_at IS NOT NULL",
        (league_id,))
    con.execute(
        "UPDATE league_messages SET pinned_at = datetime('now')"
        " WHERE id = ?", (message_id,))
    con.commit()
    row = con.execute(
        "SELECT * FROM league_messages WHERE id = ?",
        (message_id,)).fetchone()
    return _out(con, row)


@router.post("/{league_id}/messages/{message_id}/unpin",
             response_model=schemas.MessageOut)
def unpin_message(league_id: int, message_id: int, request: Request,
                  team_id: int = Query(...),
                  con: sqlite3.Connection = Depends(get_db)):
    """Unpin the commissioner's announcement (P5-W39). Only the
    commissioner's team can unpin; the post returns to normal feed
    order. A no-op on an already-unpinned post is a 422."""
    league = get_league(con, league_id)  # 404 if missing
    _require_commissioner_actor(con, league, team_id, request, "unpin board posts")
    row = con.execute(
        "SELECT * FROM league_messages"
        " WHERE id = ? AND league_id = ? AND deleted_at IS NULL",
        (message_id, league_id)).fetchone()
    if not row:
        raise HTTPException(404, f"message {message_id} not found")
    if row["pinned_at"] is None:
        raise HTTPException(422, f"message {message_id} is not pinned")
    con.execute("UPDATE league_messages SET pinned_at = NULL WHERE id = ?",
                (message_id,))
    con.commit()
    row = con.execute(
        "SELECT * FROM league_messages WHERE id = ?",
        (message_id,)).fetchone()
    return _out(con, row)
