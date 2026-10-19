"""P5-W47: waiver wire order display — hand-derived.

Scratch league with 4 teams, 3 final weeks:
  week 1: A 150 vs B 100  (A 1-0, B 0-1)
  week 2: C 140 vs D 138  (C 1-0, D 0-1)
  week 3: A 120 vs C 130  (C 2-0, A 1-1)

Standings best-first (wins, then PF): C (2-0, 270), A (1-1, 270),
B (0-1, 100), D (0-1, 138).
Tiebreak order (reverse of the engine's best-first): B, D, A, C.

Checks:
- GET /api/leagues/{id}/waivers/order returns positions 1..4 in
  D,B,A,C order with correct W-L.
- order == reverse of the /leagues/{id} standings endpoint order.
- After a 4th final matchup (B beats D 200-50 => B 1-1, D 0-2),
  the order updates: D (0-2) still first, then B (1-1, 300), A (1-1,
  270), C (2-0).
- Unknown league 404s.
"""

import sqlite3
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.database import get_db
from api.routers import leagues

SCHEMA = Path(__file__).resolve().parent / "schema.sql"


@pytest.fixture
def client(tmp_path):
    p = tmp_path / "w47.db"
    c = sqlite3.connect(str(p))
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA.read_text())
    c.execute("PRAGMA foreign_keys = ON")

    c.execute("INSERT INTO users (name) VALUES ('commish')")
    l1 = c.execute(
        "INSERT INTO leagues (name, invite_code, commissioner_id, season,"
        " settings, status) VALUES ('w47', 'CODE-w47', 1, '2027', '{}',"
        " 'in_season')").lastrowid
    t = {}
    for name in ("A", "B", "C", "D"):
        t[name] = c.execute(
            "INSERT INTO teams (league_id, name, owner_id, faab_remaining)"
            " VALUES (?, ?, 1, 100)", (l1, name)).lastrowid
    for wk, ta, tb, sa, sb in [
            (1, "A", "B", 150, 100), (2, "C", "D", 140, 138),
            (3, "A", "C", 120, 130)]:
        c.execute(
            "INSERT INTO matchups (league_id, week_no, team_a_id, team_b_id,"
            " score_a, score_b, status) VALUES (?, ?, ?, ?, ?, ?, 'final')",
            (l1, wk, t[ta], t[tb], sa, sb))
    c.commit()

    app = FastAPI()

    def override():
        cc = sqlite3.connect(str(p))
        cc.row_factory = sqlite3.Row
        cc.execute("PRAGMA foreign_keys = ON")
        try:
            yield cc
        finally:
            cc.close()

    app.dependency_overrides[get_db] = override
    app.include_router(leagues.router, prefix="/api/leagues")

    with TestClient(app) as tt:
        yield tt, (l1, t, p)


def test_tiebreak_order_hand_derived(client):
    t, (l1, teams, p) = client
    r = t.get(f"/api/leagues/{l1}/waivers/order")
    assert r.status_code == 200, r.text
    order = r.json()["order"]
    assert [o["team_name"] for o in order] == ["B", "D", "A", "C"]
    assert [o["position"] for o in order] == [1, 2, 3, 4]
    rec = {o["team_name"]: (o["wins"], o["losses"]) for o in order}
    assert rec == {"D": (0, 1), "B": (0, 1), "A": (1, 1), "C": (2, 0)}
    assert "Reverse standings" in r.json()["basis"]


def test_order_matches_reverse_standings_endpoint(client):
    t, (l1, teams, p) = client
    order = t.get(f"/api/leagues/{l1}/waivers/order").json()["order"]
    standings = t.get(f"/api/leagues/{l1}").json()["standings"]
    assert [o["team_id"] for o in order] == [
        s["team_id"] for s in reversed(standings)]


def test_order_updates_after_standings_change(client):
    t, (l1, teams, p) = client
    c = sqlite3.connect(str(p))
    c.execute(
        "INSERT INTO matchups (league_id, week_no, team_a_id, team_b_id,"
        " score_a, score_b, status) VALUES (?, 4, ?, ?, 200, 50, 'final')",
        (l1, teams["B"], teams["D"]))
    c.commit()
    c.close()
    order = t.get(f"/api/leagues/{l1}/waivers/order").json()["order"]
    # B 1-1 (PF 300) outranks A 1-1 (PF 270) in the engine's best-first
    # order, so reversed B sits behind A; D drops to 0-2 and stays first.
    assert [o["team_name"] for o in order] == ["D", "A", "B", "C"]
    rec = {o["team_name"]: (o["wins"], o["losses"]) for o in order}
    assert rec["B"] == (1, 1) and rec["D"] == (0, 2)


def test_unknown_league_404(client):
    t, (l1, teams, p) = client
    assert t.get("/api/leagues/99999/waivers/order").status_code == 404
