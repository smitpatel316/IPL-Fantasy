"""P5-W27: key dates — every date derives from its enforcing source.

Fixture: league with default settings (waiver wednesday, deadline
week 6, pick clock 90) and one fixture week row (week 1 starts
2027-03-08). Lock entries must equal lineup_lock_at() — the P4-W8
enforcement seam — for every week; the deadline entry must equal the
week-6 lock; a settings change to friday/week 4 must flip both.
"""

import json
import sqlite3
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.database import get_db
from api.routers import key_dates
from api.routers.lineups import lineup_lock_at

SCHEMA = Path(__file__).resolve().parent / "schema.sql"


def _seed(con, settings="{}"):
    con.execute("INSERT INTO users (name) VALUES ('w27-owner')")
    league = con.execute(
        "INSERT INTO leagues (name, invite_code, commissioner_id,"
        " season, settings, status) VALUES ('w27', 'CODE-w27', 1,"
        " '2027', ?, 'setup')", (settings,)).lastrowid
    con.execute(
        "INSERT INTO team_weekly_games (season, week_no, week_start,"
        " week_end, ipl_team_code, games, source) VALUES ('2027', 1,"
        " '2027-03-08', '2027-03-14', 'MI', 2, 'standin-2026')")
    con.commit()
    return league


@pytest.fixture()
def db(tmp_path):
    db_path = tmp_path / "dates.db"
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA.read_text())
    league = _seed(con)
    con.close()
    return db_path, league


def _client(db_path):
    app = FastAPI()
    app.include_router(key_dates.router, prefix="/api/leagues")

    def override():
        c = sqlite3.connect(str(db_path))
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys = ON")
        try:
            yield c
        finally:
            c.close()

    app.dependency_overrides[get_db] = override
    return TestClient(app)


def test_key_dates_match_enforcing_sources(db):
    db_path, league = db
    tc = _client(db_path)
    r = tc.get(f"/api/leagues/{league}/key-dates")
    assert r.status_code == 200, r.text
    entries = {e["key"]: e for e in r.json()["entries"]}
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    for wk in range(1, 9):
        lock = lineup_lock_at(con, league, wk)
        e = entries[f"lineup_lock_{wk}"]
        assert e["at"] == lock.isoformat(), wk
        assert e["at_pt"] and "IST" in e["at_ist"]
    con.close()
    assert entries["trade_deadline"]["at"] == entries["lineup_lock_6"]["at"]
    assert "week 6" in entries["trade_deadline"]["label"]
    assert entries["playoffs"]["at"] == entries["lineup_lock_7"]["at"]
    waiver = entries["waiver_run"]
    assert "Wednesday" in waiver["label"] and "03:00" in waiver["at_pt"]
    assert entries["draft"]["state"] == "upcoming"
    assert "90s" in entries["draft"]["detail"]
    states = [e["state"] for e in r.json()["entries"] if e["at"]]
    assert states.count("next-up") == 1  # exactly one next dated entry
    assert tc.get("/api/leagues/99999/key-dates").status_code == 404


def test_settings_change_flips_entries(db):
    db_path, league = db
    con = sqlite3.connect(str(db_path))
    con.execute("UPDATE leagues SET settings = ? WHERE id = ?",
                (json.dumps({"waiver_run_weekday": "friday",
                             "trade_deadline_week": 4}), league))
    con.commit()
    con.close()
    tc = _client(db_path)
    entries = {e["key"]: e
               for e in tc.get(f"/api/leagues/{league}/key-dates").json()["entries"]}
    assert "Friday" in entries["waiver_run"]["label"]
    assert entries["trade_deadline"]["at"] == entries["lineup_lock_4"]["at"]
