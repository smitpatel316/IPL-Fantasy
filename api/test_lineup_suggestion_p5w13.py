"""P5-W13: lineup optimizer — Suggested XI.

Hand-derived fixtures:
  Team A (14 domestic players, consensus ranks 1..14 in roster order):
  ranks 1-11 form a legal XI by construction (WK1 BAT3 AR2 BOWL3 +
  UTIL = the rank-10 BAT and rank-11 AR), so the solver must return
  exactly ranks 1..11 as starters and ranks 12..14 on BN.
  Team B (5 overseas stars at ranks 1..5 + 9 domestic at ranks 6..14):
  the D8 cap forces exactly one overseas star out of the XI — the
  solver drops the rank-5 BOWL star (cheapest swap: +7 total rank vs
  +11 for the rank-1 WK), so overseas_starters == 4 and the rank-5
  player sits on BN.
  Team C: a 15-man roster whose rank-1 WK is injured (status) and sits
  in the week-2 IL slot: the week-2 suggestion excludes him from the
  XI, returns him in IL, and starts the rank-2..12 domestic XI.
"""

import sqlite3
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.database import get_db
from api.routers import lineups

SCHEMA = Path(__file__).resolve().parent / "schema.sql"


def _player(con, name, role, overseas, rank, team_id, status=None):
    pid = con.execute(
        "INSERT INTO players (name, season) VALUES (?, '2027')",
        (name,)).lastrowid
    con.execute(
        "INSERT INTO player_roles (player_id, season, role, is_overseas,"
        " ipl_team_code, status) VALUES (?, '2027', ?, ?, 'MI', ?)",
        (pid, role, overseas, status))
    con.execute(
        "INSERT INTO pre_draft_ranks (team_id, player_id, rank)"
        " VALUES (?, ?, ?)", (team_id, pid, rank))
    con.execute(
        "INSERT INTO roster_slots (team_id, player_id, slot)"
        " VALUES (?, ?, 'BN')", (team_id, pid))
    return pid


def _team(con, league, name):
    return con.execute(
        "INSERT INTO teams (league_id, owner_id, name, faab_remaining)"
        " VALUES (?, 1, ?, 100)", (league, name)).lastrowid


def _seed(con):
    con.execute("INSERT INTO users (name) VALUES ('w13-owner')")
    league = con.execute(
        "INSERT INTO leagues (name, invite_code, commissioner_id,"
        " season, settings, status) VALUES ('w13-league', 'CODE-w13',"
        " 1, '2027', '{}', 'in_season')").lastrowid
    ids = {"league": league}

    # Team A: ranks 1..14, roles in XI order then bench.
    ta = _team(con, league, "w13-A")
    ids["teamA"] = ta
    plan_a = ["WK", "BAT", "BAT", "BAT", "AR", "AR", "BOWL", "BOWL",
              "BOWL", "BAT", "AR", "BOWL", "BAT", "WK"]
    ids["a"] = [
        _player(con, f"A{i + 1}", role, 0, i + 1, ta)
        for i, role in enumerate(plan_a)
    ]

    # Team B: overseas stars ranks 1..5, domestic ranks 6..14.
    tb = _team(con, league, "w13-B")
    ids["teamB"] = tb
    plan_b = [("WK", 1), ("BAT", 1), ("BAT", 1), ("AR", 1), ("BOWL", 1),
              ("BAT", 0), ("BAT", 0), ("AR", 0), ("BOWL", 0), ("BOWL", 0),
              ("BOWL", 0), ("AR", 0), ("BAT", 0), ("WK", 0)]
    ids["b"] = [
        _player(con, f"B{i + 1}", role, os_, i + 1, tb)
        for i, (role, os_) in enumerate(plan_b)
    ]

    # Team C: rank-1 injured WK (IL in week 2) + team A's shape at 2..15.
    tc_ = _team(con, league, "w13-C")
    ids["teamC"] = tc_
    hurt = _player(con, "C-hurt", "WK", 0, 1, tc_, status="injured")
    ids["hurt"] = hurt
    ids["c"] = [
        _player(con, f"C{i + 2}", role, 0, i + 2, tc_)
        for i, role in enumerate(plan_a)
    ]
    con.execute(
        "INSERT INTO roster_slots (team_id, player_id, slot, week_no)"
        " VALUES (?, ?, 'IL', 2)", (tc_, hurt))
    con.commit()
    return ids


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / "suggestion.db"
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA.read_text())
    ids = _seed(con)
    con.close()

    app = FastAPI()
    app.include_router(lineups.router, prefix="/api")

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


def _starters(body):
    return {pid for slot, pids in body["slots"].items()
            if slot not in ("BN", "IL") for pid in pids}


def test_suggestion_matches_hand_derived_xi(client):
    tc, ids, _ = client
    r = tc.get(f"/api/teams/{ids['teamA']}/lineup/suggestion",
               params={"week_no": 1})
    assert r.status_code == 200, r.text
    body = r.json()
    a = ids["a"]
    assert _starters(body) == set(a[:11])
    assert set(body["slots"]["BN"]) == set(a[11:])
    assert body["slots"]["WK"] == [a[0]]
    assert set(body["slots"]["UTIL"]) == {a[9], a[10]}
    assert body["valid"] is True and body["overseas_starters"] == 0
    assert "preseason rank" in body["basis"]


def test_suggestion_respects_d8_cap(client):
    tc, ids, _ = client
    r = tc.get(f"/api/teams/{ids['teamB']}/lineup/suggestion",
               params={"week_no": 1})
    assert r.status_code == 200, r.text
    body = r.json()
    b = ids["b"]
    assert body["overseas_starters"] == 4
    # The rank-5 overseas BOWL star is the one benched by the cap.
    assert b[4] in body["slots"]["BN"]
    assert _starters(body) == set(b[:4]) | set(b[5:12])


def test_suggestion_excludes_il_occupant(client):
    tc, ids, _ = client
    r = tc.get(f"/api/teams/{ids['teamC']}/lineup/suggestion",
               params={"week_no": 2})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["slots"]["IL"] == [ids["hurt"]]
    assert _starters(body) == set(ids["c"][:11])
    assert body["valid"] is True


def test_suggestion_is_read_only_and_put_round_trips(client):
    tc, ids, db_path = client
    con = sqlite3.connect(str(db_path))
    before = con.execute("SELECT COUNT(*) FROM roster_slots").fetchone()[0]
    con.close()
    r = tc.get(f"/api/teams/{ids['teamA']}/lineup/suggestion",
               params={"week_no": 3})
    assert r.status_code == 200, r.text
    con = sqlite3.connect(str(db_path))
    after = con.execute("SELECT COUNT(*) FROM roster_slots").fetchone()[0]
    con.close()
    assert after == before  # zero writes
    put = tc.put(f"/api/teams/{ids['teamA']}/lineup",
                 json={"week_no": 3, "slots": r.json()["slots"]})
    assert put.status_code == 200, put.text
    assert put.json()["valid"] is True


def test_suggestion_bounds(client):
    tc, ids, _ = client
    base = f"/api/teams/{ids['teamA']}/lineup/suggestion"
    assert tc.get(base, params={"week_no": 99}).status_code == 422
    assert tc.get(base, params={"week_no": 0}).status_code == 422
    assert tc.get("/api/teams/99999/lineup/suggestion",
                  params={"week_no": 1}).status_code == 404
