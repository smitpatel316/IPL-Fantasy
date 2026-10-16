"""Private player notes (P5-W17): per-team free-text notes on players.

Privacy is the feature: a note is keyed by (league, team, player) and
EVERY endpoint is gated by require_team_actor (P4-W18) — once a team
is claimed, only a request carrying that team's claim code can read
or write its notes, so a second team in the same league sees no trace
of them in any response. Notes are deliberately NOT projected into
the players list/detail, the activity feed, or the message board.
Unclaimed teams stay honor-system, like every other v1 surface.
"""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from .. import schemas
from ..database import get_db
from . import get_league, get_team, require_team_actor

router = APIRouter()

MAX_NOTE_LEN = 500


def _out(row: sqlite3.Row) -> schemas.PlayerNoteOut:
    return schemas.PlayerNoteOut(
        id=row["id"], league_id=row["league_id"], team_id=row["team_id"],
        player_id=row["player_id"], player_name=row["player_name"],
        note=row["note"], updated_at=row["updated_at"])


@router.get("", response_model=list[schemas.PlayerNoteOut])
def list_notes(league_id: int = Query(...), team_id: int = Query(...),
               request: Request = None,
               con: sqlite3.Connection = Depends(get_db)):
    """All of THIS team's notes in the league — and only this team's."""
    get_league(con, league_id)
    team = require_team_actor(con, team_id, request)
    if team["league_id"] != league_id:
        raise HTTPException(422, f"team {team_id} is not in league {league_id}")
    rows = con.execute(
        """SELECT n.*, p.name AS player_name FROM player_notes n
           JOIN players p ON p.id = n.player_id
           WHERE n.league_id = ? AND n.team_id = ?
           ORDER BY n.updated_at DESC, n.id DESC""",
        (league_id, team_id)).fetchall()
    return [_out(r) for r in rows]


@router.put("", response_model=schemas.PlayerNoteOut)
def upsert_note(body: schemas.PlayerNoteUpsert, request: Request,
                con: sqlite3.Connection = Depends(get_db)):
    """Create or replace the team's note on a player (one per player)."""
    get_league(con, body.league_id)
    team = require_team_actor(con, body.team_id, request)
    if team["league_id"] != body.league_id:
        raise HTTPException(
            422, f"team {body.team_id} is not in league {body.league_id}")
    note = body.note.strip()
    if not note:
        raise HTTPException(422, "note must not be empty (DELETE clears a note)")
    if len(note) > MAX_NOTE_LEN:
        raise HTTPException(422, f"note is capped at {MAX_NOTE_LEN} characters")
    if not con.execute("SELECT 1 FROM players WHERE id = ?",
                       (body.player_id,)).fetchone():
        raise HTTPException(404, f"player {body.player_id} not found")
    con.execute(
        """INSERT INTO player_notes (league_id, team_id, player_id, note)
           VALUES (?, ?, ?, ?)
           ON CONFLICT (league_id, team_id, player_id)
           DO UPDATE SET note = excluded.note,
                         updated_at = datetime('now')""",
        (body.league_id, body.team_id, body.player_id, note))
    con.commit()
    row = con.execute(
        """SELECT n.*, p.name AS player_name FROM player_notes n
           JOIN players p ON p.id = n.player_id
           WHERE n.league_id = ? AND n.team_id = ? AND n.player_id = ?""",
        (body.league_id, body.team_id, body.player_id)).fetchone()
    return _out(row)


@router.delete("", status_code=204)
def delete_note(league_id: int = Query(...), team_id: int = Query(...),
                player_id: int = Query(...), request: Request = None,
                con: sqlite3.Connection = Depends(get_db)):
    """Remove the team's note on a player (idempotent)."""
    get_league(con, league_id)
    team = require_team_actor(con, team_id, request)
    if team["league_id"] != league_id:
        raise HTTPException(422, f"team {team_id} is not in league {league_id}")
    con.execute(
        "DELETE FROM player_notes WHERE league_id = ? AND team_id = ?"
        " AND player_id = ?", (league_id, team_id, player_id))
    con.commit()
    return Response(status_code=204)
