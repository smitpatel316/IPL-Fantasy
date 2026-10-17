"""P5-W29: league-wide availability report — hand-derived fixture.

Planted statuses: team A rosters Hurt (injured -> out, sitting in the
IL slot) and Old (retired); team B rosters Fine (active — must NOT
appear); free agent Risky (out, unrostered) appears under free agents.
IL occupancy: A filled (Hurt), B open.
"""

import sqlite3
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.database import get_db
from api.routers import availability_report

SCHEMA = Path(__file__).resolve().parent / "schema.sql"


def _seed(con):
    con.execute("INSERT INTO users (name) VALUES ('w29-owner')")
    league = con.execute(
        "INSERT INTO leagues (name, invite_code, commissioner_id,"
        " season, settings, status) VALUES ('w29', 'CODE-w29', 1,"
        " '2027', '{}', 'in_season')").lastrowid
    teams = {}
    for name in ("A", "B"):
        teams[name] = con.execute(
            "INSERT INTO teams (league_id, name, owner_id) VALUES"
            " (?, ?, 1)", (league, name)).lastrowid
    players = {}
    for name, status in [("Hurt", "injured"), ("Old", "retired"),
                         ("Fine", None), ("Risky", "out")]:
        pid = con.execute(
            "INSERT INTO players (name, season) VALUES (?, '2027')",
            (name,)).lastrowid
        con.execute(
            "INSERT INTO player_roles (player_id, season, role,"
            " is_overseas, ipl_team_code, status) VALUES"
            " (?, '2027', 'BAT', 0, 'MI', ?)", (pid, status))
        players[name] = pid
    for pname, slot in [("Hurt", "IL"), ("Old", "BN")]:
        con.execute(
            "INSERT INTO roster_slots (team_id, player_id, slot) VALUES"
            " (?, ?, ?)", (teams["A"], players[pname], slot))
    con.execute(
        "INSERT INTO roster_slots (team_id, player_id, slot) VALUES"
        " (?, ?, 'BAT')", (teams["B"], players["Fine"]))
    con.commit()
    return {"league": league, "teams": teams}


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / "avail.db"
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA.read_text())
    ids = _seed(con)
    con.close()
    app = FastAPI()
    app.include_router(availability_report.router, prefix="/api/leagues")

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


def test_report_grouping_and_il(client):
    tc, ids = client
    r = tc.get(f"/api/leagues/{ids['league']}/availability-report")
    assert r.status_code == 200, r.text
    body = r.json()
    groups = {g["availability"]: g for g in body["groups"]}
    assert set(groups) == {"out", "retired"}
    out_team = groups["out"]["teams"][0]
    assert out_team["team_name"] == "A"
    assert [(p["name"], p["on_il"]) for p in out_team["players"]] == [("Hurt", True)]
    assert groups["retired"]["teams"][0]["players"][0]["name"] == "Old"
    assert [p["name"] for p in body["free_agents"]] == ["Risky"]
    occ = {o["team_name"]: o["il_player_name"] for o in body["il_occupancy"]}
    assert occ == {"A": "Hurt", "B": None}
    assert "curated registry" in body["basis"]
    assert tc.get("/api/leagues/99999/availability-report").status_code == 404
