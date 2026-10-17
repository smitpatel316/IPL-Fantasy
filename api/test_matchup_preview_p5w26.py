"""P5-W26: matchup preview — hand-derived fixture.

Pool = 3 ranked players, value = pool + 1 - rank:
  P1 rank 1 (MI) -> 3, P2 rank 2 (CSK, injured) -> 2, P3 rank 3 (MI) -> 1.
Team A week-2 starters P1+P2: rank value 5, games = MI 2 + CSK 1 = 3,
flagged = [P2]. Team B starter P3: value 1, games = MI 2 = 2.
Prior H2H: week-1 final A 100 - B 90 (winner A). A second week-2
matchup is final -> excluded; a third has no lineups -> honest
lineup_set=false with null totals.
"""

import sqlite3
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.database import get_db
from api.routers import matchup_preview

SCHEMA = Path(__file__).resolve().parent / "schema.sql"


def _seed(con):
    con.execute("INSERT INTO users (name) VALUES ('w26-owner')")
    league = con.execute(
        "INSERT INTO leagues (name, invite_code, commissioner_id,"
        " season, settings, status) VALUES ('w26', 'CODE-w26', 1,"
        " '2027', '{}', 'in_season')").lastrowid
    teams = {}
    for name in ("A", "B", "C", "D"):
        teams[name] = con.execute(
            "INSERT INTO teams (league_id, name, owner_id) VALUES"
            " (?, ?, 1)", (league, name)).lastrowid
    players = {}
    for name, role, code, status, rank in [
            ("P1", "BAT", "MI", None, 1), ("P2", "BAT", "CSK", "injured", 2),
            ("P3", "BOWL", "MI", None, 3)]:
        pid = con.execute(
            "INSERT INTO players (name, season) VALUES (?, '2027')",
            (name,)).lastrowid
        con.execute(
            "INSERT INTO player_roles (player_id, season, role,"
            " is_overseas, ipl_team_code, status) VALUES"
            " (?, '2027', ?, 0, ?, ?)", (pid, role, code, status))
        con.execute(
            "INSERT INTO pre_draft_ranks (team_id, player_id, rank)"
            " VALUES (?, ?, ?)", (teams["A"], pid, rank))
        players[name] = pid
    # construction rosters + week-2 saved lineups for A and B
    for tname, pnames in [("A", ["P1", "P2"]), ("B", ["P3"])]:
        for pname in pnames:
            con.execute(
                "INSERT INTO roster_slots (team_id, player_id, slot)"
                " VALUES (?, ?, 'BN')", (teams[tname], players[pname]))
            con.execute(
                "INSERT INTO roster_slots (team_id, player_id, slot,"
                " week_no) VALUES (?, ?, 'BAT', 2)",
                (teams[tname], players[pname]))
    for wk, code, games in [(2, "MI", 2), (2, "CSK", 1)]:
        con.execute(
            "INSERT INTO team_weekly_games (season, week_no, week_start,"
            " week_end, ipl_team_code, games, source) VALUES ('2027', ?,"
            " '2027-03-08', '2027-03-14', ?, ?, 'standin-2026')",
            (wk, code, games))
    con.execute(
        "INSERT INTO matchups (league_id, week_no, team_a_id, team_b_id,"
        " score_a, score_b, status) VALUES (?, 1, ?, ?, 100, 90, 'final')",
        (league, teams["A"], teams["B"]))
    con.execute(
        "INSERT INTO matchups (league_id, week_no, team_a_id, team_b_id,"
        " status) VALUES (?, 2, ?, ?, 'scheduled')",
        (league, teams["A"], teams["B"]))
    con.execute(
        "INSERT INTO matchups (league_id, week_no, team_a_id, team_b_id,"
        " status) VALUES (?, 2, ?, ?, 'scheduled')",
        (league, teams["C"], teams["D"]))
    con.commit()
    return {"league": league, "teams": teams}


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / "preview.db"
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA.read_text())
    ids = _seed(con)
    con.close()
    app = FastAPI()
    app.include_router(matchup_preview.router, prefix="/api/leagues")

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


def test_preview_hand_derived(client):
    tc, ids = client
    r = tc.get(f"/api/leagues/{ids['league']}/matchups/preview",
               params={"week_no": 2})
    assert r.status_code == 200, r.text
    body = r.json()
    assert "probability" in body["basis"]  # the no-probability label
    assert len(body["previews"]) == 2
    ab = body["previews"][0]
    assert ab["side_a"]["starters_rank_value"] == 5
    assert ab["side_a"]["games_this_week"] == 3
    assert ab["side_a"]["flagged_starters"] == ["P2"]
    assert ab["side_b"]["starters_rank_value"] == 1
    assert ab["side_b"]["games_this_week"] == 2
    assert ab["prior_h2h"]["week_no"] == 1
    assert ab["prior_h2h"]["winner_team_id"] == ids["teams"]["A"]
    cd = body["previews"][1]
    assert cd["side_a"]["lineup_set"] is False
    assert cd["side_a"]["starters_rank_value"] is None
    assert cd["prior_h2h"] is None


def test_final_week_has_no_previews_and_bounds(client):
    tc, ids = client
    r = tc.get(f"/api/leagues/{ids['league']}/matchups/preview",
               params={"week_no": 1})
    assert r.json()["previews"] == []  # week 1's only matchup is final
    assert tc.get(f"/api/leagues/{ids['league']}/matchups/preview",
                  params={"week_no": 9}).status_code == 422
    assert tc.get("/api/leagues/99999/matchups/preview",
                  params={"week_no": 2}).status_code == 404
