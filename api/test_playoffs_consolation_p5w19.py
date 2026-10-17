"""P5-W19: consolation bracket — hand-derived fixture.

6 teams T1..T6 (ids in creation order). Weeks 1-6 finals are seeded so
records sort strictly: T1 beats everyone etc. Simpler deterministic
standings: give each team a distinct points-for via week-1..6 rows?
Instead: one final per team pair is unnecessary — records derive from
all final rows weeks<=6. We fabricate week 6 only? _regular_season_
complete requires week-6 rows all final; records from week 6 alone:
pair T1>T2, T3>T4, T5>T6 gives wins 1 for T1/T3/T5 — ordering then by
PF. Set scores: T1 100, T3 90, T5 80 winners; losers T2 70, T4 60, T6 50
=> order by (-wins,-PF): T1(1,100) T3(1,90) T5(1,80) T2(0,70) T4(0,60)
T6(0,50). Seeds 1-4 = T1,T3,T5,T2; consolation = seeds 5/6 = T4 vs T6.
Week-7 consolation row T4 55, T6 55 final -> tie goes to better seed
(T4, seed 5) -> fifth=T4, sixth=T6.
"""
import sqlite3
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.database import get_db
from api.routers import playoffs

SCHEMA = Path(__file__).resolve().parent / "schema.sql"


def _seed(con, nteams=6):
    con.execute("INSERT INTO users (name) VALUES ('w19-owner')")
    league = con.execute(
        "INSERT INTO leagues (name, invite_code, commissioner_id, season, settings, status)"
        " VALUES ('w19-league','CODE-w19',1,'2027','{}','in_season')").lastrowid
    teams = []
    for i in range(1, nteams + 1):
        teams.append(con.execute(
            "INSERT INTO teams (league_id, owner_id, name, faab_remaining) VALUES (?,1,?,100)",
            (league, f"T{i}")).lastrowid)
    con.commit()
    return league, teams


def _matchup(con, league, week, a, b, sa, sb, status="final"):
    con.execute(
        "INSERT INTO matchups (league_id, week_no, team_a_id, team_b_id, score_a, score_b, status)"
        " VALUES (?,?,?,?,?,?,?)", (league, week, a, b, sa, sb, status))
    con.commit()


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / "w19.db"
    con = sqlite3.connect(str(db_path)); con.row_factory = sqlite3.Row
    con.executescript(SCHEMA.read_text())
    league, teams = _seed(con)
    # week 6 finals establishing standings described above
    _matchup(con, league, 6, teams[0], teams[1], 100, 70)
    _matchup(con, league, 6, teams[2], teams[3], 90, 60)
    _matchup(con, league, 6, teams[4], teams[5], 80, 50)
    con.close()
    app = FastAPI(); app.include_router(playoffs.router, prefix="/api/leagues")
    def override():
        c = sqlite3.connect(str(db_path)); c.row_factory = sqlite3.Row
        try: yield c
        finally: c.close()
    app.dependency_overrides[get_db] = override
    return TestClient(app), league, teams, db_path


def test_consolation_projected_pairing(client):
    tc, league, teams, _ = client
    body = tc.get(f"/api/leagues/{league}/playoffs").json()
    cons = body["consolation"]
    assert cons is not None and cons["label"] == "Consolation game" and cons["week_no"] == 7
    assert {cons["team_a_id"], cons["team_b_id"]} == {teams[3], teams[5]}  # T4 vs T6
    assert cons["status"] in ("scheduled", "projected")
    assert body["fifth_place_team_id"] is None


def test_consolation_tie_goes_to_better_seed(client):
    tc, league, teams, db_path = client
    con = sqlite3.connect(str(db_path))
    _matchup(con, league, 7, teams[3], teams[5], 55, 55)
    con.close()
    body = tc.get(f"/api/leagues/{league}/playoffs").json()
    cons = body["consolation"]
    assert cons["status"] == "final" and cons["winner_team_id"] == teams[3]
    assert body["fifth_place_team_id"] == teams[3]
    assert body["sixth_place_team_id"] == teams[5]


def test_consolation_winner_by_score(client):
    tc, league, teams, db_path = client
    con = sqlite3.connect(str(db_path))
    _matchup(con, league, 7, teams[5], teams[3], 77, 40)  # T6 beats T4, row flipped
    con.close()
    body = tc.get(f"/api/leagues/{league}/playoffs").json()
    assert body["consolation"]["winner_team_id"] == teams[5]
    assert body["fifth_place_team_id"] == teams[5]
    assert body["sixth_place_team_id"] == teams[3]


def test_no_consolation_under_six_teams(tmp_path):
    db_path = tmp_path / "w19small.db"
    con = sqlite3.connect(str(db_path)); con.row_factory = sqlite3.Row
    con.executescript(SCHEMA.read_text())
    league, teams = _seed(con, nteams=4)
    _matchup(con, league, 6, teams[0], teams[1], 10, 5)
    _matchup(con, league, 6, teams[2], teams[3], 9, 4)
    con.close()
    app = FastAPI(); app.include_router(playoffs.router, prefix="/api/leagues")
    def override():
        c = sqlite3.connect(str(db_path)); c.row_factory = sqlite3.Row
        try: yield c
        finally: c.close()
    app.dependency_overrides[get_db] = override
    tc = TestClient(app)
    body = tc.get(f"/api/leagues/{league}/playoffs").json()
    assert body["consolation"] is None and body["fifth_place_team_id"] is None
