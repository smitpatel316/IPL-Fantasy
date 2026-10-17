"""P5-W20: notifications inbox — hand-derived fixture.

Teams A, B, C in one league; players P1, P2.
Scripted history:
  * trade 1: B -> A, 'proposed', gives [P1] receives [P2],
    proposed_at 2027-03-01 10:00  => A: trade_proposed; B: nothing yet;
    C: nothing.
  * trade 2: A -> B, 'executed', executed_at 2027-03-02 10:00
    => A + B: trade_executed.
  * trade 3: A -> C, 'rejected', created 2027-03-03 10:00
    => A: trade_rejected; C: nothing (only proposer is notified).
  * waiver: A won P1 bid 17 (week 1, created 2027-03-04 10:00);
    A lost P2 (created 2027-03-04 11:00, no amount anywhere);
    B has a PENDING claim bid 99 — must never appear for anyone.
  * adjustment: FAAB +5 on A (2027-03-05 10:00, note 'fix').
Expected A inbox (newest first): adj, waiver_lost, waiver_won,
trade_rejected, trade_executed, trade_proposed = 6 entries, 6 unread.
B inbox: trade_executed only = 1. C inbox: empty.
Mark-as-read (A, claimed with code): unread -> 0, survives a fresh
request; a later event (new adjustment) makes unread 1 again.
Wrong claim code on read or mark -> 403.
"""
import sqlite3
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.database import get_db
from api.routers import notifications

SCHEMA = Path(__file__).resolve().parent / "schema.sql"


def _seed(con):
    con.execute("INSERT INTO users (name) VALUES ('w20-owner')")
    league = con.execute(
        "INSERT INTO leagues (name, invite_code, commissioner_id, season, settings, status)"
        " VALUES ('w20-league','CODE-w20',1,'2027','{}','in_season')").lastrowid
    teams = {}
    for label in ("A", "B", "C"):
        teams[label] = con.execute(
            "INSERT INTO teams (league_id, owner_id, name, faab_remaining)"
            " VALUES (?,1,?,100)", (league, f"w20-{label}")).lastrowid
    players = {}
    for label in ("P1", "P2"):
        players[label] = con.execute(
            "INSERT INTO players (name, season) VALUES (?, '2027')", (label,)).lastrowid
    A, B, C = teams["A"], teams["B"], teams["C"]
    P1, P2 = players["P1"], players["P2"]
    con.execute(
        "INSERT INTO trades (league_id, from_team_id, to_team_id, gives, receives,"
        " status, proposed_at, created_at) VALUES (?,?,?,?,?,'proposed',?,?)",
        (league, B, A, f"[{P1}]", f"[{P2}]", "2027-03-01 10:00:00", "2027-03-01 10:00:00"))
    con.execute(
        "INSERT INTO trades (league_id, from_team_id, to_team_id, gives, receives,"
        " status, executed_at, created_at) VALUES (?,?,?,?,?,'executed',?,?)",
        (league, A, B, f"[{P2}]", f"[{P1}]", "2027-03-02 10:00:00", "2027-03-01 12:00:00"))
    con.execute(
        "INSERT INTO trades (league_id, from_team_id, to_team_id, gives, receives,"
        " status, created_at) VALUES (?,?,?,?,?,'rejected',?)",
        (league, A, C, f"[{P1}]", f"[{P2}]", "2027-03-03 10:00:00"))
    con.execute(
        "INSERT INTO waiver_claims (league_id, week_no, team_id, add_player_id, bid, status, created_at)"
        " VALUES (?,1,?,?,17,'won','2027-03-04 10:00:00')", (league, A, P1))
    con.execute(
        "INSERT INTO waiver_claims (league_id, week_no, team_id, add_player_id, bid, status, created_at)"
        " VALUES (?,1,?,?,9,'lost','2027-03-04 11:00:00')", (league, A, P2))
    con.execute(
        "INSERT INTO waiver_claims (league_id, week_no, team_id, add_player_id, bid, status, created_at)"
        " VALUES (?,1,?,?,99,'pending','2027-03-04 12:00:00')", (league, B, P1))
    con.execute(
        "INSERT INTO league_adjustments (league_id, team_id, kind, faab_delta, faab_after, note, created_at)"
        " VALUES (?,?, 'faab', 5, 105, 'fix', '2027-03-05 10:00:00')", (league, A))
    con.commit()
    return league, teams


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / "w20.db"
    con = sqlite3.connect(str(db_path)); con.row_factory = sqlite3.Row
    con.executescript(SCHEMA.read_text())
    league, teams = _seed(con)
    con.close()
    app = FastAPI(); app.include_router(notifications.router, prefix="/api/leagues")
    def override():
        c = sqlite3.connect(str(db_path)); c.row_factory = sqlite3.Row
        try: yield c
        finally: c.close()
    app.dependency_overrides[get_db] = override
    return TestClient(app), league, teams, db_path


def _get(tc, league, team, **kw):
    r = tc.get(f"/api/leagues/{league}/notifications", params={"team_id": team}, **kw)
    assert r.status_code == 200, r.text
    return r.json()


def test_inbox_matches_hand_derived_history(client):
    tc, league, teams, _ = client
    body = _get(tc, league, teams["A"])
    kinds = [e["kind"] for e in body["entries"]]
    assert kinds == ["commissioner_faab", "waiver_lost", "waiver_won",
                     "trade_rejected", "trade_executed", "trade_proposed"]
    assert body["total"] == 6 and body["unread_count"] == 6
    won = next(e for e in body["entries"] if e["kind"] == "waiver_won")
    lost = next(e for e in body["entries"] if e["kind"] == "waiver_lost")
    assert won["amount"] == 17 and lost["amount"] is None
    # D6: B's pending $99 bid appears nowhere in A's payload
    assert "99" not in str(body)


def test_other_teams_inboxes(client):
    tc, league, teams, _ = client
    b = _get(tc, league, teams["B"])
    assert [e["kind"] for e in b["entries"]] == ["trade_executed"]
    c = _get(tc, league, teams["C"])
    assert c["total"] == 0 and c["unread_count"] == 0 and c["entries"] == []


def test_mark_read_persists_and_new_events_unread(client):
    tc, league, teams, db_path = client
    A = teams["A"]
    r = tc.post(f"/api/leagues/{league}/notifications/read", params={"team_id": A})
    assert r.status_code == 200 and r.json()["unread_count"] == 0
    again = _get(tc, league, A)
    assert again["unread_count"] == 0 and all(e["read"] for e in again["entries"])
    con = sqlite3.connect(str(db_path))
    con.execute(
        "INSERT INTO league_adjustments (league_id, team_id, kind, faab_delta, faab_after, note, created_at)"
        " VALUES (?,?, 'faab', -3, 102, 'later', '2027-03-06 10:00:00')", (league, A))
    con.commit(); con.close()
    after = _get(tc, league, A)
    assert after["unread_count"] == 1 and after["entries"][0]["read"] is False


def test_claim_gate(client):
    tc, league, teams, db_path = client
    A = teams["A"]
    con = sqlite3.connect(str(db_path))
    con.execute("UPDATE teams SET claim_code = 'SECRET1234' WHERE id = ?", (A,))
    con.commit(); con.close()
    assert tc.get(f"/api/leagues/{league}/notifications",
                  params={"team_id": A}).status_code == 403
    assert tc.post(f"/api/leagues/{league}/notifications/read",
                   params={"team_id": A}).status_code == 403
    ok = tc.get(f"/api/leagues/{league}/notifications", params={"team_id": A},
                headers={"X-Team-Claim": "SECRET1234"})
    assert ok.status_code == 200 and ok.json()["total"] == 6


def test_unknown_league_and_wrong_league_team(client):
    tc, league, teams, _ = client
    assert tc.get("/api/leagues/99999/notifications",
                  params={"team_id": teams["A"]}).status_code == 404
    assert tc.get(f"/api/leagues/{league}/notifications",
                  params={"team_id": 99999}).status_code == 404
