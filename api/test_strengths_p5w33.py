"""P5-W33: league strengths heatmap — hand-derived fixture.

Consensus ranks are seeded as team A's pre_draft_ranks (MIN is the
consensus). 23 ranked players -> value = 24 - rank.

Team A (construction roster, top-11 fallback; ranks 1-11 + a
rank-24/value-0 AR who must be dropped by the top-11 cut):
  WK 1,10 -> 23+14 = 37 | BAT 2,3,7 -> 22+21+17 = 60
  AR 4,8  -> 20+16 = 36 | BOWL 5,6,9,11 -> 19+18+15+13 = 65
  total 198
Team B (week-1 saved starters seam; ranks 12-22):
  WK 12,21 -> 12+3 = 15 | BAT 13,16,19 -> 11+8+5 = 24
  AR 14,17,22 -> 10+7+2 = 19 | BOWL 15,18,20 -> 9+6+4 = 19
  total 77
Averages: WK 26.0, BAT 42.0, AR 27.5, BOWL 42.0.
Shades (pinned: >=1.5 -> 2, >=1.15 -> 1, <=0.5 -> -2, <=0.85 -> -1):
  A: WK 1.42->1, BAT 1.43->1, AR 1.31->1, BOWL 1.55->2
  B: WK 0.58->-1, BAT 0.57->-1, AR 0.69->-1, BOWL 0.45->-2
Totals must equal the power-rankings roster_value for the same DB.
"""

import sqlite3
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.database import get_db
from api.routers import power_rankings, strengths

SCHEMA = Path(__file__).resolve().parent / "schema.sql"
A_PLAYERS = [  # (rank, role)
    (1, "WK"), (2, "BAT"), (3, "BAT"), (4, "AR"), (5, "BOWL"),
    (6, "BOWL"), (7, "BAT"), (8, "AR"), (9, "BOWL"), (10, "WK"),
    (11, "BOWL"), (24, "AR"),
]
B_PLAYERS = [
    (12, "WK"), (13, "BAT"), (14, "AR"), (15, "BOWL"), (16, "BAT"),
    (17, "AR"), (18, "BOWL"), (19, "BAT"), (20, "BOWL"), (21, "WK"),
    (22, "AR"),
]
B_SLOTS = ["WK", "BAT", "AR", "BOWL", "BAT", "AR", "BOWL", "UTIL",
           "UTIL", "WK", "BOWL"]


def _seed(con):
    con.execute("INSERT INTO users (name) VALUES ('w33-owner')")
    league = con.execute(
        "INSERT INTO leagues (name, invite_code, commissioner_id,"
        " season, settings, status) VALUES ('w33-league', 'CODE-w33',"
        " 1, '2027', '{}', 'in_season')").lastrowid
    a = con.execute(
        "INSERT INTO teams (league_id, name, owner_id) VALUES (?, 'A', 1)",
        (league,)).lastrowid
    b = con.execute(
        "INSERT INTO teams (league_id, name, owner_id) VALUES (?, 'B', 1)",
        (league,)).lastrowid
    for rank, role in A_PLAYERS + B_PLAYERS:
        pid = con.execute(
            "INSERT INTO players (name, season) VALUES (?, '2027')",
            (f"P{rank:02d}",)).lastrowid
        con.execute(
            "INSERT INTO player_roles (player_id, season, role,"
            " is_overseas, ipl_team_code) VALUES (?, '2027', ?, 0, 'MI')",
            (pid, role))
        con.execute(
            "INSERT INTO pre_draft_ranks (team_id, player_id, rank)"
            " VALUES (?, ?, ?)", (a, pid, rank))
        owner = a if (rank, role) in A_PLAYERS else b
        if owner == a:
            con.execute(
                "INSERT INTO roster_slots (team_id, player_id, slot,"
                " week_no) VALUES (?, ?, ?, NULL)", (a, pid, role))
        else:
            slot = B_SLOTS[B_PLAYERS.index((rank, role))]
            con.execute(
                "INSERT INTO roster_slots (team_id, player_id, slot,"
                " week_no) VALUES (?, ?, ?, 1)", (b, pid, slot))
    # Empty pre-draft league.
    league2 = con.execute(
        "INSERT INTO leagues (name, invite_code, commissioner_id,"
        " season, settings, status) VALUES ('w33-empty', 'CODE-w33e',"
        " 1, '2027', '{}', 'setup')").lastrowid
    for nm in ("C", "D"):
        con.execute(
            "INSERT INTO teams (league_id, name, owner_id)"
            " VALUES (?, ?, 1)", (league2, nm))
    con.commit()
    return {"league": league, "empty": league2}


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / "strengths.db"
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA.read_text())
    ids = _seed(con)
    con.close()
    app = FastAPI()
    app.include_router(strengths.router, prefix="/api/leagues")
    app.include_router(power_rankings.router, prefix="/api/leagues")

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


def test_cells_shades_and_totals(client):
    tc, ids = client
    r = tc.get(f"/api/leagues/{ids['league']}/strengths")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["drafted"] is True
    assert body["averages"] == {"WK": 26.0, "BAT": 42.0, "AR": 27.5,
                                "BOWL": 42.0}
    assert [row["team_name"] for row in body["rows"]] == ["A", "B"]
    a, b = body["rows"]
    assert [(c["role"], c["value"], c["shade"]) for c in a["cells"]] == [
        ("WK", 37, 1), ("BAT", 60, 1), ("AR", 36, 1), ("BOWL", 65, 2)]
    assert a["total"] == 198
    assert [(c["role"], c["value"], c["shade"]) for c in b["cells"]] == [
        ("WK", 15, -1), ("BAT", 24, -1), ("AR", 19, -1), ("BOWL", 19, -2)]
    assert b["total"] == 77
    # Total column == power-rankings roster_value for the same DB state.
    pr = tc.get(f"/api/leagues/{ids['league']}/power-rankings").json()
    assert pr["basis"] == "roster_value"
    by_team = {e["team_name"]: e["roster_value"] for e in pr["entries"]}
    assert by_team == {"A": 198, "B": 77}


def test_predraft_empty_state(client):
    tc, ids = client
    r = tc.get(f"/api/leagues/{ids['empty']}/strengths")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["drafted"] is False
    assert body["averages"] == {"WK": 0.0, "BAT": 0.0, "AR": 0.0,
                                "BOWL": 0.0}
    assert all(row["total"] == 0 for row in body["rows"])
    assert all(c["shade"] == 0 for row in body["rows"] for c in row["cells"])
    assert tc.get("/api/leagues/99999/strengths").status_code == 404
