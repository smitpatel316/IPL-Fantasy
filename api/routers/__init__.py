"""Shared router helpers: row mapping, 404s, league lookups."""

import hmac
import json
import secrets
import sqlite3
import string

from fastapi import HTTPException, Request


def new_claim_code() -> str:
    """A fresh per-team claim code (P4-W18)."""
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(10))


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


def require_team_actor(con: sqlite3.Connection, team_id: int, request: Request) -> dict:
    """Lightweight team identity (P4-W18): once a team is CLAIMED (has a
    claim code), team-scoped mutations must present that code in the
    X-Team-Claim header. Unclaimed teams stay honor-system so existing
    leagues keep working until their managers claim them."""
    team = get_team(con, team_id)
    code = team.get("claim_code")
    if code:
        sent = request.headers.get("x-team-claim", "")
        if not hmac.compare_digest(sent, code):
            raise HTTPException(
                403,
                f"team '{team['name']}' is claimed — its claim code is "
                "required to act for it (X-Team-Claim header)",
            )
    return team


def player_roles_map(con: sqlite3.Connection, season: str = "2027") -> dict[int, dict]:
    """player_id -> {role, is_overseas, ipl_team_code, status, il_eligible}.

    IL eligibility (D7, P4-W4): a player is IL-eligible when their
    curated status designates them out ('retired' | 'injured' | 'out' —
    i.e. any status other than NULL/'active'): they have missed or are
    expected to miss a game. The status column is read defensively —
    DBs created before it existed simply have nobody eligible.
    """
    cols = {r["name"] for r in con.execute("PRAGMA table_info(player_roles)")}
    status_expr = "status" if "status" in cols else "NULL AS status"
    out: dict[int, dict] = {}
    for r in con.execute(
        f"SELECT player_id, role, is_overseas, ipl_team_code, {status_expr}"
        " FROM player_roles WHERE season = ?",
        (season,),
    ):
        status = r["status"]
        out[r["player_id"]] = {
            "role": r["role"],
            "is_overseas": bool(r["is_overseas"]),
            "ipl_team_code": r["ipl_team_code"],
            "status": status,
            "il_eligible": bool(status) and status.strip().lower() != "active",
            "availability": availability_from_status(status),
        }
    return out


def availability_from_status(status: str | None) -> str:
    """P5-W6: coarse availability for the lineup/players dots, derived
    from the curated player_roles.status (the same designation P4-W4
    uses for IL eligibility) until the live poller lands:
      NULL/'active' -> 'active' (green)
      'retired'     -> 'retired' (greyed)
      anything else ('injured', 'out', ...) -> 'out' (red): the player
      has missed or is expected to miss a game."""
    if not status:
        return "active"
    s = status.strip().lower()
    if s == "active":
        return "active"
    if s == "retired":
        return "retired"
    return "out"


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


def avg_points_map(con: sqlite3.Connection) -> dict[int, float]:
    """Average fantasy points per player from scored matches (empty
    until the scoring pipeline lands rows in player_match_stats)."""
    return {
        r["player_id"]: round(r["a"], 1)
        for r in con.execute(
            "SELECT player_id, AVG(fantasy_points) AS a FROM player_match_stats"
            " WHERE player_id IS NOT NULL GROUP BY player_id")
    }


def ownership_pct_map(con: sqlite3.Connection) -> dict[int, float]:
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
