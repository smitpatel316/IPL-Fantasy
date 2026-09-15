"""Shared router helpers: row mapping, 404s, league lookups."""

import json
import sqlite3

from fastapi import HTTPException


def row_dict(row: sqlite3.Row) -> dict:
    return dict(row)


def get_league(con: sqlite3.Connection, league_id: int) -> dict:
    row = con.execute("SELECT * FROM leagues WHERE id = ?", (league_id,)).fetchone()
    if not row:
        raise HTTPException(404, f"league {league_id} not found")
    d = row_dict(row)
    d["settings"] = json.loads(d["settings"] or "{}")
    return d


def get_team(con: sqlite3.Connection, team_id: int) -> dict:
    row = con.execute(
        """SELECT t.*, u.name AS owner_name FROM teams t
           LEFT JOIN users u ON u.id = t.owner_id WHERE t.id = ?""",
        (team_id,),
    ).fetchone()
    if not row:
        raise HTTPException(404, f"team {team_id} not found")
    return row_dict(row)


def player_roles_map(con: sqlite3.Connection, season: str = "2027") -> dict[int, dict]:
    """player_id -> {role, is_overseas, ipl_team_code} for lineup validation."""
    out: dict[int, dict] = {}
    for r in con.execute(
        "SELECT player_id, role, is_overseas, ipl_team_code FROM player_roles WHERE season = ?",
        (season,),
    ):
        out[r["player_id"]] = {
            "role": r["role"],
            "is_overseas": bool(r["is_overseas"]),
            "ipl_team_code": r["ipl_team_code"],
        }
    return out


def owned_map(con: sqlite3.Connection, league_id: int) -> dict[int, int]:
    """player_id -> team_id for exclusive ownership (blueprint §5 integrity rule)."""
    out: dict[int, int] = {}
    for r in con.execute(
        """SELECT rs.player_id, rs.team_id FROM roster_slots rs
           JOIN teams t ON t.id = rs.team_id
           WHERE t.league_id = ? AND rs.week_no IS NULL""",
        (league_id,),
    ):
        out[r["player_id"]] = r["team_id"]
    return out
