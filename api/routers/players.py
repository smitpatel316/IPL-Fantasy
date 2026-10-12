"""Players: draft universe + roles + ranks + ownership (read-only in v1)."""

import json
import sqlite3
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from .. import schemas
from ..database import get_db
from . import owned_map

router = APIRouter()


def _avg_points(con: sqlite3.Connection) -> dict[int, float]:
    """Average fantasy points per player from scored matches (empty
    until the scoring pipeline lands rows in player_match_stats)."""
    return {
        r["player_id"]: round(r["a"], 1)
        for r in con.execute(
            "SELECT player_id, AVG(fantasy_points) AS a FROM player_match_stats"
            " WHERE player_id IS NOT NULL GROUP BY player_id")
    }


def _ownership_pct(con: sqlite3.Connection) -> dict[int, float]:
    """Per player: % of leagues where they sit on a construction roster."""
    total = con.execute("SELECT COUNT(*) FROM leagues").fetchone()[0]
    if not total:
        return {}
    return {
        r["player_id"]: round(100.0 * r["n"] / total, 1)
        for r in con.execute(
            """SELECT rs.player_id, COUNT(DISTINCT t.league_id) AS n
               FROM roster_slots rs JOIN teams t ON t.id = rs.team_id
               WHERE rs.week_no IS NULL GROUP BY rs.player_id""")
    }


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
    avgs = _avg_points(con)
    own_pct = _ownership_pct(con)
    out = []
    for r in con.execute(sql, params):
        out.append(schemas.PlayerOut(
            id=r["id"], name=r["name"], season=r["season"], role=r["role"],
            is_overseas=bool(r["is_overseas"] or 0),
            ipl_team_code=r["ipl_team_code"], preseason_rank=r["preseason_rank"],
            owned_by_team_id=owned.get(r["id"]),
            avg_points=avgs.get(r["id"]),
            ownership_pct=own_pct.get(r["id"], 0.0),
        ))
    return out


@router.get("/{player_id}", response_model=schemas.PlayerDetailOut)
def get_player(player_id: int, league_id: int = Query(...),
               con: sqlite3.Connection = Depends(get_db)):
    """Player detail (P4-W19): identity + preseason rank, ownership in
    every league, and the match-by-match scoring log (empty until the
    scoring pipeline lands). preseason_rank/owner are read in the
    context of `league_id`, like the list."""
    row = con.execute(
        """SELECT p.id, p.name, p.season, pr.role, pr.is_overseas, pr.ipl_team_code,
                  (SELECT MIN(rank) FROM pre_draft_ranks r
                   JOIN teams t ON t.id = r.team_id
                   WHERE r.player_id = p.id AND t.league_id = ?) AS preseason_rank
           FROM players p LEFT JOIN player_roles pr
             ON pr.player_id = p.id AND pr.season = p.season
           WHERE p.id = ?""",
        (league_id, player_id),
    ).fetchone()
    if not row:
        raise HTTPException(404, f"player {player_id} not found")
    owners = [
        schemas.PlayerOwnerOut(
            league_id=r["league_id"], league_name=r["league_name"],
            team_id=r["team_id"], team_name=r["team_name"])
        for r in con.execute(
            """SELECT t.league_id, l.name AS league_name, t.id AS team_id,
                      t.name AS team_name
               FROM roster_slots rs
               JOIN teams t ON t.id = rs.team_id
               JOIN leagues l ON l.id = t.league_id
               WHERE rs.player_id = ? AND rs.week_no IS NULL
               ORDER BY t.league_id""",
            (player_id,))
    ]
    log = [
        schemas.PlayerMatchLogOut(
            match_id=r["match_id"], week_no=r["week_no"],
            match_date_ist=r["match_date_ist"], home_code=r["home_code"],
            away_code=r["away_code"], fantasy_points=r["fantasy_points"],
            breakdown=json.loads(r["breakdown"] or "{}"))
        for r in con.execute(
            """SELECT s.match_id, m.week_no, m.match_date_ist, m.home_code,
                      m.away_code, s.fantasy_points, s.breakdown
               FROM player_match_stats s JOIN matches m ON m.id = s.match_id
               WHERE s.player_id = ?
               ORDER BY m.match_date_ist, s.match_id""",
            (player_id,))
    ]
    avgs = _avg_points(con)
    own_pct = _ownership_pct(con)
    return schemas.PlayerDetailOut(
        id=row["id"], name=row["name"], season=row["season"], role=row["role"],
        is_overseas=bool(row["is_overseas"] or 0),
        ipl_team_code=row["ipl_team_code"], preseason_rank=row["preseason_rank"],
        owned_by_team_id=owned_map(con, league_id).get(player_id),
        avg_points=avgs.get(player_id),
        ownership_pct=own_pct.get(player_id, 0.0),
        owners=owners,
        matches_played=len(log),
        total_points=sum(e.fantasy_points for e in log),
        match_log=log,
    )
