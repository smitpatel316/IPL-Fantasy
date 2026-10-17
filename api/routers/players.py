"""Players: draft universe + roles + ranks + ownership (read-only in v1)."""

import json
import sqlite3
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from .. import schedule_games, schemas, services
from ..constants import TOTAL_WEEKS
from ..database import get_db
from . import (
    availability_from_status,
    avg_points_map,
    get_league,
    owned_map,
    ownership_pct_map,
)

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
    get_league(con, league_id)  # 404 for an unknown league (P4-W10)
    owned = owned_map(con, league_id)
    sql = """SELECT p.id, p.name, p.season, pr.role, pr.is_overseas, pr.ipl_team_code,
                    pr.status,
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
    avgs = avg_points_map(con)
    own_pct = ownership_pct_map(con)
    out = []
    for r in con.execute(sql, params):
        out.append(schemas.PlayerOut(
            id=r["id"], name=r["name"], season=r["season"], role=r["role"],
            is_overseas=bool(r["is_overseas"] or 0),
            ipl_team_code=r["ipl_team_code"], preseason_rank=r["preseason_rank"],
            owned_by_team_id=owned.get(r["id"]),
            availability=availability_from_status(r["status"]),
            avg_points=avgs.get(r["id"]),
            ownership_pct=own_pct.get(r["id"], 0.0),
        ))
    return out


@router.get("/compare", response_model=schemas.PlayerCompareOut)
def compare_players(
    league_id: int = Query(...),
    ids: str = Query(..., description="comma-separated player ids (2-3)"),
    con: sqlite3.Connection = Depends(get_db),
):
    """P5-W14 player compare: 2-3 players side by side. Every value is
    the same projection the list/detail endpoints serve (role, IPL
    team, overseas, preseason rank in this league, avg points,
    ownership %, availability) plus games over the next 3 fantasy
    weeks from the schedule-nudges table. Read-only; entries return in
    the order requested. Declared before /{player_id} so 'compare' is
    not parsed as a player id."""
    league = get_league(con, league_id)  # 404 for an unknown league
    try:
        wanted = [int(x) for x in ids.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(422, "ids must be comma-separated player ids")
    if not 2 <= len(wanted) <= 3 or len(set(wanted)) != len(wanted):
        raise HTTPException(422, "compare needs 2-3 distinct player ids")
    week = services.current_week(con, league_id)
    weeks = list(range(week, min(week + 3, TOTAL_WEEKS + 1)))
    games_by_code: dict[str, int] = {}
    fixture_seen = False
    for wk in weeks:
        data = schedule_games.fetch_week(con, league["season"], wk)
        for g in data["games"]:
            fixture_seen = True
            games_by_code[g["ipl_team_code"]] = (
                games_by_code.get(g["ipl_team_code"], 0) + g["games"])
    owned = owned_map(con, league_id)
    avgs = avg_points_map(con)
    own_pct = ownership_pct_map(con)
    entries = []
    for pid in wanted:
        row = con.execute(
            """SELECT p.id, p.name, p.season, pr.role, pr.is_overseas,
                      pr.ipl_team_code, pr.status,
                      (SELECT MIN(rank) FROM pre_draft_ranks r
                       JOIN teams t ON t.id = r.team_id
                       WHERE r.player_id = p.id AND t.league_id = ?) AS preseason_rank
               FROM players p LEFT JOIN player_roles pr
                 ON pr.player_id = p.id AND pr.season = p.season
               WHERE p.id = ?""",
            (league_id, pid),
        ).fetchone()
        if not row:
            raise HTTPException(404, f"player {pid} not found")
        code = row["ipl_team_code"]
        entries.append(schemas.PlayerCompareEntryOut(
            id=row["id"], name=row["name"], season=row["season"],
            role=row["role"], is_overseas=bool(row["is_overseas"] or 0),
            ipl_team_code=code, preseason_rank=row["preseason_rank"],
            owned_by_team_id=owned.get(row["id"]),
            availability=availability_from_status(row["status"]),
            avg_points=avgs.get(row["id"]),
            ownership_pct=own_pct.get(row["id"], 0.0),
            games_next_3_weeks=(
                games_by_code.get(code, 0)
                if fixture_seen and code else None),
        ))
    return schemas.PlayerCompareOut(
        league_id=league_id, current_week=week, weeks=weeks,
        players=entries)


@router.get("/{player_id}", response_model=schemas.PlayerDetailOut)
def get_player(player_id: int, league_id: int = Query(...),
               con: sqlite3.Connection = Depends(get_db)):
    """Player detail (P4-W19): identity + preseason rank, ownership in
    every league, and the match-by-match scoring log (empty until the
    scoring pipeline lands). preseason_rank/owner are read in the
    context of `league_id`, like the list."""
    row = con.execute(
        """SELECT p.id, p.name, p.season, pr.role, pr.is_overseas, pr.ipl_team_code,
                  pr.status,
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
    avgs = avg_points_map(con)
    own_pct = ownership_pct_map(con)
    return schemas.PlayerDetailOut(
        id=row["id"], name=row["name"], season=row["season"], role=row["role"],
        is_overseas=bool(row["is_overseas"] or 0),
        ipl_team_code=row["ipl_team_code"], preseason_rank=row["preseason_rank"],
        owned_by_team_id=owned_map(con, league_id).get(player_id),
        availability=availability_from_status(row["status"]),
        avg_points=avgs.get(player_id),
        ownership_pct=own_pct.get(player_id, 0.0),
        owners=owners,
        matches_played=len(log),
        total_points=sum(e.fantasy_points for e in log),
        match_log=log,
    )
