"""P5-W10: season-start readiness — every item derived from DB state.

Walks one scratch league through create -> join -> claim -> ranks ->
draft -> lineups, asserting each item flips only when its underlying
state lands (and no earlier). Settings carry num_teams=2 so the
teams_filled target is explicit.
"""

import json
import sqlite3
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.database import get_db
from api.routers import readiness

SCHEMA = Path(__file__).resolve().parent / "schema.sql"


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / "readiness.db"
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA.read_text())
    con.execute("INSERT INTO users (name) VALUES ('w10-owner')")
    league = con.execute(
        "INSERT INTO leagues (name, invite_code, commissioner_id,"
        " season, settings, status) VALUES ('w10-league', 'CODE-w10',"
        " 1, '2027', ?, 'setup')",
        (json.dumps({"num_teams": 2, "waiver_run_weekday": "wednesday"}),)
    ).lastrowid
    con.commit()
    con.close()

    app = FastAPI()
    app.include_router(readiness.router, prefix="/api/leagues")

    def override():
        c = sqlite3.connect(str(db_path))
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys = ON")
        try:
            yield c
        finally:
            c.close()

    app.dependency_overrides[get_db] = override
    return TestClient(app), league, db_path


def _items(tc, league):
    r = tc.get(f"/api/leagues/{league}/readiness")
    assert r.status_code == 200, r.text
    body = r.json()
    return body, {i["key"]: i["done"] for i in body["items"]}


def _sql(db_path, stmt, args=()):
    con = sqlite3.connect(str(db_path))
    cur = con.execute(stmt, args)
    con.commit()
    lid = cur.lastrowid
    con.close()
    return lid


def test_fresh_league_state(client):
    tc, league, _ = client
    body, done = _items(tc, league)
    assert body["total_count"] == 8
    assert done == {
        "league_created": True, "teams_filled": False,
        "teams_claimed": False, "custom_ranks": False,
        "draft_started": False, "draft_complete": False,
        "week1_lineups": False, "waiver_armed": True,
    }
    assert body["ready_count"] == 2


def test_transitions_flip_only_on_state(client):
    tc, league, db_path = client
    t1 = _sql(db_path, "INSERT INTO teams (league_id, owner_id, name)"
              " VALUES (?, 1, 'w10-A')", (league,))
    _, done = _items(tc, league)
    assert done["teams_filled"] is False  # 1/2
    t2 = _sql(db_path, "INSERT INTO teams (league_id, owner_id, name)"
              " VALUES (?, 1, 'w10-B')", (league,))
    _, done = _items(tc, league)
    assert done["teams_filled"] is True and done["teams_claimed"] is False

    _sql(db_path, "UPDATE teams SET claim_code = 'CODEA' WHERE id = ?", (t1,))
    _, done = _items(tc, league)
    assert done["teams_claimed"] is False  # only 1/2 claimed
    _sql(db_path, "UPDATE teams SET claim_code = 'CODEB' WHERE id = ?", (t2,))
    _, done = _items(tc, league)
    assert done["teams_claimed"] is True

    # Consensus ranks for both teams: not custom. Reorder team B: custom.
    pids = []
    for name in ("P1", "P2", "P3"):
        pids.append(_sql(db_path,
                         "INSERT INTO players (name, season)"
                         " VALUES (?, '2027')", (name,)))
    for t in (t1, t2):
        for rank, pid in enumerate(pids, start=1):
            _sql(db_path, "INSERT INTO pre_draft_ranks (team_id,"
                 " player_id, rank) VALUES (?, ?, ?)", (t, pid, rank))
    _, done = _items(tc, league)
    assert done["custom_ranks"] is False
    _sql(db_path, "UPDATE pre_draft_ranks SET rank = 1"
         " WHERE team_id = ? AND player_id = ?", (t2, pids[2]))
    _sql(db_path, "UPDATE pre_draft_ranks SET rank = 3"
         " WHERE team_id = ? AND player_id = ?", (t2, pids[0]))
    _, done = _items(tc, league)
    assert done["custom_ranks"] is True

    draft = _sql(db_path, "INSERT INTO drafts (league_id, status,"
                 " draft_order) VALUES (?, 'live', ?)",
                 (league, json.dumps([t1, t2])))
    _, done = _items(tc, league)
    assert done["draft_started"] is True and done["draft_complete"] is False
    _sql(db_path, "UPDATE drafts SET status = 'complete' WHERE id = ?",
         (draft,))
    _, done = _items(tc, league)
    assert done["draft_complete"] is True and done["week1_lineups"] is False

    _sql(db_path, "INSERT INTO roster_slots (team_id, player_id, slot,"
         " week_no) VALUES (?, ?, 'WK', 1)", (t1, pids[0]))
    _, done = _items(tc, league)
    assert done["week1_lineups"] is False  # team B still missing
    _sql(db_path, "INSERT INTO roster_slots (team_id, player_id, slot,"
         " week_no) VALUES (?, ?, 'WK', 1)", (t2, pids[1]))
    body, done = _items(tc, league)
    assert done["week1_lineups"] is True
    assert body["ready_count"] == 8


def test_unknown_league_404(client):
    tc, _, _ = client
    assert tc.get("/api/leagues/99999/readiness").status_code == 404
