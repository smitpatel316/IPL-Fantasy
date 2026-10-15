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
    return schemas.MessageOut(
        id=row["id"], league_id=row["league_id"], team_id=row["team_id"],
        team_name=team["name"] if team else "",
        body=row["body"], created_at=row["created_at"])


@router.get("/{league_id}/messages",
            response_model=schemas.MessageBoardOut)
def list_messages(league_id: int, limit: int = Query(50, ge=1, le=100),
                  offset: int = Query(0, ge=0),
                  con: sqlite3.Connection = Depends(get_db)):
    """Newest first, soft-deleted posts excluded. `total` counts the
    visible posts so the UI can page older ones in."""
    league = get_league(con, league_id)  # 404 if missing
    total = con.execute(
        "SELECT COUNT(*) FROM league_messages"
        " WHERE league_id = ? AND deleted_at IS NULL",
        (league_id,)).fetchone()[0]
    rows = con.execute(
        "SELECT * FROM league_messages"
        " WHERE league_id = ? AND deleted_at IS NULL"
        " ORDER BY id DESC LIMIT ? OFFSET ?",
        (league_id, limit, offset)).fetchall()
    return schemas.MessageBoardOut(
        league_id=league_id,
        commissioner_team_id=_commissioner_team_id(con, league),
        total=total, messages=[_out(con, r) for r in rows])


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
    commissioner's team (and pass the P4-W18 claim gate)."""
    league = get_league(con, league_id)  # 404 if missing
    actor = require_team_actor(con, team_id, request)
    if actor["league_id"] != league_id:
        raise HTTPException(
            422, f"team {team_id} is not in league {league_id}")
    if team_id != _commissioner_team_id(con, league):
        raise HTTPException(
            403, "only the commissioner's team can remove board posts")
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
