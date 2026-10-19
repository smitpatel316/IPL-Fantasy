"""P5-W48: weekly recap — hand-derived.

Scratch league with 4 teams (A, B, C, D), two scored weeks:
  week 1: A 150 vs B 100 (A wins), C 140 vs D 138 (C wins)
  week 2: A 90 vs C 200 (C wins), B 110 vs D 120 (D wins)
Pre-week-2 averages: A 150, B 100, C 140, D 138.

Hand-derived week-2 facts:
- biggest upset: C beat A — C's pre-week avg (140) was below A's (150),
  delta 10 (D beat B as the favorite, so no upset there)
- highest scorer: C with 200 (vs A)
- closest matchup: D 120-110 B, margin 10
- biggest blowout: C 200-90 A, margin 110

Checks: facts match the hand-derived values; week 3 (no finals)
returns scored=false and facts=[]; week 0/9 -> 422; unknown league 404s.
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
    p = tmp_path / "w48.db"
    c = sqlite3.connect(str(p))
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA.read_text())
    c.execute("PRAGMA foreign_keys = ON")

    c.execute("INSERT INTO users (name) VALUES ('commish')")
    l1 = c.execute(
        "INSERT INTO leagues (name, invite_code, commissioner_id, season,"
        " settings, status) VALUES ('w48', 'CODE-w48', 1, '2027', '{}',"
        " 'in_season')").lastrowid
    t = {}
    for name in ("A", "B", "C", "D"):
        t[name] = c.execute(
            "INSERT INTO teams (league_id, name, owner_id, faab_remaining)"
            " VALUES (?, ?, 1, 100)", (l1, name)).lastrowid
    for wk, ta, tb, sa, sb in [
            (1, "A", "B", 150, 100), (1, "C", "D", 140, 138),
            (2, "A", "C", 90, 200), (2, "B", "D", 110, 120)]:
        c.execute(
            "INSERT INTO matchups (league_id, week_no, team_a_id, team_b_id,"
            " score_a, score_b, status) VALUES (?, ?, ?, ?, ?, ?, 'final')",
            (l1, wk, t[ta], t[tb], sa, sb))
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
        yield tt, l1


def test_week2_facts_hand_derived(client):
    t, l1 = client
    r = t.get(f"/api/leagues/{l1}/recap/2")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["scored"] is True and body["matchup_count"] == 2
    facts = {f["key"]: f for f in body["facts"]}

    upset = facts["biggest_upset"]
    assert upset["value"] == "+10 underdog"
    assert "C" in upset["detail"] and "A" in upset["detail"]
    assert "140" in upset["detail"] and "150" in upset["detail"]

    hs = facts["highest_scorer"]
    assert hs["value"] == "200"
    assert "C" in hs["detail"] and "A" in hs["detail"]

    close = facts["closest_matchup"]
    assert close["value"] == "10"
    assert "D" in close["detail"] and "B" in close["detail"]

    blow = facts["biggest_blowout"]
    assert blow["value"] == "110"
    assert "C" in blow["detail"] and "A" in blow["detail"]


def test_unscored_week_empty_state(client):
    t, l1 = client
    r = t.get(f"/api/leagues/{l1}/recap/3")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["scored"] is False
    assert body["facts"] == []


def test_bad_week_and_unknown_league(client):
    t, l1 = client
    assert t.get(f"/api/leagues/{l1}/recap/0").status_code == 422
    assert t.get(f"/api/leagues/{l1}/recap/9").status_code == 422
    assert t.get("/api/leagues/99999/recap/2").status_code == 404
