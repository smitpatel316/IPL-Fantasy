"""SQLite dev database. Per-request connections (open/close) — no cross-thread
sharing issues under uvicorn. DATABASE_URL env override; default data/ipl_fantasy.db.
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
    con = sqlite3.connect(str(path))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def init_db() -> None:
    """Create tables if missing (idempotent)."""
    schema = SCHEMA_PATH.read_text()
    with connect() as con:
        con.executescript(schema)
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
