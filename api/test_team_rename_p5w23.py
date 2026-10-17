"""P5-W23: team rename — hand-derived fixture.

League with teams A ("Alpha XI") and B ("Beta XI"):
  * renaming A to "Alpha Prime" round-trips in the PATCH response and
    the new name is what the league standings + teams list project;
  * renaming A to B's name -> 409 (same contract as join);
  * whitespace-only / empty names -> 422;
  * unknown team -> 404;
  * once A is claimed, rename without/with a wrong claim code -> 403,
    with the code -> 200; B (unclaimed) stays honor-system.
"""
import sqlite3
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.database import get_db
from api.routers import identity, leagues

SCHEMA = Path(__file__).resolve().parent / "schema.sql"


def _seed(con):
    con.execute("INSERT INTO users (name) VALUES ('w23-owner')")
    league = con.execute(
        "INSERT INTO leagues (name, invite_code, commissioner_id, season, settings, status)"
        " VALUES ('w23-league','CODE-w23',1,'2027','{}','setup')").lastrowid
    teams = {}
    for label, name in (("A", "Alpha XI"), ("B", "Beta XI")):
        teams[label] = con.execute(
            "INSERT INTO teams (league_id, owner_id, name, faab_remaining)"
            " VALUES (?,1,?,100)", (league, name)).lastrowid
    con.commit()
    return league, teams


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / "w23.db"
    con = sqlite3.connect(str(db_path)); con.row_factory = sqlite3.Row
    con.executescript(SCHEMA.read_text())
    league, teams = _seed(con)
    con.close()
    app = FastAPI()
    app.include_router(identity.router, prefix="/api")
    app.include_router(leagues.router, prefix="/api/leagues")

    def override():
        c = sqlite3.connect(str(db_path)); c.row_factory = sqlite3.Row
        try: yield c
        finally: c.close()
    app.dependency_overrides[get_db] = override
    return TestClient(app), league, teams, db_path


def _claim(db_path, team_id, code="SECRET1234"):
    con = sqlite3.connect(str(db_path))
    con.execute("UPDATE teams SET claim_code = ? WHERE id = ?", (code, team_id))
    con.commit(); con.close()


def test_rename_roundtrips_and_projects_everywhere(client):
    tc, league, teams, _ = client
    r = tc.patch(f"/api/teams/{teams['A']}", json={"name": "  Alpha Prime  "})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["name"] == "Alpha Prime"  # trimmed
    assert body["claim_code"] is None  # never leaked by a mutation response
    detail = tc.get(f"/api/leagues/{league}").json()
    names = {s["team_id"]: s["team_name"] for s in detail["standings"]}
    assert names[teams["A"]] == "Alpha Prime"
    assert names[teams["B"]] == "Beta XI"
    listed = tc.get(f"/api/leagues/{league}/teams").json()
    assert {t["id"]: t["name"] for t in listed}[teams["A"]] == "Alpha Prime"


def test_duplicate_name_409_and_same_name_ok(client):
    tc, league, teams, _ = client
    r = tc.patch(f"/api/teams/{teams['A']}", json={"name": "Beta XI"})
    assert r.status_code == 409
    assert "taken in this league" in r.json()["detail"]
    # Renaming to your own current name is a no-op, not a clash.
    r = tc.patch(f"/api/teams/{teams['A']}", json={"name": "Alpha XI"})
    assert r.status_code == 200


def test_empty_and_unknown(client):
    tc, league, teams, _ = client
    assert tc.patch(f"/api/teams/{teams['A']}",
                    json={"name": "   "}).status_code == 422
    assert tc.patch(f"/api/teams/{teams['A']}",
                    json={"name": ""}).status_code == 422
    assert tc.patch("/api/teams/99999",
                    json={"name": "Ghost"}).status_code == 404


def test_claim_gate(client):
    tc, league, teams, db_path = client
    _claim(db_path, teams["A"])
    assert tc.patch(f"/api/teams/{teams['A']}",
                    json={"name": "Nope"}).status_code == 403
    assert tc.patch(f"/api/teams/{teams['A']}", json={"name": "Nope"},
                    headers={"X-Team-Claim": "WRONGCODE1"}).status_code == 403
    r = tc.patch(f"/api/teams/{teams['A']}", json={"name": "Claimed Name"},
                 headers={"X-Team-Claim": "SECRET1234"})
    assert r.status_code == 200, r.text
    assert r.json()["name"] == "Claimed Name"
    assert r.json()["claimed"] is True
    # Unclaimed B is untouched by A's claim and stays honor-system.
    r = tc.patch(f"/api/teams/{teams['B']}", json={"name": "Beta Prime"})
    assert r.status_code == 200
