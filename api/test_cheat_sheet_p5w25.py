"""P5-W25: draft cheat sheet — hand-derived tier fixture.

Tier rule (pinned): within a role, ordered by consensus rank, a new
tier starts wherever the rank gap to the previous player exceeds 5.

WK ranks 1, 3, 10, 16 -> gaps 2, 7, 6 -> tiers 1, 1, 2, 3.
BAT ranks 2, 4, unranked -> tiers 1, 1, 1 (unranked sorts last and
keeps the running tier). Schedule: MI plays 2+1 games (total 3),
CSK none in the fixture rows beyond week 1 = 1 (total 1).
"""

import sqlite3
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.database import get_db
from api.routers import leagues

SCHEMA = Path(__file__).resolve().parent / "schema.sql"
PLAYERS = [
    # name, role, team, overseas, status, rank
    ("WK A", "WK", "MI", 0, None, 1),
    ("WK B", "WK", "MI", 0, None, 3),
    ("WK C", "WK", "CSK", 1, None, 10),
    ("WK D", "WK", "CSK", 0, "injured", 16),
    ("BAT E", "BAT", "MI", 0, None, 2),
    ("BAT F", "BAT", "CSK", 0, None, 4),
    ("BAT G", "BAT", "MI", 0, None, None),
]


def _seed(con):
    con.execute("INSERT INTO users (name) VALUES ('w25-owner')")
    league = con.execute(
        "INSERT INTO leagues (name, invite_code, commissioner_id,"
        " season, settings, status) VALUES ('w25-league', 'CODE-w25',"
        " 1, '2027', '{}', 'setup')").lastrowid
    team = con.execute(
        "INSERT INTO teams (league_id, name, owner_id) VALUES (?, 'T1', 1)",
        (league,)).lastrowid
    for name, role, code, os_, status, rank in PLAYERS:
        pid = con.execute(
            "INSERT INTO players (name, season) VALUES (?, '2027')",
            (name,)).lastrowid
        con.execute(
            "INSERT INTO player_roles (player_id, season, role,"
            " is_overseas, ipl_team_code, status) VALUES"
            " (?, '2027', ?, ?, ?, ?)", (pid, role, os_, code, status))
        if rank is not None:
            con.execute(
                "INSERT INTO pre_draft_ranks (team_id, player_id, rank)"
                " VALUES (?, ?, ?)", (team, pid, rank))
    for wk, code, games in [(1, "MI", 2), (2, "MI", 1), (1, "CSK", 1)]:
        con.execute(
            "INSERT INTO team_weekly_games (season, week_no, week_start,"
            " week_end, ipl_team_code, games, source) VALUES ('2027', ?,"
            " '2027-03-08', '2027-03-14', ?, ?, 'standin-2026')",
            (wk, code, games))
    con.commit()
    return {"league": league}


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / "sheet.db"
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA.read_text())
    ids = _seed(con)
    con.close()
    app = FastAPI()
    app.include_router(leagues.router, prefix="/api/leagues")

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


def test_tiers_order_and_fields(client):
    tc, ids = client
    r = tc.get(f"/api/leagues/{ids['league']}/cheat-sheet")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tier_gap_threshold"] == 5
    assert body["source"] == "standin-2026"
    groups = {g["role"]: g["players"] for g in body["groups"]}
    assert [g["role"] for g in body["groups"]] == ["WK", "BAT", "AR", "BOWL"]
    wk = groups["WK"]
    assert [(p["name"], p["preseason_rank"], p["tier"]) for p in wk] == [
        ("WK A", 1, 1), ("WK B", 3, 1), ("WK C", 10, 2), ("WK D", 16, 3)]
    assert wk[0]["total_games"] == 3 and wk[2]["total_games"] == 1
    assert wk[3]["availability"] == "out"
    assert wk[2]["is_overseas"] is True
    bat = groups["BAT"]
    assert [(p["name"], p["tier"]) for p in bat] == [
        ("BAT E", 1), ("BAT F", 1), ("BAT G", 1)]
    assert bat[2]["preseason_rank"] is None
    assert groups["AR"] == [] and groups["BOWL"] == []
    # field-for-field vs the players-list projection for rank/avg
    assert all(p["avg_points"] is None for p in wk)


def test_csv_matches_payload(client):
    tc, ids = client
    body = tc.get(f"/api/leagues/{ids['league']}/cheat-sheet").json()
    r = tc.get(f"/api/leagues/{ids['league']}/cheat-sheet.csv")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    lines = r.text.strip().splitlines()
    n = sum(len(g["players"]) for g in body["groups"])
    assert len(lines) == n + 1
    assert lines[1].startswith("WK,1,WK A,MI,no,1,")
    assert tc.get("/api/leagues/99999/cheat-sheet").status_code == 404
    assert tc.get("/api/leagues/99999/cheat-sheet.csv").status_code == 404
