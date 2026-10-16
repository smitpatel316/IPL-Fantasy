"""P5-W9: power rankings — deterministic, hand-derived fixture.

22 players carry consensus ranks 1..22 (pool N=22, value = 23-rank).
Team A rosters ranks 1..11  -> starter values 22..12, sum 187.
Team B rosters ranks 12..22 -> starter values 11..1,  sum 66.
(no saved week-1 lineups, so starters = top 11 of the roster)

Pre-season: A #1 (187), B #2 (66), basis roster_value, no movement.
Week 1 final (B 100, A 50): standings pts B=2, A=0; PF shares
100/150=.6667 and 50/150=.3333 -> scores B 2.6667, A 0.3333: B #1.
Movement still None (only one final week).
Week 2 final (A 200, B 0): both 1-1; PF A=250, B=100, total 350 ->
A 2+.7143=2.7143, B 2+.2857=2.2857: A #1 again; movement vs week 1:
A +1, B -1.
"""

import sqlite3
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.database import get_db
from api.routers import power_rankings

SCHEMA = Path(__file__).resolve().parent / "schema.sql"


def _seed(con):
    con.execute("INSERT INTO users (name) VALUES ('w9-owner')")
    ids = {}
    league = con.execute(
        "INSERT INTO leagues (name, invite_code, commissioner_id,"
        " season, settings, status) VALUES ('w9-league', 'CODE-w9', 1,"
        " '2027', '{}', 'in_season')").lastrowid
    ids["league"] = league
    for label in ("A", "B"):
        ids[f"team{label}"] = con.execute(
            "INSERT INTO teams (league_id, owner_id, name,"
            " faab_remaining) VALUES (?, 1, ?, 100)",
            (league, f"w9-{label}")).lastrowid
    for rank in range(1, 23):
        pid = con.execute(
            "INSERT INTO players (name, season) VALUES (?, '2027')",
            (f"P{rank}",)).lastrowid
        team = ids["teamA"] if rank <= 11 else ids["teamB"]
        con.execute(
            "INSERT INTO roster_slots (team_id, player_id, slot)"
            " VALUES (?, ?, 'BN')", (team, pid))
        # Consensus: both teams rank identically -> MIN(rank) = rank.
        for t in (ids["teamA"], ids["teamB"]):
            con.execute(
                "INSERT INTO pre_draft_ranks (team_id, player_id, rank)"
                " VALUES (?, ?, ?)", (t, pid, rank))
    con.commit()
    return ids


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / "power.db"
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA.read_text())
    ids = _seed(con)
    con.close()

    app = FastAPI()
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
    return TestClient(app), ids, db_path


def _final(db_path, ids, week, score_a, score_b):
    con = sqlite3.connect(str(db_path))
    con.execute(
        "INSERT INTO matchups (league_id, week_no, team_a_id, team_b_id,"
        " score_a, score_b, status) VALUES (?, ?, ?, ?, ?, ?, 'final')",
        (ids["league"], week, ids["teamA"], ids["teamB"], score_a, score_b))
    con.commit()
    con.close()


def _get(tc, ids):
    r = tc.get(f"/api/leagues/{ids['league']}/power-rankings")
    assert r.status_code == 200, r.text
    return r.json()


def test_preseason_roster_value_ranking(client):
    tc, ids, _ = client
    body = _get(tc, ids)
    assert body["basis"] == "roster_value" and body["through_week"] == 0
    a, b = body["entries"]
    assert (a["team_id"], a["rank"], a["roster_value"]) == (ids["teamA"], 1, 187)
    assert (b["team_id"], b["rank"], b["roster_value"]) == (ids["teamB"], 2, 66)
    assert a["movement"] is None and a["points_for"] == 0.0
    # Reproducible: same DB state -> byte-identical ranking.
    assert _get(tc, ids) == body


def test_first_final_week_blends_record_and_pf(client):
    tc, ids, db_path = client
    _final(db_path, ids, 1, 50, 100)  # team_a=A 50, team_b=B 100
    body = _get(tc, ids)
    assert body["basis"] == "record_blend" and body["through_week"] == 1
    b, a = body["entries"]
    assert b["team_id"] == ids["teamB"] and b["power_score"] == 2.6667
    assert a["team_id"] == ids["teamA"] and a["power_score"] == 0.3333
    assert (b["wins"], b["points_for"]) == (1, 100.0)
    assert a["movement"] is None  # only one final week so far


def test_second_week_adds_movement(client):
    tc, ids, db_path = client
    _final(db_path, ids, 1, 50, 100)
    _final(db_path, ids, 2, 200, 0)  # A 200, B 0
    body = _get(tc, ids)
    assert body["through_week"] == 2
    a, b = body["entries"]
    assert a["team_id"] == ids["teamA"] and a["power_score"] == 2.7143
    assert b["team_id"] == ids["teamB"] and b["power_score"] == 2.2857
    assert a["movement"] == 1 and b["movement"] == -1


def test_unknown_league_404(client):
    tc, _, _ = client
    assert tc.get("/api/leagues/99999/power-rankings").status_code == 404
