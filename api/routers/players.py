"""Players: draft universe + roles + ranks + ownership (read-only in v1)."""

import sqlite3
from typing import Optional

from fastapi import APIRouter, Depends, Query

from .. import schemas
from ..database import get_db
from . import owned_map

router = APIRouter()


@router.get("", response_model=list[schemas.PlayerOut])
def list_players(
    league_id: int = Query(...),
    season: str = Query("2027"),
    role: Optional[str] = Query(None, pattern="^(WK|BAT|AR|BOWL)$"),
    team: Optional[str] = Query(None, description="IPL team code, e.g. MI"),
    q: Optional[str] = Query(None, description="name substring"),
    con: sqlite3.Connection = Depends(get_db),
):
    owned = owned_map(con, league_id)
    sql = """SELECT p.id, p.name, p.season, pr.role, pr.is_overseas, pr.ipl_team_code,
                    (SELECT MIN(rank) FROM pre_draft_ranks r
                     JOIN teams t ON t.id = r.team_id
                     WHERE r.player_id = p.id AND t.league_id = :league_id) AS preseason_rank
             FROM players p LEFT JOIN player_roles pr
               ON pr.player_id = p.id AND pr.season = p.season
             WHERE p.season = :season"""
    params: dict = {"league_id": league_id, "season": season}
    if role:
        sql += " AND pr.role = :role"
        params["role"] = role
    if team:
        sql += " AND pr.ipl_team_code = :team"
        params["team"] = team
    if q:
        sql += " AND p.name LIKE :q"
        params["q"] = f"%{q}%"
    sql += " ORDER BY preseason_rank NULLS LAST, p.name"
    out = []
    for r in con.execute(sql, params):
        out.append(schemas.PlayerOut(
            id=r["id"], name=r["name"], season=r["season"], role=r["role"],
            is_overseas=bool(r["is_overseas"] or 0),
            ipl_team_code=r["ipl_team_code"], preseason_rank=r["preseason_rank"],
            owned_by_team_id=owned.get(r["id"]),
        ))
    return out
