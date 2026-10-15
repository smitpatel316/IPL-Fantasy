"""Player watchlist (P5-W2): per-team starred players.

A manager stars players from the players list or the waiver wire and
gets a "Watched" section on the players page with ownership %, avg
points, and schedule badges. Persisted per league+team in the
`watchlist` table. Reads are open to anyone; writes are claim-aware —
once a team is claimed, X-Team-Claim must match (require_team_actor,
P4-W18), exactly like lineup/waiver/trade mutations.

Entry rows extend PlayerOut and derive ownership % / avg points from
the same shared maps as the players list, so the watched section's
numbers always agree with the list.
"""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from .. import schemas
from ..database import get_db
from . import (
    avg_points_map,
    get_league,
    get_team,
    owned_map,
    ownership_pct_map,
    require_team_actor,
)

router = APIRouter()


def _entry(con: sqlite3.Connection, row: sqlite3.Row,
           owned: dict[int, int], avgs: dict[int, float],
           own_pct: dict[int, float]) -> schemas.WatchlistEntryOut:
    pid = row["player_id"]
    return schemas.WatchlistEntryOut(
        id=pid, name=row["name"], season=row["season"], role=row["role"],
        is_overseas=bool(row["is_overseas"] or 0),
        ipl_team_code=row["ipl_team_code"],
        preseason_rank=row["preseason_rank"],
        owned_by_team_id=owned.get(pid),
        avg_points=avgs.get(pid),
        ownership_pct=own_pct.get(pid, 0.0),
        watch_id=row["id"], league_id=row["league_id"],
        team_id=row["team_id"], created_at=row["created_at"],
    )


def _rows(con: sqlite3.Connection, league_id: int,
          team_id: int) -> list[schemas.WatchlistEntryOut]:
    """Every watched player for (league, team), most recently starred
    first. The rank subquery matches the players list (P4-W19)."""
    league = get_league(con, league_id)
    owned = owned_map(con, league_id)
    avgs = avg_points_map(con)
    own_pct = ownership_pct_map(con)
    rows = con.execute(
        """SELECT w.id, w.league_id, w.team_id, w.player_id, w.created_at,
                  p.name, p.season, pr.role, pr.is_overseas, pr.ipl_team_code,
                  (SELECT MIN(rank) FROM pre_draft_ranks r
                   JOIN teams t ON t.id = r.team_id
                   WHERE r.player_id = p.id AND t.league_id = :league_id)
                      AS preseason_rank
           FROM watchlist w
           JOIN players p ON p.id = w.player_id
           LEFT JOIN player_roles pr
             ON pr.player_id = p.id AND pr.season = p.season
           WHERE w.league_id = :league_id AND w.team_id = :team_id
             AND p.season = :season
           ORDER BY w.id DESC""",
        {"league_id": league_id, "team_id": team_id,
         "season": league["season"]},
    ).fetchall()
    return [_entry(con, r, owned, avgs, own_pct) for r in rows]


@router.get("", response_model=list[schemas.WatchlistEntryOut])
def list_watchlist(league_id: int = Query(...), team_id: int = Query(...),
                   con: sqlite3.Connection = Depends(get_db)):
    """Read is open (like every other read endpoint); unknown league
    or team 404s."""
    get_league(con, league_id)
    team = get_team(con, team_id)
    if team["league_id"] != league_id:
        raise HTTPException(422, f"team {team_id} is not in league {league_id}")
    return _rows(con, league_id, team_id)


@router.post("", response_model=schemas.WatchlistEntryOut)
def star_player(body: schemas.WatchlistCreate, request: Request,
                con: sqlite3.Connection = Depends(get_db)):
    """Star a player for the acting team. Idempotent: re-starring an
    already-watched player returns the existing row unchanged."""
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
    con.execute(
        "INSERT OR IGNORE INTO watchlist (league_id, team_id, player_id)"
        " VALUES (?, ?, ?)",
        (body.league_id, body.team_id, body.player_id))
    con.commit()
    for entry in _rows(con, body.league_id, body.team_id):
        if entry.id == body.player_id:
            return entry
    raise HTTPException(500, "star was not persisted")  # pragma: no cover


@router.delete("", status_code=204)
def unstar_player(request: Request, league_id: int = Query(...),
                  team_id: int = Query(...), player_id: int = Query(...),
                  con: sqlite3.Connection = Depends(get_db)):
    """Unstar a player. Idempotent: removing a player who isn't
    starred is still a 204 — the end state is identical."""
    get_league(con, league_id)
    team = require_team_actor(con, team_id, request)  # P4-W18 gate
    if team["league_id"] != league_id:
        raise HTTPException(422, f"team {team_id} is not in league {league_id}")
    con.execute(
        "DELETE FROM watchlist WHERE league_id = ? AND team_id = ?"
        " AND player_id = ?",
        (league_id, team_id, player_id))
    con.commit()
    return Response(status_code=204)
