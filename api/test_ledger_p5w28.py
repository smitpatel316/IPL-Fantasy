"""P5-W28: per-team FAAB & transaction ledger — hand-derived.

Scripted history for team A (FAAB starts $100):
  1. wins P1 for $17 -> balance 83
  2. loses a claim on P2 (own bid $30 shown, no deduction) -> 83
  3. commissioner FAAB +10 (recorded faab_after 93) -> 93
  4. pending claim on P3 with bid $99 -> amount None (D6), balance 93
Team B (unaffected) gets only the starting entry. A claimed team
403s without its code.
"""

import sqlite3
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.database import get_db
from api.routers import ledger

SCHEMA = Path(__file__).resolve().parent / "schema.sql"


def _seed(con):
    con.execute("INSERT INTO users (name) VALUES ('w28-owner')")
    league = con.execute(
        "INSERT INTO leagues (name, invite_code, commissioner_id,"
        " season, settings, status) VALUES ('w28', 'CODE-w28', 1,"
        " '2027', '{}', 'in_season')").lastrowid
    teams = {}
    for name in ("A", "B"):
        teams[name] = con.execute(
            "INSERT INTO teams (league_id, name, owner_id, faab_remaining)"
            " VALUES (?, ?, 1, 93)", (league, name)).lastrowid
    players = {}
    for name in ("P1", "P2", "P3"):
        players[name] = con.execute(
            "INSERT INTO players (name, season) VALUES (?, '2027')",
            (name,)).lastrowid
    a = teams["A"]
    rows = [
        ("won", players["P1"], 17, "2027-03-10T00:00:00"),
        ("lost", players["P2"], 30, "2027-03-11T00:00:00"),
        ("pending", players["P3"], 99, "2027-03-12T00:00:00"),
    ]
    for status, pid, bid, ts in rows:
        con.execute(
            "INSERT INTO waiver_claims (league_id, team_id, week_no,"
            " add_player_id, bid, status, created_at) VALUES (?, ?, 1,"
            " ?, ?, ?, ?)", (league, a, pid, bid, status, ts))
    con.execute(
        "INSERT INTO league_adjustments (league_id, team_id, kind,"
        " faab_delta, faab_after, note, created_at) VALUES (?, ?, 'faab',"
        " 10, 93, 'goodwill', '2027-03-11T12:00:00')", (league, a))
    con.commit()
    return {"league": league, "teams": teams}


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / "ledger.db"
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA.read_text())
    ids = _seed(con)
    con.close()
    app = FastAPI()
    app.include_router(ledger.router, prefix="/api/leagues")

    def override():
        c = sqlite3.connect(str(db_path))
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys = ON")
        try:
            yield c
        finally:
            c.close()

    app.dependency_overrides[get_db] = override
    return TestClient(app), ids, db_path


def test_ledger_running_balances(client):
    tc, ids, _ = client
    a = ids["teams"]["A"]
    r = tc.get(f"/api/leagues/{ids['league']}/teams/{a}/ledger")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["starting_faab"] == 100 and body["current_faab"] == 93
    got = [(e["kind"], e["faab_delta"], e["balance_after"]) for e in body["entries"]]
    assert got == [
        ("starting_balance", 0, 100),
        ("waiver_won", -17, 83),
        ("waiver_lost", 0, 83),
        ("commissioner_faab", 10, 93),
        ("waiver_pending", 0, 93),
    ]
    pending = body["entries"][-1]
    assert pending["amount"] is None  # the $99 pending bid never leaks
    assert "99" not in pending["text"]
    assert body["entries"][1]["amount"] == 17
    b = ids["teams"]["B"]
    rb = tc.get(f"/api/leagues/{ids['league']}/teams/{b}/ledger")
    assert [e["kind"] for e in rb.json()["entries"]] == ["starting_balance"]


def test_ledger_claim_gate(client):
    tc, ids, db_path = client
    a = ids["teams"]["A"]
    con = sqlite3.connect(str(db_path))
    con.execute("UPDATE teams SET claim_code = 'sekret' WHERE id = ?", (a,))
    con.commit()
    con.close()
    url = f"/api/leagues/{ids['league']}/teams/{a}/ledger"
    assert tc.get(url).status_code == 403
    assert tc.get(url, headers={"X-Team-Claim": "wrong"}).status_code == 403
    assert tc.get(url, headers={"X-Team-Claim": "sekret"}).status_code == 200
    assert tc.get("/api/leagues/99999/teams/1/ledger").status_code == 404
