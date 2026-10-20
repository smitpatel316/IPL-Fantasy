"""P5-W30: commissioner draft-order editor — hand-derived.

Two teams A(1st joined), B. PATCH draft_order=[B, A] must validate as
an exact permutation, persist in settings, and start_draft must deal
round 1 in exactly that order (drafts.draft_order == [B, A]).
Invalid permutations 422; post-start edits 422; a league with no set
order still drafts (seeded shuffle = some permutation of the teams).
"""

import json
import sqlite3
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import services
from api.database import get_db
from api.routers import leagues

SCHEMA = Path(__file__).resolve().parent / "schema.sql"


def _seed(con):
    con.execute("INSERT INTO users (name) VALUES ('w30-owner')")
    league = con.execute(
        "INSERT INTO leagues (name, invite_code, commissioner_id,"
        " season, settings, status) VALUES ('w30', 'CODE-w30', 1,"
        " '2027', '{}', 'setup')").lastrowid
    teams = []
    for name in ("A", "B"):
        teams.append(con.execute(
            "INSERT INTO teams (league_id, name, owner_id) VALUES"
            " (?, ?, 1)", (league, name)).lastrowid)
    roles = ["WK", "BAT", "BAT", "BAT", "AR", "AR", "BOWL", "BOWL",
             "BOWL", "BAT", "AR", "BOWL", "WK", "BAT"]
    for i in range(30):
        pid = con.execute(
            "INSERT INTO players (name, season) VALUES (?, '2027')",
            (f"P{i + 1}",)).lastrowid
        con.execute(
            "INSERT INTO player_roles (player_id, season, role,"
            " is_overseas, ipl_team_code) VALUES (?, '2027', ?, 0, 'MI')",
            (pid, roles[i % len(roles)]))
        for tid in teams:
            con.execute(
                "INSERT INTO pre_draft_ranks (team_id, player_id, rank)"
                " VALUES (?, ?, ?)", (tid, pid, i + 1))
    con.commit()
    return league, teams


@pytest.fixture()
def env(tmp_path):
    db_path = tmp_path / "order.db"
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA.read_text())
    league, teams = _seed(con)
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
    return TestClient(app), db_path, league, teams


def _con(db_path):
    c = sqlite3.connect(str(db_path))
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    return c


def test_set_order_is_used_by_start_draft(env):
    tc, db_path, league, teams = env
    a, b = teams
    # P5-W52: the endpoint is now commissioner-gated; a is the
    # commissioner's team (first team owned by the commissioner user).
    r = tc.patch(f"/api/leagues/{league}/settings",
                 json={"commissioner_team_id": a, "draft_order": [b, a]})
    assert r.status_code == 200, r.text
    assert r.json()["settings"]["draft_order"] == [b, a]
    con = _con(db_path)
    draft = services.start_draft(con, league)
    assert draft["draft_order"] == [b, a]
    con.close()


def test_invalid_permutations_rejected(env):
    tc, db_path, league, teams = env
    a, b = teams
    for bad in ([a, a], [a], [a, b, 999], [999, 998]):
        r = tc.patch(f"/api/leagues/{league}/settings",
                     json={"commissioner_team_id": a, "draft_order": bad})
        assert r.status_code == 422, (bad, r.text)


def test_post_start_edit_rejected_and_shuffle_default(env):
    tc, db_path, league, teams = env
    con = _con(db_path)
    draft = services.start_draft(con, league)  # no set order: shuffle
    assert sorted(draft["draft_order"]) == sorted(teams)
    con.close()
    r = tc.patch(f"/api/leagues/{league}/settings",
                 json={"commissioner_team_id": teams[0],
                       "draft_order": teams})
    assert r.status_code == 422
    assert "locks" in r.json()["detail"]
