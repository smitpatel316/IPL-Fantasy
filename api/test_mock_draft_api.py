"""P5-L1 API test: POST /api/mock-draft/{league_id}.

Scratch sqlite DB (schema.sql) + minimal FastAPI app mounting only the
mock_draft router. Verifies: 200 + full 112-pick draft, D8-legal
rosters for every bot, difficulty divergence, zero writes to the live
league (tables checksummed before/after), and 404/422 contracts.
"""

import sqlite3
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.database import get_db
from api.routers import mock_draft
from api.engine.draft_engine import d8_reachable

SCHEMA = Path(__file__).resolve().parent / "schema.sql"

ROLE_SEQ = ["WK", "BAT", "BAT", "BAT", "AR", "AR", "BOWL", "BOWL",
            "BOWL", "BAT", "BAT", "AR", "BOWL", "WK", "BAT", "BAT"]
N_PLAYERS = 130


def _seed(con):
    con.execute("INSERT INTO users (name) VALUES ('md-owner')")
    cur = con.execute(
        "INSERT INTO leagues (name, invite_code, commissioner_id, season,"
        " settings, status) VALUES ('md', 'CODE-md', 1, '2027', '{}',"
        " 'pre_draft')")
    league_id = cur.lastrowid
    team_ids = []
    for label in ("A", "B"):
        team_ids.append(con.execute(
            "INSERT INTO teams (league_id, owner_id, name, faab_remaining)"
            " VALUES (?, 1, ?, 100)", (league_id, f"md-{label}")).lastrowid)
    pids = []
    for i in range(N_PLAYERS):
        p = con.execute(
            "INSERT INTO players (name, season) VALUES (?, '2027')",
            (f"md-p{i:03d}",)).lastrowid
        pids.append(p)
        con.execute(
            "INSERT INTO player_roles (player_id, season, role, is_overseas,"
            " ipl_team_code, source, status)"
            " VALUES (?, '2027', ?, ?, ?, 'md', NULL)",
            (p, ROLE_SEQ[i % len(ROLE_SEQ)], 1 if i % 2 else 0,
             "MI" if i % 3 == 0 else "CSK"))
        for tid in team_ids:
            con.execute(
                "INSERT OR IGNORE INTO pre_draft_ranks (team_id, player_id,"
                " rank) VALUES (?, ?, ?)", (tid, p, i + 1))
    # A few fixture rows so the sharp bot's schedule weighting is live.
    for w in (1, 2, 3):
        for code, games in (("MI", 2), ("CSK", 1)):
            con.execute(
                "INSERT INTO team_weekly_games (season, week_no, week_start,"
                " week_end, ipl_team_code, games, source)"
                " VALUES ('2027', ?, '2027-03-08', '2027-03-14', ?, ?, 'md')",
                (w, code, games))
    con.commit()
    return league_id


@pytest.fixture()
def env(tmp_path):
    con = sqlite3.connect(str(tmp_path / "md.db"), check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA.read_text())
    league_id = _seed(con)

    app = FastAPI()
    app.include_router(mock_draft.router, prefix="/api/mock-draft")

    def _override_get_db():
        yield con

    app.dependency_overrides[get_db] = _override_get_db
    yield con, TestClient(app), league_id
    con.close()


def _snapshot(con):
    tables = ["leagues", "teams", "users", "players", "player_roles",
              "pre_draft_ranks", "roster_slots", "drafts", "engine_state",
              "team_weekly_games"]
    snap = {}
    for t in tables:
        try:
            snap[t] = con.execute(f"SELECT * FROM {t}").fetchall()
        except sqlite3.OperationalError:
            snap[t] = None
    return snap


def test_mock_draft_full_flow(env):
    con, client, league_id = env
    before = _snapshot(con)
    r = client.post(f"/api/mock-draft/{league_id}", json={
        "bots": [{"name": f"B{i}", "difficulty": "sharp" if i % 2 == 0 else "casual"}
                 for i in range(8)],
        "seed": 11,
    })
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["rounds"] == 14
    assert out["seed"] == 11
    assert len(out["picks"]) == 112
    assert [p["pick_no"] for p in out["picks"]] == list(range(1, 113))
    assert out["schedule_weighted"] is True
    # Zero writes to the live league.
    assert _snapshot(con) == before
    # Every team: 14 players, D8-legal end state.
    role_of = {row[0]: (row[1], row[2]) for row in con.execute(
        "SELECT player_id, role, is_overseas FROM player_roles"
        " WHERE season = '2027'").fetchall()}
    name_to_id = {row[1]: row[0] for row in con.execute(
        "SELECT id, name FROM players WHERE season = '2027'").fetchall()}
    for t in out["teams"]:
        n = sum(len(v) for v in t["roster"].values())
        assert n == 14, (t["name"], n)
        d, o = {}, {}
        for pids in t["roster"].values():
            for pname in pids:
                role, os_ = role_of[name_to_id[pname]]
                tgt = o if os_ else d
                tgt[role] = tgt.get(role, 0) + 1
        assert d8_reachable(d, o, 0), f"{t['name']} not D8-legal"
    # Difficulty diverges: worst sharp avg consensus rank < best casual.
    sharp = [t["avg_consensus_rank"] for t in out["teams"]
             if t["difficulty"] == "sharp"]
    casual = [t["avg_consensus_rank"] for t in out["teams"]
              if t["difficulty"] == "casual"]
    assert max(sharp) < min(casual), (sharp, casual)
    # No player drafted twice.
    ids = [p["player_id"] for p in out["picks"]]
    assert len(set(ids)) == 112


def test_mock_draft_default_bots_and_seed(env):
    _con, client, league_id = env
    r = client.post(f"/api/mock-draft/{league_id}", json={})
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["seed"] == 42
    assert len(out["teams"]) == 8
    diffs = [t["difficulty"] for t in out["teams"]]
    assert set(diffs) == {"sharp", "casual"}
    # Deterministic: same request twice -> identical picks.
    r2 = client.post(f"/api/mock-draft/{league_id}", json={})
    assert [p["player_id"] for p in r2.json()["picks"]] == \
        [p["player_id"] for p in out["picks"]]


def test_mock_draft_unknown_league_404(env):
    _con, client, _lid = env
    r = client.post("/api/mock-draft/9999", json={})
    assert r.status_code == 404, r.text


def test_mock_draft_bad_difficulty_422(env):
    _con, client, league_id = env
    r = client.post(f"/api/mock-draft/{league_id}", json={
        "bots": [{"name": "X", "difficulty": "grandmaster"},
                 {"name": "Y", "difficulty": "sharp"}]})
    assert r.status_code == 422, r.text


def test_mock_draft_duplicate_names_422(env):
    _con, client, league_id = env
    r = client.post(f"/api/mock-draft/{league_id}", json={
        "bots": [{"name": "X", "difficulty": "sharp"},
                 {"name": "X", "difficulty": "casual"}]})
    assert r.status_code == 422, r.text


def test_mock_draft_too_few_bots_422(env):
    _con, client, league_id = env
    r = client.post(f"/api/mock-draft/{league_id}", json={
        "bots": [{"name": "Solo", "difficulty": "sharp"}]})
    assert r.status_code == 422, r.text
