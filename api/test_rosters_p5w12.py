"""P5-W12: all-teams roster view — read-only projection.

Fixture (hand-derived):
  Team A has a saved week-1 lineup: WK(os) BAT BAT(os) BAT AR AR
  BOWL BOWL BOWL UTIL UTIL + BN(os) BN BN + IL = 15 players.
  overseas_starters counts starter slots only -> 2 (WK + one BAT);
  the overseas BN player must NOT count.
  Team B has construction rows only (week_no NULL): 2 BATs -> the
  view falls back to construction slots, roster_size 2.
"""

import sqlite3
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.database import get_db
from api.routers import rosters

SCHEMA = Path(__file__).resolve().parent / "schema.sql"


def _player(con, name, role, overseas):
    pid = con.execute(
        "INSERT INTO players (name, season) VALUES (?, '2027')",
        (name,)).lastrowid
    con.execute(
        "INSERT INTO player_roles (player_id, season, role, is_overseas,"
        " ipl_team_code) VALUES (?, '2027', ?, ?, 'MI')",
        (pid, role, overseas))
    return pid


def _seed(con):
    con.execute("INSERT INTO users (name) VALUES ('w12-owner')")
    ids = {}
    league = con.execute(
        "INSERT INTO leagues (name, invite_code, commissioner_id,"
        " season, settings, status) VALUES ('w12-league', 'CODE-w12',"
        " 1, '2027', '{}', 'in_season')").lastrowid
    ids["league"] = league
    for label, faab in (("A", 73), ("B", 100)):
        ids[f"team{label}"] = con.execute(
            "INSERT INTO teams (league_id, owner_id, name,"
            " faab_remaining) VALUES (?, 1, ?, ?)",
            (league, f"w12-{label}", faab)).lastrowid
    plan = [  # (slot, role, overseas) for team A's week-1 lineup
        ("WK", "WK", 1), ("BAT", "BAT", 0), ("BAT", "BAT", 1),
        ("BAT", "BAT", 0), ("AR", "AR", 0), ("AR", "AR", 0),
        ("BOWL", "BOWL", 0), ("BOWL", "BOWL", 0), ("BOWL", "BOWL", 0),
        ("UTIL", "AR", 0), ("UTIL", "BAT", 0),
        ("BN", "BOWL", 1), ("BN", "BAT", 0), ("BN", "AR", 0),
        ("IL", "BAT", 0),
    ]
    for i, (slot, role, os_) in enumerate(plan):
        pid = _player(con, f"A{i}", role, os_)
        con.execute(
            "INSERT INTO roster_slots (team_id, player_id, slot, week_no)"
            " VALUES (?, ?, ?, 1)", (ids["teamA"], pid, slot))
    for i in range(2):
        pid = _player(con, f"B{i}", "BAT", 0)
        con.execute(
            "INSERT INTO roster_slots (team_id, player_id, slot)"
            " VALUES (?, ?, 'BAT')", (ids["teamB"], pid))
    con.commit()
    return ids


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / "rosters.db"
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA.read_text())
    ids = _seed(con)
    con.close()

    app = FastAPI()
    app.include_router(rosters.router, prefix="/api/leagues")

    def override():
        c = sqlite3.connect(str(db_path))
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys = ON")
        try:
            yield c
        finally:
            c.close()

    app.dependency_overrides[get_db] = override
    return TestClient(app), ids


def test_rosters_grouped_with_d8_count(client):
    tc, ids = client
    r = tc.get(f"/api/leagues/{ids['league']}/rosters")
    assert r.status_code == 200, r.text
    teams = {t["team_name"]: t for t in r.json()["teams"]}
    a = teams["w12-A"]
    assert a["roster_size"] == 15 and a["faab_remaining"] == 73
    assert a["overseas_starters"] == 2  # BN overseas does not count
    assert len(a["slots"]["WK"]) == 1 and len(a["slots"]["BAT"]) == 3
    assert len(a["slots"]["AR"]) == 2 and len(a["slots"]["BOWL"]) == 3
    assert len(a["slots"]["UTIL"]) == 2 and len(a["slots"]["BN"]) == 3
    assert len(a["slots"]["IL"]) == 1
    assert a["slots"]["WK"][0]["is_overseas"] is True
    b = teams["w12-B"]
    assert b["roster_size"] == 2 and len(b["slots"]["BAT"]) == 2
    assert b["overseas_starters"] == 0


def test_unknown_league_404(client):
    tc, _ = client
    assert tc.get("/api/leagues/99999/rosters").status_code == 404
