"""Custom pre-draft ranks (P4-W17): per-team ordered player lists the
draft engine's auto-pick follows. Read/write here; the engine reads
them at draft build/revive, and a write during a live draft refreshes
the running draft's in-memory ranks (services.set_team_ranks).

P5-W31: CSV import/export for the same ranks. Export renders the
team's saved order as CSV (rank, player_id, player, role, ipl_team —
the GET projection joined to the players/roles data). Import accepts
a raw CSV text body (no multipart dependency): each row resolves by
player_id column when present, else by exact player name; rows are
ordered as they appear (a leading rank column is positional only).
Every row is validated BEFORE anything is saved — unknown player,
duplicate, ambiguous name, or a player outside the team's league
pool (the league season's players) is a 422 and the saved ranks are
left untouched — then the save flows through the exact existing
write path (services.set_team_ranks: same duplicate/length rules,
live-draft refresh included), gated claim-aware per P4-W18.
"""

import csv
import io
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse

from .. import schemas, services
from ..database import get_db
from . import get_league, get_team, player_roles_map, require_team_actor

router = APIRouter()

MAX_IMPORT_BYTES = 1_000_000


@router.get("/teams/{team_id}/ranks", response_model=schemas.RanksOut)
def get_ranks(team_id: int, con: sqlite3.Connection = Depends(get_db)):
    return schemas.RanksOut(
        team_id=team_id, player_ids=services.get_team_ranks(con, team_id))


@router.put("/teams/{team_id}/ranks", response_model=schemas.RanksOut)
def set_ranks(team_id: int, body: schemas.RanksIn,
              con: sqlite3.Connection = Depends(get_db)):
    return schemas.RanksOut(**services.set_team_ranks(con, team_id, body.player_ids))


def _ranks_rows(con: sqlite3.Connection, team_id: int) -> list[dict]:
    """The export projection: saved rank order joined to player +
    role data for the team's league season (same fields the players
    list projects)."""
    team = get_team(con, team_id)  # 404 if missing
    league = get_league(con, team["league_id"])
    roles = player_roles_map(con, league["season"])
    out = []
    for i, pid in enumerate(services.get_team_ranks(con, team_id)):
        row = con.execute(
            "SELECT name FROM players WHERE id = ?", (pid,)).fetchone()
        meta = roles.get(pid) or {}
        out.append({
            "rank": i + 1, "player_id": pid,
            "player": row["name"] if row else f"#{pid}",
            "role": meta.get("role") or "",
            "ipl_team": meta.get("ipl_team_code") or "",
        })
    return out


@router.get("/teams/{team_id}/ranks.csv")
def export_ranks_csv(team_id: int,
                     con: sqlite3.Connection = Depends(get_db)):
    """P5-W31: the team's current ranks as CSV — same order the GET
    returns, for spreadsheet backup / offline prep."""
    rows = _ranks_rows(con, team_id)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["rank", "player_id", "player", "role", "ipl_team"])
    for r in rows:
        w.writerow([r["rank"], r["player_id"], r["player"],
                    r["role"], r["ipl_team"]])
    return PlainTextResponse(
        buf.getvalue(), media_type="text/csv",
        headers={"Content-Disposition":
                 f'attachment; filename="ranks-team-{team_id}.csv"'})


def _parse_ranks_csv(text: str, pool_by_id: dict[int, str],
                     pool_by_name: dict[str, list[int]]) -> list[int]:
    """Resolve CSV rows to an ordered player-id list, or raise 422.

    Header-aware: a first row naming any of rank/player_id/player/
    name/id fixes the player_id and player columns. Headerless rows
    resolve heuristically: a lone numeric cell is an id, a lone text
    cell is a name, rank,id,... and rank,name layouts are honoured.
    """

    def _by_name(name: str) -> int:
        matches = pool_by_name.get(name, [])
        if not matches:
            raise HTTPException(
                422, f"unknown player {name!r} — not in this league's pool")
        if len(matches) > 1:
            raise HTTPException(
                422, f"player name {name!r} is ambiguous — use player_id")
        return matches[0]

    def _by_id(pid: int) -> int:
        if pid not in pool_by_id:
            raise HTTPException(
                422, f"player {pid} is not in this league's player pool")
        return pid

    reader = csv.reader(io.StringIO(text))
    rows = [r for r in reader if any(c.strip() for c in r)]
    if not rows:
        raise HTTPException(422, "CSV contains no player rows")
    id_col = name_col = None
    first = [c.strip().lower() for c in rows[0]]
    header_keys = {"rank", "player_id", "player id", "player", "name",
                   "id", "role", "ipl_team", "ipl team", "team"}
    if any(c in header_keys for c in first) and \
            not all(c.lstrip("-").isdigit() for c in first if c):
        for i, c in enumerate(first):
            if c in ("player_id", "player id", "id"):
                id_col = i
            elif c in ("player", "name"):
                name_col = i
        rows = rows[1:]
        if not rows:
            raise HTTPException(422, "CSV contains no player rows")

    def resolve(cells: list[str]) -> int:
        cells = [c.strip() for c in cells]
        if id_col is not None and id_col < len(cells) and cells[id_col]:
            raw = cells[id_col]
            if not raw.lstrip("-").isdigit():
                raise HTTPException(422, f"invalid player_id {raw!r}")
            return _by_id(int(raw))
        if name_col is not None and name_col < len(cells) and cells[name_col]:
            return _by_name(cells[name_col])
        nums = [c for c in cells if c.lstrip("-").isdigit()]
        texts = [c for c in cells if c and not c.lstrip("-").isdigit()]
        if len(cells) >= 3 and cells[0].isdigit() and cells[1].isdigit():
            return _by_id(int(cells[1]))  # rank, player_id, player, ...
        if len(cells) == 1:
            if nums:
                return _by_id(int(nums[0]))
            return _by_name(texts[0])
        if texts:
            return _by_name(texts[0])
        raise HTTPException(422, f"cannot parse CSV row {cells!r}")

    ids = [resolve(r) for r in rows]
    if len(ids) != len(set(ids)):
        raise HTTPException(422, "player_ids contains duplicates")
    if len(ids) > 500:
        raise HTTPException(422, "rank list too long (max 500)")
    return ids


@router.post("/teams/{team_id}/ranks/import",
             response_model=schemas.RanksOut)
async def import_ranks_csv(team_id: int, request: Request,
                           con: sqlite3.Connection = Depends(get_db)):
    """P5-W31: import ranks from a CSV text body. Claim-aware per
    P4-W18; validated fully before the save, so a bad file leaves
    the saved ranks untouched."""
    team = require_team_actor(con, team_id, request)  # P4-W18 gate
    league = get_league(con, team["league_id"])
    raw = await request.body()
    if len(raw) > MAX_IMPORT_BYTES:
        raise HTTPException(422, "CSV too large (max 1MB)")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(422, "CSV must be UTF-8 text")
    pool = con.execute(
        "SELECT id, name FROM players WHERE season = ?",
        (league["season"],)).fetchall()
    pool_by_id = {r["id"]: r["name"] for r in pool}
    pool_by_name: dict[str, list[int]] = {}
    for r in pool:
        pool_by_name.setdefault(r["name"], []).append(r["id"])
    player_ids = _parse_ranks_csv(text, pool_by_id, pool_by_name)
    try:
        saved = services.set_team_ranks(con, team_id, player_ids)
    except HTTPException as e:
        # Import contract: every validation failure is a 422 (the PUT
        # path 404s an unknown player id; pre-validation above already
        # converts pool misses, this is defence in depth).
        if e.status_code == 404:
            raise HTTPException(422, e.detail)
        raise
    return schemas.RanksOut(**saved)
