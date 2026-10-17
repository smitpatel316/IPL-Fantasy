"""P5-W34: playoff clinch / elimination — hand-derived fixtures.

Bounds (standings points = 2W+T; final in [pts, pts + 2*remaining]):
  * clinched — at most 3 rivals can pass the team's current points
    (max > min, or max == min in a LIVE tie: while either side has
    games left a tied rival can still pass on tiebreakers, so tied
    bounds never clinch). Exception: a tie between two teams with
    no games left is settled by the projection's seed order.
  * eliminated — at least 4 rivals are guaranteed ahead of the
    team's best case (min > max, or a finished-tie settled by seeds).
  * magic number (in-contention only) = 4th-highest rival max + 1 -
    current points; null when winning out cannot supply it.

Fixture: round-robin rounds 1-4 final, rounds 5-6 scheduled.
Finals (winner scores: A 100, B 90, anyone else 80; loser 50):
  R1: A>F, B>E, C>D   R2: A>E, D>F, B>C
  R3: A>D, C>E, B>F   R4: A>C, B>D, E>F
Records: A 4-0 pts8 PF400; B 4-0 pts8 PF360; C 2-2 pts4 PF260;
         D 1-3 pts2 PF230; E 1-3 pts2 PF230; F 0-4 pts0 PF200.
Seeds: 1 A (PF over B), 2 B, 3 C, 4 D (name over E at equal PF),
       5 E, 6 F. GB from 4th (D, 1-3): A -3, B -3, C -1, D 0, E 0, F 1.
Scheduled: W5 A-B, C-D; W6 A-E, B-D.
Remaining: A2 B2 C1 D2 E1 F0. Max: A12 B12 C6 D6 E4 F0.
Statuses:
  A: rivals max > 8 or live-tie >= 8 -> B(12) only = 1 -> clinched.
  B: -> A(12) only = 1 -> clinched.
  C: rivals that can pass 4 -> A(12), B(12), D(6), E(4, LIVE TIE ==
     C's min) = 4 -> NOT clinched (the tied-bound pin: counting only
     strict > would give 3 and falsely clinch). Rivals guaranteed
     ahead of C's max 6 -> A(8), B(8) = 2 -> in_contention.
     magic = 4th-highest rival max (4) + 1 - 4 = 1.
  D: can pass 2 -> A, B, C(6), E(4) = 4 -> not clinched; guaranteed
     ahead of max 6 -> A, B = 2 -> in_contention.
     magic = 4th-highest rival max (4) + 1 - 2 = 3 (<= 2*rem = 4).
  E: can pass 2 -> A, B, C, D = 4 -> not clinched; guaranteed ahead
     of max 4 -> A, B = 2 (C's min 4 is a live tie, not locked) ->
     in_contention. magic = 4th-highest rival max (6) + 1 - 2 = 5
     > 2*rem (2) -> None.
  F: guaranteed ahead of max 0 -> every rival's min > 0 = 5 ->
     eliminated.

Completed season (all scheduled rows final, team_a wins 10-5):
  A 6-0 pts12, B 5-1 pts10, C 3-2 pts6, E 1-4 pts2, D 1-5 pts2,
  F 0-4 pts0. Seeds: A, B, C, E (fewer losses than D), D, F.
  With no games left, the E/D points tie is settled by seeds:
  A/B/C/E clinched, D/F eliminated.
"""
import sqlite3
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.database import get_db
from api.routers import playoff_picture

SCHEMA = Path(__file__).resolve().parent / "schema.sql"
WINNER_SCORE = {"A": 100, "B": 90}
FINALS = [  # (week, winner, loser)
    (1, "A", "F"), (1, "B", "E"), (1, "C", "D"),
    (2, "A", "E"), (2, "D", "F"), (2, "B", "C"),
    (3, "A", "D"), (3, "C", "E"), (3, "B", "F"),
    (4, "A", "C"), (4, "B", "D"), (4, "E", "F"),
]
SCHEDULED = [(5, "A", "B"), (5, "C", "D"), (6, "A", "E"), (6, "B", "D")]


def _seed(con):
    con.execute("INSERT INTO users (name) VALUES ('w34-owner')")
    league = con.execute(
        "INSERT INTO leagues (name, invite_code, commissioner_id, season, settings, status)"
        " VALUES ('w34-league','CODE-w34',1,'2027','{}','in_season')").lastrowid
    teams = {}
    for label in "ABCDEF":
        teams[label] = con.execute(
            "INSERT INTO teams (league_id, owner_id, name, faab_remaining)"
            " VALUES (?,1,?,100)", (league, label)).lastrowid
    for week, w, loser in FINALS:
        con.execute(
            "INSERT INTO matchups (league_id, week_no, team_a_id, team_b_id, score_a, score_b, status)"
            " VALUES (?,?,?,?,?,50,'final')",
            (league, week, teams[w], teams[loser], WINNER_SCORE.get(w, 80)))
    for week, a, b in SCHEDULED:
        con.execute(
            "INSERT INTO matchups (league_id, week_no, team_a_id, team_b_id, score_a, score_b, status)"
            " VALUES (?,?,?,?,0,0,'scheduled')", (league, week, teams[a], teams[b]))
    con.commit()
    return league


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / "w34.db"
    con = sqlite3.connect(str(db_path)); con.row_factory = sqlite3.Row
    con.executescript(SCHEMA.read_text())
    league = _seed(con)
    con.close()
    app = FastAPI(); app.include_router(playoff_picture.router, prefix="/api/leagues")
    def override():
        c = sqlite3.connect(str(db_path)); c.row_factory = sqlite3.Row
        try: yield c
        finally: c.close()
    app.dependency_overrides[get_db] = override
    return TestClient(app), league, db_path


def _get(tc, league):
    r = tc.get(f"/api/leagues/{league}/playoff-picture")
    assert r.status_code == 200, r.text
    return r.json()


def test_clinch_statuses_and_magic_numbers(client):
    tc, league, _ = client
    body = _get(tc, league)
    by = {e["team_name"]: e for e in body["entries"]}
    order = [e["team_name"] for e in sorted(body["entries"], key=lambda e: e["seed"])]
    assert order == ["A", "B", "C", "D", "E", "F"]
    # Existing P5-W22 fields unchanged for the same DB state.
    assert by["A"]["games_back"] == -3.0 and by["C"]["games_back"] == -1.0
    assert by["D"]["games_back"] == 0.0 and by["E"]["games_back"] == 0.0
    assert by["F"]["games_back"] == 1.0
    assert [by[n]["remaining_games"] for n in "ABCDEF"] == [2, 2, 1, 2, 1, 0]
    # Clinch statuses (see module docstring for the full derivation).
    assert by["A"]["clinch_status"] == "clinched"
    assert by["B"]["clinch_status"] == "clinched"
    assert by["C"]["clinch_status"] == "in_contention"  # live tied bound (E max == C min)
    assert by["D"]["clinch_status"] == "in_contention"
    assert by["E"]["clinch_status"] == "in_contention"
    assert by["F"]["clinch_status"] == "eliminated"
    # Magic numbers.
    assert by["A"]["magic_number"] is None
    assert by["B"]["magic_number"] is None
    assert by["C"]["magic_number"] == 1
    assert by["D"]["magic_number"] == 3
    assert by["E"]["magic_number"] is None  # needs 5, can gain at most 2
    assert by["F"]["magic_number"] is None


def test_completed_season_final_picture(client):
    tc, league, db_path = client
    con = sqlite3.connect(str(db_path))
    con.execute("UPDATE matchups SET status='final', score_a=10, score_b=5"
                " WHERE league_id = ? AND status != 'final'", (league,))
    con.commit(); con.close()
    body = _get(tc, league)
    assert body["regular_season_complete"] is True
    by = {e["team_name"]: e for e in body["entries"]}
    order = [e["team_name"] for e in sorted(body["entries"], key=lambda e: e["seed"])]
    assert order == ["A", "B", "C", "E", "D", "F"]
    for name in "ABCE":
        assert by[name]["clinch_status"] == "clinched", name
        assert by[name]["magic_number"] is None, name
    for name in "DF":
        assert by[name]["clinch_status"] == "eliminated", name
        assert by[name]["magic_number"] is None, name
