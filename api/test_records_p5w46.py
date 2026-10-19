"""P5-W46: league records book — hand-derived.

Scratch league with 4 teams (A, B, C, D), 4 final weeks:
  week 1: A 150 vs B 100  (A wins, margin 50)
  week 2: C 140 vs D 138  (C wins, margin 2 — narrowest)
  week 3: A 120 vs C 120  (tie)
  week 4: A 130 vs D 90   (A wins, margin 40)
  week 5: scheduled, A vs B 0-0 (counts 0)

Hand-derived records:
- highest weekly score: 150 (A, week 1)
- largest margin: 50 (A 150-100 B, week 1)
- longest win streak: 1 week — A wins week 1, ties week 3 (reset), wins
  week 4 => best run is 1 (weeks 1 and 4); C wins week 2 only => 1;
  alphabetically first team with run 1 is A (week 1)
- narrowest win: 2 (C 140-138 D, week 2)
- most points in a loss: 138 (D, week 2)

Checks: all five records match the hand-derived values; scored=4;
an unscored league returns scored=0 and records=[]; unknown league 404s.
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
    p = tmp_path / "w46.db"
    c = sqlite3.connect(str(p))
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA.read_text())
    c.execute("PRAGMA foreign_keys = ON")

    c.execute("INSERT INTO users (name) VALUES ('commish')")
    l1 = c.execute(
        "INSERT INTO leagues (name, invite_code, commissioner_id, season,"
        " settings, status) VALUES ('r46', 'CODE-r46', 1, '2027', '{}',"
        " 'in_season')").lastrowid
    l2 = c.execute(
        "INSERT INTO leagues (name, invite_code, commissioner_id, season,"
        " settings, status) VALUES ('fresh', 'CODE-r46b', 1, '2027', '{}',"
        " 'setup')").lastrowid
    t = {}
    for name in ("A", "B", "C", "D"):
        t[name] = c.execute(
            "INSERT INTO teams (league_id, name, owner_id, faab_remaining)"
            " VALUES (?, ?, 1, 100)", (l1, name)).lastrowid
    games = [
        (1, "A", "B", 150, 100, "final"),
        (2, "C", "D", 140, 138, "final"),
        (3, "A", "C", 120, 120, "final"),
        (4, "A", "D", 130, 90, "final"),
        (5, "A", "B", 0, 0, "scheduled"),
    ]
    for wk, ta, tb, sa, sb, st in games:
        c.execute(
            "INSERT INTO matchups (league_id, week_no, team_a_id, team_b_id,"
            " score_a, score_b, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (l1, wk, t[ta], t[tb], sa, sb, st))
    c.commit()
    c.close()

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
        yield tt, (l1, l2)


def _recs(client, l1):
    t, _ = client
    r = t.get(f"/api/leagues/{l1}/records")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["league_id"] == l1
    return {rec["key"]: rec for rec in body["records"]}, body


def test_all_five_records_hand_derived(client):
    t, (l1, l2) = client
    recs, body = _recs(client, l1)
    assert body["scored"] == 4  # the scheduled week-5 game counts 0

    hs = recs["highest_weekly_score"]
    assert hs["value"] == "150"
    assert "A" in hs["detail"] and "week 1" in hs["detail"]

    lm = recs["largest_margin"]
    assert lm["value"] == "50"
    assert "A" in lm["detail"] and "B" in lm["detail"]
    assert "week 1" in lm["detail"]

    nw = recs["narrowest_win"]
    assert nw["value"] == "2"
    assert "C" in nw["detail"] and "D" in nw["detail"]
    assert "week 2" in nw["detail"]

    mpl = recs["most_points_in_loss"]
    assert mpl["value"] == "138"
    assert "D" in mpl["detail"] and "week 2" in mpl["detail"]

    # A: W1 win, W3 tie (reset), W4 win => best run 1 (earliest, week 1).
    streak = recs["longest_win_streak"]
    assert streak["value"] == "1 week"
    assert "A" in streak["detail"] and "week 1" in streak["detail"]


def test_unscored_league_empty_state(client):
    t, (l1, l2) = client
    r = t.get(f"/api/leagues/{l2}/records")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["scored"] == 0
    assert body["records"] == []


def test_unknown_league_404(client):
    t, (l1, l2) = client
    assert t.get("/api/leagues/99999/records").status_code == 404
