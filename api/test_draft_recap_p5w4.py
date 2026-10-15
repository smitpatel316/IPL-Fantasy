"""P5-W4: draft recap + grades.

Hand-derived fixture: 2 teams, ranked pool of 4 (consensus ranks
1..4, values 4/3/2/1 with pool N=4). Snake picks:
  #1 T1 -> rank-2 player (value 3, delta -1: reach)
  #2 T2 -> rank-1 player (value 4, delta +1: steal)
  #3 T2 -> rank-3 player (value 2, delta 0)
  #4 T1 -> rank-4 player (value 1, delta 0)
Expected value per team = value(its pick numbers) = 5 for both.
T1 projected 4 -> ratio 0.8 -> grade F. T2 projected 6 -> 1.2 -> A.
"""

import sqlite3
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.database import get_db
from api.routers import leagues

SCHEMA = Path(__file__).resolve().parent / "schema.sql"


def _seed(con, draft_status="complete"):
    con.execute("INSERT INTO users (name) VALUES ('w4-owner')")
    league_id = con.execute(
        "INSERT INTO leagues (name, invite_code, commissioner_id,"
        " season, settings, status) VALUES ('w4-league', 'CODEW4', 1,"
        " '2027', '{}', 'in_season')").lastrowid
    t1 = con.execute(
        "INSERT INTO teams (league_id, owner_id, name, faab_remaining)"
        " VALUES (?, 1, 'Alpha XI', 100)", (league_id,)).lastrowid
    t2 = con.execute(
        "INSERT INTO teams (league_id, owner_id, name, faab_remaining)"
        " VALUES (?, 1, 'Beta XI', 100)", (league_id,)).lastrowid
    players = {}
    for rank in (1, 2, 3, 4):
        pid = con.execute(
            "INSERT INTO players (name, season) VALUES (?, '2027')",
            (f"Player{rank}",)).lastrowid
        players[rank] = pid
        for tid in (t1, t2):
            con.execute(
                "INSERT INTO pre_draft_ranks (team_id, player_id, rank)"
                " VALUES (?, ?, ?)", (tid, pid, rank))
    draft_id = None
    if draft_status is not None:
        draft_id = con.execute(
            "INSERT INTO drafts (league_id, draft_order, rounds, status,"
            " current_pick_no) VALUES (?, ?, 2, ?, 4)",
            (league_id, f"[{t1},{t2}]", draft_status)).lastrowid
        picks = [  # (pick_no, team, consensus rank of player taken)
            (1, t1, 2), (2, t2, 1), (3, t2, 3), (4, t1, 4)]
        for pick_no, tid, rank in picks:
            con.execute(
                "INSERT INTO draft_picks (draft_id, pick_no, round_no,"
                " team_id, player_id) VALUES (?, ?, ?, ?, ?)",
                (draft_id, pick_no, 1 if pick_no <= 2 else 2, tid,
                 players[rank]))
    con.commit()
    return league_id, t1, t2, players


@pytest.fixture()
def make_client(tmp_path):
    def _make(draft_status="complete"):
        db_path = tmp_path / f"recap-{draft_status}.db"
        con = sqlite3.connect(str(db_path))
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")
        con.executescript(SCHEMA.read_text())
        ids = _seed(con, draft_status)
        con.close()
        app = FastAPI()
        app.include_router(leagues.router, prefix="/api/leagues")

        def override():
            c = sqlite3.connect(str(db_path))
            c.row_factory = sqlite3.Row
            c.execute("PRAGMA foreign_keys = ON")
            try:
                yield c
            finally:
                c.close()

        app.dependency_overrides[get_db] = override
        return TestClient(app), ids
    return _make


def test_recap_grades_hand_derived(make_client):
    tc, (league_id, t1, t2, _players) = make_client()
    r = tc.get(f"/api/leagues/{league_id}/draft-recap")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "complete"
    teams = {t["team_name"]: t for t in body["teams"]}
    assert teams["Beta XI"]["grade"] == "A"
    assert teams["Beta XI"]["value_ratio"] == 1.2
    assert teams["Beta XI"]["projected_value"] == 6
    assert teams["Beta XI"]["expected_value"] == 5
    assert teams["Alpha XI"]["grade"] == "F"
    assert teams["Alpha XI"]["value_ratio"] == 0.8
    # Sorted best-first.
    assert body["teams"][0]["team_name"] == "Beta XI"
    # Steal / reach.
    steal = teams["Beta XI"]["biggest_steal"]
    assert steal["player_name"] == "Player1" and steal["delta"] == 1
    assert teams["Beta XI"]["biggest_reach"] is None
    reach = teams["Alpha XI"]["biggest_reach"]
    assert reach["player_name"] == "Player2" and reach["delta"] == -1
    assert teams["Alpha XI"]["biggest_steal"] is None
    # Headlines.
    assert body["headline_biggest_steal"]["player_name"] == "Player1"
    assert body["headline_biggest_steal"]["team_name"] == "Beta XI"
    assert body["headline_best_pick"]["player_name"] == "Player1"
    assert body["headline_best_pick"]["pick_no"] == 2


def test_recap_reproducible(make_client):
    tc, (league_id, *_rest) = make_client()
    a = tc.get(f"/api/leagues/{league_id}/draft-recap").json()
    b = tc.get(f"/api/leagues/{league_id}/draft-recap").json()
    assert a == b


def test_recap_no_draft_yet(make_client):
    tc, (league_id, *_rest) = make_client(draft_status=None)
    body = tc.get(f"/api/leagues/{league_id}/draft-recap").json()
    assert body["status"] == "no_draft" and body["teams"] == []


def test_recap_live_draft_not_graded(make_client):
    tc, (league_id, *_rest) = make_client(draft_status="live")
    body = tc.get(f"/api/leagues/{league_id}/draft-recap").json()
    assert body["status"] == "live" and body["teams"] == []


def test_recap_unknown_league_404(make_client):
    tc, _ids = make_client()
    assert tc.get("/api/leagues/9999/draft-recap").status_code == 404
