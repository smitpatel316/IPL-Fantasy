"""P5-W21: roster-health assistant — hand-derived fixture.

Team A construction roster (week_no NULL):
  P1 BAT slot, status 'injured'  -> move_to_il (note: frees a spot)
  P2 BOWL slot, status NULL      -> healthy, appears nowhere
  P3 AR slot, status 'retired'   -> retired only (not move_to_il)
  P4 WK slot IL, status 'active' -> return_candidates
  P5 BAT slot IL, status 'injured' -> correctly on IL, appears nowhere
Team B: one healthy player -> all lists empty (honest empty state).
A second team reading A's health without A's claim code -> 403 once
A is claimed; with the code -> 200.
"""
import sqlite3
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.database import get_db
from api.routers import roster_health

SCHEMA = Path(__file__).resolve().parent / "schema.sql"


def _seed(con):
    con.execute("INSERT INTO users (name) VALUES ('w21-owner')")
    league = con.execute(
        "INSERT INTO leagues (name, invite_code, commissioner_id, season, settings, status)"
        " VALUES ('w21-league','CODE-w21',1,'2027','{}','in_season')").lastrowid
    teams = {}
    for label in ("A", "B"):
        teams[label] = con.execute(
            "INSERT INTO teams (league_id, owner_id, name, faab_remaining)"
            " VALUES (?,1,?,100)", (league, f"w21-{label}")).lastrowid
    specs = [  # name, role, slot, status (team A)
        ("P1", "BAT", "BAT", "injured"),
        ("P2", "BOWL", "BOWL", None),
        ("P3", "AR", "AR", "retired"),
        ("P4", "WK", "IL", "active"),
        ("P5", "BAT", "IL", "injured"),
    ]
    for name, role, slot, status in specs:
        pid = con.execute(
            "INSERT INTO players (name, season) VALUES (?, '2027')", (name,)).lastrowid
        con.execute(
            "INSERT INTO player_roles (player_id, season, role, is_overseas, ipl_team_code, status)"
            " VALUES (?, '2027', ?, 0, 'MI', ?)", (pid, role, status))
        con.execute(
            "INSERT INTO roster_slots (team_id, player_id, slot) VALUES (?, ?, ?)",
            (teams["A"], pid, slot))
    pid = con.execute(
        "INSERT INTO players (name, season) VALUES ('Q1', '2027')").lastrowid
    con.execute(
        "INSERT INTO player_roles (player_id, season, role, is_overseas, ipl_team_code, status)"
        " VALUES (?, '2027', 'BAT', 0, 'MI', 'active')", (pid,))
    con.execute(
        "INSERT INTO roster_slots (team_id, player_id, slot) VALUES (?, ?, 'BAT')",
        (teams["B"], pid))
    con.commit()
    return league, teams


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / "w21.db"
    con = sqlite3.connect(str(db_path)); con.row_factory = sqlite3.Row
    con.executescript(SCHEMA.read_text())
    # schema.sql player_roles may lack status on older shape; ensure col
    cols = [r[1] for r in con.execute("PRAGMA table_info(player_roles)")]
    if "status" not in cols:
        con.execute("ALTER TABLE player_roles ADD COLUMN status TEXT")
    league, teams = _seed(con)
    con.close()
    app = FastAPI(); app.include_router(roster_health.router, prefix="/api/leagues")
    def override():
        c = sqlite3.connect(str(db_path)); c.row_factory = sqlite3.Row
        try: yield c
        finally: c.close()
    app.dependency_overrides[get_db] = override
    return TestClient(app), league, teams, db_path


def _get(tc, league, team, **kw):
    r = tc.get(f"/api/leagues/{league}/roster-health", params={"team_id": team}, **kw)
    assert r.status_code == 200, r.text
    return r.json()


def test_candidate_lists_hand_derived(client):
    tc, league, teams, _ = client
    body = _get(tc, league, teams["A"])
    assert [p["player_name"] for p in body["move_to_il"]] == ["P1"]
    assert body["move_to_il"][0]["note"] == "Moving to IL frees a roster spot"
    assert [p["player_name"] for p in body["return_candidates"]] == ["P4"]
    assert [p["player_name"] for p in body["retired"]] == ["P3"]
    assert "curated registry" in body["basis"]


def test_healthy_roster_empty_state(client):
    tc, league, teams, _ = client
    body = _get(tc, league, teams["B"])
    assert body["move_to_il"] == [] and body["return_candidates"] == [] \
        and body["retired"] == []


def test_claim_gate_hides_payload(client):
    tc, league, teams, db_path = client
    con = sqlite3.connect(str(db_path))
    con.execute("UPDATE teams SET claim_code = 'SECRET1234' WHERE id = ?",
                (teams["A"],))
    con.commit(); con.close()
    r = tc.get(f"/api/leagues/{league}/roster-health",
               params={"team_id": teams["A"]})
    assert r.status_code == 403
    ok = _get(tc, league, teams["A"], headers={"X-Team-Claim": "SECRET1234"})
    assert ok["team_name"] == "w21-A"


def test_unknowns(client):
    tc, league, teams, _ = client
    assert tc.get("/api/leagues/99999/roster-health",
                  params={"team_id": teams["A"]}).status_code == 404
    assert tc.get(f"/api/leagues/{league}/roster-health",
                  params={"team_id": 99999}).status_code == 404
