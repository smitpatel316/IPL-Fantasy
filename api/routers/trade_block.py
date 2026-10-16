"""Trade block (P5-W7): the league-wide "on the block" board.

A manager marks their own rostered players as available and adds a
short "seeking" note ("want a BOWL, will move a BAT"). Listings are
persisted per league+team in the `trade_block` table and are
claim-aware (P4-W18): only the owning team's actor can post or remove
its listings; every other team's listings are read-only. Reads are
open, like every other read endpoint.

Auto-expire: a listing lives only while the player is on the listing
team's construction roster (owned_map). When the player leaves —
trade, waiver drop, commissioner move — the read path prunes the row
and it disappears from the board.
"""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from .. import schemas
from ..database import get_db
from . import availability_from_status, get_league, get_team, owned_map, require_team_actor

router = APIRouter()


def _prune_stale(con: sqlite3.Connection, league_id: int) -> None:
    """Drop listings whose player is no longer on the listing team's
    roster (auto-expire). Runs on the read path so the board never
    shows a player who has already moved."""
    owned = owned_map(con, league_id)
    stale = [
        r["id"]
        for r in con.execute(
            "SELECT id, team_id, player_id FROM trade_block WHERE league_id = ?",
            (league_id,),
        )
        if owned.get(r["player_id"]) != r["team_id"]
    ]
    if stale:
        con.executemany("DELETE FROM trade_block WHERE id = ?",
                        [(i,) for i in stale])
        con.commit()


def _rows(con: sqlite3.Connection,
          league_id: int) -> list[schemas.TradeBlockEntryOut]:
    league = get_league(con, league_id)
    rows = con.execute(
        """SELECT tb.id, tb.league_id, tb.team_id, tb.player_id,
                  tb.seeking, tb.created_at, tb.updated_at,
                  t.name AS team_name,
                  p.name, p.season, pr.role, pr.is_overseas,
                  pr.ipl_team_code, pr.status,
                  (SELECT MIN(rank) FROM pre_draft_ranks r
                   JOIN teams t2 ON t2.id = r.team_id
                   WHERE r.player_id = p.id AND t2.league_id = :league_id)
                      AS preseason_rank
           FROM trade_block tb
           JOIN teams t ON t.id = tb.team_id
           JOIN players p ON p.id = tb.player_id
           LEFT JOIN player_roles pr
             ON pr.player_id = p.id AND pr.season = p.season
           WHERE tb.league_id = :league_id AND p.season = :season
           ORDER BY tb.id DESC""",
        {"league_id": league_id, "season": league["season"]},
    ).fetchall()
    return [
        schemas.TradeBlockEntryOut(
            id=r["id"], league_id=r["league_id"], team_id=r["team_id"],
            team_name=r["team_name"], player_id=r["player_id"],
            name=r["name"], season=r["season"], role=r["role"],
            is_overseas=bool(r["is_overseas"] or 0),
            ipl_team_code=r["ipl_team_code"],
            preseason_rank=r["preseason_rank"],
            availability=availability_from_status(r["status"]),
            seeking=r["seeking"], created_at=r["created_at"],
            updated_at=r["updated_at"],
        )
        for r in rows
    ]


@router.get("", response_model=list[schemas.TradeBlockEntryOut])
def list_trade_block(league_id: int = Query(...),
                     con: sqlite3.Connection = Depends(get_db)):
    """The whole league's block, newest listing first. Open read."""
    get_league(con, league_id)  # 404 if missing
    _prune_stale(con, league_id)
    return _rows(con, league_id)


@router.post("", response_model=schemas.TradeBlockEntryOut)
def post_listing(body: schemas.TradeBlockCreate, request: Request,
                 con: sqlite3.Connection = Depends(get_db)):
    """Put one of your own rostered players on the block (or update
    the seeking note). Upsert: re-posting the same player refreshes
    `seeking` and returns the same listing id."""
    league = get_league(con, body.league_id)
    team = require_team_actor(con, body.team_id, request)  # P4-W18 gate
    if team["league_id"] != body.league_id:
        raise HTTPException(
            422, f"team {body.team_id} is not in league {body.league_id}")
    prow = con.execute("SELECT season FROM players WHERE id = ?",
                       (body.player_id,)).fetchone()
    if not prow:
        raise HTTPException(404, f"player {body.player_id} not found")
    if prow["season"] != league["season"]:
        raise HTTPException(
            422, f"player {body.player_id} is not a {league['season']} player")
    owner = owned_map(con, body.league_id).get(body.player_id)
    if owner != body.team_id:
        raise HTTPException(
            422, "only players on your own roster can go on the block")
    con.execute(
        """INSERT INTO trade_block (league_id, team_id, player_id, seeking)
           VALUES (?, ?, ?, ?)
           ON CONFLICT (league_id, team_id, player_id)
           DO UPDATE SET seeking = excluded.seeking,
                         updated_at = datetime('now')""",
        (body.league_id, body.team_id, body.player_id, body.seeking.strip()))
    con.commit()
    for entry in _rows(con, body.league_id):
        if entry.player_id == body.player_id and entry.team_id == body.team_id:
            return entry
    raise HTTPException(500, "listing was not persisted")  # pragma: no cover


@router.delete("", status_code=204)
def remove_listing(request: Request, league_id: int = Query(...),
                   team_id: int = Query(...), player_id: int = Query(...),
                   con: sqlite3.Connection = Depends(get_db)):
    """Take your own player off the block. Idempotent: removing a
    player who isn't listed is still a 204."""
    get_league(con, league_id)
    team = require_team_actor(con, team_id, request)  # P4-W18 gate
    if team["league_id"] != league_id:
        raise HTTPException(422, f"team {team_id} is not in league {league_id}")
    con.execute(
        "DELETE FROM trade_block WHERE league_id = ? AND team_id = ?"
        " AND player_id = ?",
        (league_id, team_id, player_id))
    con.commit()
    return Response(status_code=204)
