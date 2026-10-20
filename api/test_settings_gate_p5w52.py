"""P5-W52: PATCH /api/leagues/{id}/settings is commissioner-gated — hand-derived.

Scratch league: commissioner user 1 owns the commissioner's team; a
second team belongs to user 2. Expectations are computed by hand:

1. a non-commissioner team acting as commissioner_team_id -> 403 and
   the settings row is unchanged.
2. the claimed commissioner's team without its X-Team-Claim header ->
   403 (P4-W18 claim gate).
3. the claimed commissioner's team with a wrong code -> 403.
4. the claimed commissioner's team with the right code -> 200; the key
   is applied, the DB row persists it, and commissioner_team_id is NOT
   persisted into settings.
5. an UNCLAIMED commissioner's team acts without a header -> 200
   (honor-system, same as P4-W18).
6. a body with no commissioner_team_id at all -> 422 (schema rejects).
7. invalid settings keys still 422 for the commissioner (gate and
   validation are independent).
"""

import json
import sqlite3
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.database import get_db
from api.routers import leagues

SCHEMA = Path(__file__).resolve().parent / "schema.sql"
COMM_CODE = "GATECODE01"


def _seed(con, claim_code=None):
    con.execute("INSERT INTO users (name) VALUES ('comm')")
    con.execute("INSERT INTO users (name) VALUES ('rival')")
    league = con.execute(
        "INSERT INTO leagues (name, invite_code, commissioner_id,"
        " season, settings, status) VALUES ('gate', 'CODE-gate', 1,"
        " '2027', '{}', 'setup')").lastrowid
    comm = con.execute(
        "INSERT INTO teams (league_id, name, owner_id) VALUES"
        " (?, 'Comm XI', 1)", (league,)).lastrowid
    other = con.execute(
        "INSERT INTO teams (league_id, name, owner_id) VALUES"
        " (?, 'Rival XI', 2)", (league,)).lastrowid
    if claim_code is not None:
        con.execute("UPDATE teams SET claim_code = ? WHERE id = ?",
                    (claim_code, comm))
    con.commit()
    return league, comm, other


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / "gate.db"
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA.read_text())
    league, comm, other = _seed(con, claim_code=COMM_CODE)
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
    return TestClient(app), db_path, league, comm, other


@pytest.fixture()
def unclaimed_client(tmp_path):
    """Same shape but the commissioner's team is NOT claimed: no header
    needed (P4-W18 honor-system for unclaimed teams)."""
    db_path = tmp_path / "gateu.db"
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA.read_text())
    league, comm, other = _seed(con, claim_code=None)
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
    return TestClient(app), db_path, league, comm, other


def _settings(db_path, league):
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    row = con.execute("SELECT settings FROM leagues WHERE id = ?",
                      (league,)).fetchone()
    con.close()
    return json.loads(row["settings"])


def test_non_commissioner_403_and_settings_unchanged(client):
    tc, db_path, league, comm, other = client
    before = _settings(db_path, league)
    r = tc.patch(f"/api/leagues/{league}/settings",
                 json={"commissioner_team_id": other,
                       "pick_clock_secs": 120})
    assert r.status_code == 403, r.text
    assert "only the commissioner's team" in r.json()["detail"]
    # nothing was written: settings are byte-identical to before.
    assert _settings(db_path, league) == before


def test_claimed_commissioner_needs_claim_code(client):
    tc, db_path, league, comm, other = client
    before = _settings(db_path, league)
    r = tc.patch(f"/api/leagues/{league}/settings",
                 json={"commissioner_team_id": comm,
                       "pick_clock_secs": 120})
    assert r.status_code == 403, r.text
    assert _settings(db_path, league) == before


def test_claimed_commissioner_wrong_code_403(client):
    tc, db_path, league, comm, other = client
    r = tc.patch(f"/api/leagues/{league}/settings",
                 json={"commissioner_team_id": comm,
                       "pick_clock_secs": 120},
                 headers={"X-Team-Claim": "WRONGCODE"})
    assert r.status_code == 403, r.text


def test_commissioner_with_code_200_and_applies(client):
    tc, db_path, league, comm, other = client
    r = tc.patch(f"/api/leagues/{league}/settings",
                 json={"commissioner_team_id": comm,
                       "pick_clock_secs": 120,
                       "trade_deadline_week": 5},
                 headers={"X-Team-Claim": COMM_CODE})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["settings"]["pick_clock_secs"] == 120
    assert body["settings"]["trade_deadline_week"] == 5
    # the identity field is not persisted into the settings blob.
    assert "commissioner_team_id" not in body["settings"]
    # and the league row itself agrees (not just the response).
    persisted = _settings(db_path, league)
    assert persisted["pick_clock_secs"] == 120
    assert persisted["trade_deadline_week"] == 5
    assert "commissioner_team_id" not in persisted


def test_unclaimed_commissioner_honor_system_200(unclaimed_client):
    tc, db_path, league, comm, other = unclaimed_client
    r = tc.patch(f"/api/leagues/{league}/settings",
                 json={"commissioner_team_id": comm,
                       "waiver_run_weekday": "friday"})
    assert r.status_code == 200, r.text
    assert r.json()["settings"]["waiver_run_weekday"] == "friday"


def test_missing_commissioner_team_id_422(client):
    tc, db_path, league, comm, other = client
    before = _settings(db_path, league)
    r = tc.patch(f"/api/leagues/{league}/settings",
                 json={"pick_clock_secs": 120})
    assert r.status_code == 422, r.text
    assert _settings(db_path, league) == before


def test_invalid_key_still_422_for_commissioner(client):
    # gate passes (right team + right code) so the draft_order
    # permutation validation runs and rejects -> 422, nothing written.
    tc, db_path, league, comm, other = client
    before = _settings(db_path, league)
    r = tc.patch(f"/api/leagues/{league}/settings",
                 json={"commissioner_team_id": comm,
                       "draft_order": [comm, comm]},
                 headers={"X-Team-Claim": COMM_CODE})
    assert r.status_code == 422, r.text
    assert _settings(db_path, league) == before
