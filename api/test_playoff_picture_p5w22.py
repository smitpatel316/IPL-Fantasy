"""P5-W22: playoff picture — hand-derived fixture (see module math).

6 teams A..F. Finals weeks 1-3:
  W1: A>B 100-50, C>D 90-60, E>F 80-70
  W2: A>C 110-70, B>D 95-65, E=F 75-75
  W3: A>D 120-80, B>C 100-85, F>E 90-85
Records: A 3-0 PF330; B 2-1 PF245; E 1-1-1 PF240; F 1-1-1 PF235;
         C 1-2 PF245; D 0-3 PF205.
Seeds (W, L asc, T desc, PF): 1 A, 2 B, 3 E, 4 F, 5 C, 6 D.
Standings points (2W+T): A6 B4 E3 F3 C2 D0, total 18.
Shares: A .3333 B .2222 C .1111 D 0 E .1667 F .1667.
GB from 4th (F, 1-1): A -1.5, B -0.5, E 0, F 0, C 0.5, D 1.5.
  (E and F have IDENTICAL records — the tied case: both GB 0, E seeds
  above F on points-for.)
Scheduled weeks 4-6: W4 A-D B-E C-F; W5 A-E B-F C-D; W6 A-F B-D C-E.
Remaining SOS (mean opponent share): A/B/C .1111, D/E/F .2222.
"""
import sqlite3
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.database import get_db
from api.routers import playoff_picture

SCHEMA = Path(__file__).resolve().parent / "schema.sql"
FINALS = [
    (1, "A", "B", 100, 50), (1, "C", "D", 90, 60), (1, "E", "F", 80, 70),
    (2, "A", "C", 110, 70), (2, "B", "D", 95, 65), (2, "E", "F", 75, 75),
    (3, "A", "D", 120, 80), (3, "B", "C", 100, 85), (3, "F", "E", 90, 85),
]
SCHEDULED = [
    (4, "A", "D"), (4, "B", "E"), (4, "C", "F"),
    (5, "A", "E"), (5, "B", "F"), (5, "C", "D"),
    (6, "A", "F"), (6, "B", "D"), (6, "C", "E"),
]


def _seed(con):
    con.execute("INSERT INTO users (name) VALUES ('w22-owner')")
    league = con.execute(
        "INSERT INTO leagues (name, invite_code, commissioner_id, season, settings, status)"
        " VALUES ('w22-league','CODE-w22',1,'2027','{}','in_season')").lastrowid
    teams = {}
    for label in "ABCDEF":
        teams[label] = con.execute(
            "INSERT INTO teams (league_id, owner_id, name, faab_remaining)"
            " VALUES (?,1,?,100)", (league, label)).lastrowid
    for week, a, b, sa, sb in FINALS:
        con.execute(
            "INSERT INTO matchups (league_id, week_no, team_a_id, team_b_id, score_a, score_b, status)"
            " VALUES (?,?,?,?,?,?,'final')", (league, week, teams[a], teams[b], sa, sb))
    for week, a, b in SCHEDULED:
        con.execute(
            "INSERT INTO matchups (league_id, week_no, team_a_id, team_b_id, score_a, score_b, status)"
            " VALUES (?,?,?,? ,0,0,'scheduled')", (league, week, teams[a], teams[b]))
    con.commit()
    return league, teams


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / "w22.db"
    con = sqlite3.connect(str(db_path)); con.row_factory = sqlite3.Row
    con.executescript(SCHEMA.read_text())
    league, teams = _seed(con)
    con.close()
    app = FastAPI(); app.include_router(playoff_picture.router, prefix="/api/leagues")
    def override():
        c = sqlite3.connect(str(db_path)); c.row_factory = sqlite3.Row
        try: yield c
        finally: c.close()
    app.dependency_overrides[get_db] = override
    return TestClient(app), league, teams, db_path


def _get(tc, league):
    r = tc.get(f"/api/leagues/{league}/playoff-picture")
    assert r.status_code == 200, r.text
    return r.json()


def test_picture_matches_fixture(client):
    tc, league, teams, _ = client
    body = _get(tc, league)
    assert body["through_week"] == 3 and body["regular_season_complete"] is False
    order = [(e["seed"], e["team_name"]) for e in body["entries"]]
    assert order == [(1, "A"), (2, "B"), (3, "E"), (4, "F"), (5, "C"), (6, "D")]
    by = {e["team_name"]: e for e in body["entries"]}
    assert (by["A"]["wins"], by["A"]["games_back"]) == (3, -1.5)
    assert by["B"]["games_back"] == -0.5
    assert by["E"]["games_back"] == 0 and by["F"]["games_back"] == 0  # tied records
    assert by["C"]["games_back"] == 0.5 and by["D"]["games_back"] == 1.5
    for name in "ABCDEF":
        assert by[name]["remaining_games"] == 3
    assert by["A"]["remaining_sos"] == 0.1111 and by["D"]["remaining_sos"] == 0.2222
    assert by["E"]["remaining_sos"] == 0.2222 and by["C"]["remaining_sos"] == 0.1111
    a_opps = [(o["week_no"], o["opponent_team_name"]) for o in by["A"]["remaining_opponents"]]
    assert a_opps == [(4, "D"), (5, "E"), (6, "F")]


def test_completed_regular_season(client):
    tc, league, teams, db_path = client
    con = sqlite3.connect(str(db_path))
    con.execute("UPDATE matchups SET status='final', score_a=10, score_b=5"
                " WHERE league_id = ?", (league,))
    con.commit(); con.close()
    body = _get(tc, league)
    assert body["regular_season_complete"] is True
    assert all(e["remaining_games"] == 0 and e["remaining_sos"] == 0.0
               for e in body["entries"])


def test_unknown_league_404(client):
    tc, _, _, _ = client
    assert tc.get("/api/leagues/99999/playoff-picture").status_code == 404
