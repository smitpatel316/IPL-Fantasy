"""P5-W45: My leagues switcher — hand-derived.

Scratch setup: two leagues (L1 'Alpha', L2 'Beta'). L1 has teams A and B
with three FINAL matchups: A beats B week 1 (150-100), B beats A week 2
(140-130), tie week 3 (120-120); plus one SCHEDULED matchup (counts 0).
L2 has team C with no matchups yet.

Checks:
- GET /api/leagues/my-leagues?team_ids={A},{C} lists both leagues with
  correct records (A: 1-1-1, 400 PF; C: 0-0-0) and correct league
  names/seasons, in the order of the ids passed.
- Unknown team ids are skipped (deleted team from another device).
- claim_code never appears in the payload.
- Empty team_ids -> 422; malformed id -> 422; too many -> 422.
- GET /api/leagues/{id} still returns the same W-L-T (refactor didn't
  change the standings math).
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
    p = tmp_path / "w45.db"
    c = sqlite3.connect(str(p))
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA.read_text())
    c.execute("PRAGMA foreign_keys = ON")

    c.execute("INSERT INTO users (name) VALUES ('commish')")
    l1 = c.execute(
        "INSERT INTO leagues (name, invite_code, commissioner_id, season,"
        " settings, status) VALUES ('Alpha', 'CODE-A', 1, '2027', '{}',"
        " 'in_season')").lastrowid
    l2 = c.execute(
        "INSERT INTO leagues (name, invite_code, commissioner_id, season,"
        " settings, status) VALUES ('Beta', 'CODE-B', 1, '2027', '{}',"
        " 'setup')").lastrowid
    a = c.execute(
        "INSERT INTO teams (league_id, name, owner_id, faab_remaining,"
        " claim_code) VALUES (?, 'A', 1, 100, 'CODEA')", (l1,)).lastrowid
    b = c.execute(
        "INSERT INTO teams (league_id, name, owner_id, faab_remaining,"
        " claim_code) VALUES (?, 'B', 1, 100, 'CODEB')", (l1,)).lastrowid
    cc = c.execute(
        "INSERT INTO teams (league_id, name, owner_id, faab_remaining,"
        " claim_code) VALUES (?, 'C', 1, 100, 'CODEC')", (l2,)).lastrowid
    # week 1: A 150 beats B 100; week 2: B 140 beats A 130;
    # week 3: tie 120-120; week 4: scheduled (counts 0).
    c.execute(
        "INSERT INTO matchups (league_id, week_no, team_a_id, team_b_id,"
        " score_a, score_b, status) VALUES (?, 1, ?, ?, 150, 100, 'final')",
        (l1, a, b))
    c.execute(
        "INSERT INTO matchups (league_id, week_no, team_a_id, team_b_id,"
        " score_a, score_b, status) VALUES (?, 2, ?, ?, 130, 140, 'final')",
        (l1, a, b))
    c.execute(
        "INSERT INTO matchups (league_id, week_no, team_a_id, team_b_id,"
        " score_a, score_b, status) VALUES (?, 3, ?, ?, 120, 120, 'final')",
        (l1, a, b))
    c.execute(
        "INSERT INTO matchups (league_id, week_no, team_a_id, team_b_id,"
        " score_a, score_b, status) VALUES (?, 4, ?, ?, 0, 0, 'scheduled')",
        (l1, a, b))
    c.commit()
    c.close()

    app = FastAPI()

    def override():
        c = sqlite3.connect(str(p))
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys = ON")
        try:
            yield c
        finally:
            c.close()

    app.dependency_overrides[get_db] = override

    # same shape as api/index.py for these two routes
    app.include_router(leagues.router, prefix="/api/leagues")

    with TestClient(app) as t:
        yield t, (l1, l2, a, b, cc)


def test_my_leagues_lists_both_with_correct_records(client):
    t, (l1, l2, a, b, cc) = client
    r = t.get(f"/api/leagues/my-leagues?team_ids={a},{cc}")
    assert r.status_code == 200, r.text
    rows = r.json()
    assert len(rows) == 2
    # order follows the ids passed
    assert rows[0]["team_id"] == a and rows[0]["league_id"] == l1
    assert rows[0]["league_name"] == "Alpha"
    assert rows[0]["season"] == "2027"
    assert rows[0]["league_status"] == "in_season"
    assert rows[0]["wins"] == 1 and rows[0]["losses"] == 1
    assert rows[0]["ties"] == 1
    assert rows[0]["points_for"] == 400.0  # 150 + 130 + 120
    assert rows[1]["team_id"] == cc and rows[1]["league_id"] == l2
    assert rows[1]["league_name"] == "Beta"
    assert rows[1]["wins"] == 0 and rows[1]["losses"] == 0
    assert rows[1]["points_for"] == 0.0


def test_my_leagues_both_sides_and_no_code_leak(client):
    t, (l1, l2, a, b, cc) = client
    r = t.get(f"/api/leagues/my-leagues?team_ids={b}")
    assert r.status_code == 200, r.text
    row = r.json()[0]
    assert row["wins"] == 1 and row["losses"] == 1 and row["ties"] == 1
    assert row["points_for"] == 360.0  # 100 + 140 + 120
    assert "claim_code" not in row
    assert "claim_code" not in r.text


def test_my_leagues_skips_unknown_teams(client):
    t, (l1, l2, a, b, cc) = client
    r = t.get(f"/api/leagues/my-leagues?team_ids={a},99999")
    assert r.status_code == 200, r.text
    assert len(r.json()) == 1


def test_my_leagues_validation(client):
    t, (l1, l2, a, b, cc) = client
    assert t.get("/api/leagues/my-leagues").status_code == 422
    assert t.get("/api/leagues/my-leagues?team_ids=").status_code == 422
    assert t.get("/api/leagues/my-leagues?team_ids=abc").status_code == 422
    big = ",".join(str(i) for i in range(1, 102))
    assert t.get(f"/api/leagues/my-leagues?team_ids={big}").status_code == 422


def test_league_detail_standings_unchanged_by_refactor(client):
    t, (l1, l2, a, b, cc) = client
    r = t.get(f"/api/leagues/{l1}")
    assert r.status_code == 200, r.text
    rows = {s["team_id"]: s for s in r.json()["standings"]}
    assert (rows[a]["wins"], rows[a]["losses"], rows[a]["ties"]) == (1, 1, 1)
    assert (rows[b]["wins"], rows[b]["losses"], rows[b]["ties"]) == (1, 1, 1)
