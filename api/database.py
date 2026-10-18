"""SQLite dev database. Per-request connections (open/close).
check_same_thread=False: FastAPI runs sync generator dependencies and sync
endpoints in anyio's worker threadpool, and setup/endpoint/teardown may land
on different threads within one request. Each request still gets its own
connection (no cross-request sharing); threads within a request use it
sequentially. DATABASE_URL env override; default data/ipl_fantasy.db.
Postgres migration is a Phase-4 decision, not this scaffold's."""

import logging
import os
import sqlite3
from pathlib import Path

log = logging.getLogger("api.db")

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = REPO_ROOT / "data" / "ipl_fantasy.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def db_path() -> Path:
    url = os.getenv("DATABASE_URL", "")
    if url.startswith("sqlite:///"):
        return Path(url.replace("sqlite:///", "", 1))
    if url and not url.startswith("sqlite"):
        raise RuntimeError(f"Only sqlite DATABASE_URL supported in scaffold, got: {url!r}")
    return DEFAULT_DB


def connect() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    # check_same_thread=False: see module docstring (anyio worker threads).
    con = sqlite3.connect(str(path), check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def init_db() -> None:
    """Create tables if missing (idempotent)."""
    schema = SCHEMA_PATH.read_text()
    with connect() as con:
        con.executescript(schema)
        # P4-W4: player_roles.status (IL-eligibility designation) predates
        # its schema entry — the 2026 demo migration added it ad hoc on
        # the Pi. Add it wherever it's still missing.
        cols = {r["name"] for r in con.execute("PRAGMA table_info(player_roles)")}
        if "status" not in cols:
            con.execute("ALTER TABLE player_roles ADD COLUMN status TEXT")
        # P4-W18: claim_code predates nothing — add it to team tables
        # created before the column existed (idempotent).
        cols = {r[1] for r in con.execute("PRAGMA table_info(teams)")}
        if "claim_code" not in cols:
            con.execute("ALTER TABLE teams ADD COLUMN claim_code TEXT")
        # P5-W39: pinned_at on league_messages (P5-W5 table) — add it
        # wherever it's still missing (e.g. the Pi prod DB created
        # before this column existed).
        cols = {r["name"] for r in con.execute("PRAGMA table_info(league_messages)")}
        if "pinned_at" not in cols:
            con.execute("ALTER TABLE league_messages ADD COLUMN pinned_at TEXT")
        con.commit()
    log.info(f"db ready at {db_path()}")


def table_empty(table: str) -> bool:
    with connect() as con:
        return con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0


# FastAPI dependency: yields a connection, closes it after the request.
def get_db():
    con = connect()
    try:
        yield con
    finally:
        con.close()
