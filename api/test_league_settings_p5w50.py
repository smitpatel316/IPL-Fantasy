"""P5-W50: commissioner league settings editor UI — backend contract.

Scratch league with 2 teams (COMM = the commissioner's team, RIVAL).
Checks:
  1. PATCH /leagues/{id}/settings round-trips: 200, and the subsequent
     GET /leagues/{id} reflects the new trade_deadline_week and
     waiver_run_weekday (plus pick_clock_secs).
  2. out-of-range / bad-pattern patch values 422
     (pick_clock_secs > 600, waiver_run_weekday not a weekday).
  3. an unknown key 422s (pydantic ignores extras -> "no settings supplied").
  4. an empty patch body 422s.
  5. commissioner identity: _commissioner_team_id resolves the
     commissioner's team and not the rival's — this is the identity the
     web UI mirrors for commissioner-only visibility. NOTE: the PATCH
     endpoint itself is still ungated server-side (the P4-W15
     "Ungated until team identity lands" TODO was never implemented);
     visibility gating is the P5-W50 UI change.
"""

import json
import sqlite3
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.database import get_db
from api.routers import leagues
from api.routers.message_board import _commissioner_team_id
from api.routers import get_league

SCHEMA = Path(__file__).resolve().parent / "schema.sql"


@pytest.fixture
def db_path(tmp_path):
    p = tmp_path / "w50.db"
    c = sqlite3.connect(str(p))
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA.read_text())
    c.execute("PRAGMA foreign_keys = ON")
    c.close()
    return p


@pytest.fixture
def client(db_path):
    app = FastAPI()
    app.include_router(leagues.router, prefix="/api/leagues")

    def _db():
        con = sqlite3.connect(str(db_path))
        con.row_factory = sqlite3.Row
        try:
            yield con
        finally:
            con.close()

    app.dependency_overrides[get_db] = _db
    with TestClient(app) as c:
        yield c


@pytest.fixture
def league_id(db_path):
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    con.execute("INSERT INTO users (name) VALUES ('w50-commish')")
    con.execute("INSERT INTO users (name) VALUES ('w50-rival')")
    lid = con.execute(
        "INSERT INTO leagues (name, invite_code, commissioner_id, season,"
        " settings, status) VALUES ('w50-league', 'CODE-w50', 1, '2027',"
        " ?, 'setup')",
        (json.dumps({
            "draft_type": "snake", "rounds": 14, "faab_budget": 100,
            "scoring_table_version": "v1", "overseas_cap": 4,
            "playoff_teams": 4, "trade_deadline_week": 6,
            "waiver_run_weekday": "wednesday", "pick_clock_secs": 90,
        }),)).lastrowid
    comm = con.execute(
        "INSERT INTO teams (league_id, owner_id, name, faab_remaining)"
        " VALUES (?, 1, 'w50-COMM', 100)", (lid,)).lastrowid
    rival = con.execute(
        "INSERT INTO teams (league_id, owner_id, name, faab_remaining)"
        " VALUES (?, 2, 'w50-RIVAL', 100)", (lid,)).lastrowid
    con.commit()
    con.close()
    return lid, comm, rival


def test_settings_round_trip(client, league_id, db_path):
    lid, _, _ = league_id
    r = client.patch(
        f"/api/leagues/{lid}/settings",
        json={"trade_deadline_week": 5, "waiver_run_weekday": "friday",
              "pick_clock_secs": 120},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["settings"]["trade_deadline_week"] == 5
    assert body["settings"]["waiver_run_weekday"] == "friday"
    assert body["settings"]["pick_clock_secs"] == 120
    # creation-time-only keys untouched by the patch
    assert body["settings"]["faab_budget"] == 100
    assert body["settings"]["playoff_teams"] == 4
    # the change reflects on the league page's GET
    g = client.get(f"/api/leagues/{lid}")
    assert g.status_code == 200, g.text
    settings = g.json()["settings"]
    assert settings["trade_deadline_week"] == 5
    assert settings["waiver_run_weekday"] == "friday"


def test_settings_validation_422s(client, league_id):
    lid, _, _ = league_id
    # pick_clock_secs out of range (0..600)
    r = client.patch(f"/api/leagues/{lid}/settings",
                     json={"pick_clock_secs": 999})
    assert r.status_code == 422, r.text
    # waiver_run_weekday must be a lowercase weekday
    r = client.patch(f"/api/leagues/{lid}/settings",
                     json={"waiver_run_weekday": "Funday"})
    assert r.status_code == 422, r.text
    # trade_deadline_week out of range (1..8)
    r = client.patch(f"/api/leagues/{lid}/settings",
                     json={"trade_deadline_week": 9})
    assert r.status_code == 422, r.text


def test_invalid_key_and_empty_patch_422(client, league_id):
    lid, _, _ = league_id
    # unknown keys are ignored by the patch schema, leaving no settings
    r = client.patch(f"/api/leagues/{lid}/settings",
                     json={"faab_budget": 200})
    assert r.status_code == 422, r.text
    r = client.patch(f"/api/leagues/{lid}/settings", json={})
    assert r.status_code == 422, r.text


def test_commissioner_identity_resolution(db_path, league_id):
    # the UI mirrors this identity for commissioner-only visibility
    lid, comm, rival = league_id
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    league = get_league(con, lid)
    assert _commissioner_team_id(con, league) == comm
    assert _commissioner_team_id(con, league) != rival
    con.close()
