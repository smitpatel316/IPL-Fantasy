"""P5-W14: player compare tool — aggregate read endpoint.

Hand-derived fixture: one league, players X (MI BAT, consensus rank 5,
rostered by team 1, scored 80 + 100 in two matches -> avg 90.0,
ownership 100% of 1 league) and Y (CSK WK, rank 9, free agent, no
stats -> avg None, ownership 0%). team_weekly_games for 2027 weeks
1-3: MI plays 2/1/3 (=6), CSK plays 1/1/1 (=3). No final matchups, so
current_week = 1 and the compare window is weeks [1, 2, 3].
"""

import sqlite3
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.database import get_db
from api.routers import players

SCHEMA = Path(__file__).resolve().parent / "schema.sql"


def _player(con, name, role, code, rank, team_id):
    pid = con.execute(
        "INSERT INTO players (name, season) VALUES (?, '2027')",
        (name,)).lastrowid
    con.execute(
        "INSERT INTO player_roles (player_id, season, role, is_overseas,"
        " ipl_team_code) VALUES (?, '2027', ?, 0, ?)", (pid, role, code))
    con.execute(
        "INSERT INTO pre_draft_ranks (team_id, player_id, rank)"
        " VALUES (?, ?, ?)", (team_id, pid, rank))
    return pid


def _seed(con):
    con.execute("INSERT INTO users (name) VALUES ('w14-owner')")
    league = con.execute(
        "INSERT INTO leagues (name, invite_code, commissioner_id,"
        " season, settings, status) VALUES ('w14-league', 'CODE-w14',"
        " 1, '2027', '{}', 'in_season')").lastrowid
    team = con.execute(
        "INSERT INTO teams (league_id, owner_id, name, faab_remaining)"
        " VALUES (?, 1, 'w14-A', 100)", (league,)).lastrowid
    x = _player(con, "Xavier", "BAT", "MI", 5, team)
    y = _player(con, "Yusuf", "WK", "CSK", 9, team)
    z = _player(con, "Zaid", "BOWL", "MI", 20, team)
    con.execute(
        "INSERT INTO roster_slots (team_id, player_id, slot)"
        " VALUES (?, ?, 'BAT')", (team, x))
    for i, pts in enumerate((80, 100)):
        mid = con.execute(
            "INSERT INTO matches (season, week_no, match_date_ist,"
            " home_code, away_code) VALUES ('2027', 1, '2027-03-10',"
            " 'MI', 'CSK')").lastrowid
        con.execute(
            "INSERT INTO player_match_stats (match_id, player_id,"
            " player_name, fantasy_points, breakdown)"
            " VALUES (?, ?, 'Xavier', ?, '{}')",
            (mid, x, pts))
    for wk, (mi, csk) in enumerate(((2, 1), (1, 1), (3, 1)), start=1):
        for code, games in (("MI", mi), ("CSK", csk)):
            con.execute(
                "INSERT INTO team_weekly_games (season, week_no,"
                " week_start, week_end, ipl_team_code, games, source)"
                " VALUES ('2027', ?, '2027-03-08', '2027-03-14', ?, ?,"
                " 'test')", (wk, code, games))
    con.commit()
    return {"league": league, "team": team, "x": x, "y": y, "z": z}


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / "compare.db"
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA.read_text())
    ids = _seed(con)
    con.close()

    app = FastAPI()
    app.include_router(players.router, prefix="/api/players")

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


def test_compare_matches_detail_values(client):
    tc, ids = client
    r = tc.get("/api/players/compare",
               params={"league_id": ids["league"],
                       "ids": f"{ids['y']},{ids['x']}"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["current_week"] == 1 and body["weeks"] == [1, 2, 3]
    # Order follows the request, not rank.
    assert [p["id"] for p in body["players"]] == [ids["y"], ids["x"]]
    by_id = {p["id"]: p for p in body["players"]}
    x, y = by_id[ids["x"]], by_id[ids["y"]]
    assert x["preseason_rank"] == 5 and x["avg_points"] == 90.0
    assert x["ownership_pct"] == 100.0
    assert x["owned_by_team_id"] == ids["team"]
    assert x["games_next_3_weeks"] == 6
    assert y["preseason_rank"] == 9 and y["avg_points"] is None
    assert y["ownership_pct"] == 0.0 and y["owned_by_team_id"] is None
    assert y["games_next_3_weeks"] == 3
    # Every shared field equals the individual detail endpoint exactly.
    for pid, entry in by_id.items():
        d = tc.get(f"/api/players/{pid}",
                   params={"league_id": ids["league"]}).json()
        for field in ("name", "role", "is_overseas", "ipl_team_code",
                      "preseason_rank", "owned_by_team_id",
                      "availability", "avg_points", "ownership_pct"):
            assert entry[field] == d[field], (pid, field)


def test_compare_three_players(client):
    tc, ids = client
    r = tc.get("/api/players/compare",
               params={"league_id": ids["league"],
                       "ids": f"{ids['x']},{ids['y']},{ids['z']}"})
    assert r.status_code == 200, r.text
    assert len(r.json()["players"]) == 3


def test_compare_validation(client):
    tc, ids = client
    lg = {"league_id": ids["league"]}
    assert tc.get("/api/players/compare",
                  params={**lg, "ids": str(ids["x"])}).status_code == 422
    assert tc.get("/api/players/compare",
                  params={**lg, "ids": f"{ids['x']},{ids['x']}"}
                  ).status_code == 422
    assert tc.get("/api/players/compare",
                  params={**lg, "ids": "1,2,3,4"}).status_code == 422
    assert tc.get("/api/players/compare",
                  params={**lg, "ids": "a,b"}).status_code == 422
    assert tc.get("/api/players/compare",
                  params={**lg, "ids": f"{ids['x']},99999"}
                  ).status_code == 404
    assert tc.get("/api/players/compare",
                  params={"league_id": 99999,
                          "ids": f"{ids['x']},{ids['y']}"}
                  ).status_code == 404
