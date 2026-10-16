"""P5-W15: schedule matrix — cell-for-cell vs schedule-nudges.

Hand-derived fixture: team_weekly_games for season 2027 —
  MI:  wk1=2, wk2=1, wk3=3, wk5=2 (no wk4 row -> bye 0)
  CSK: wk1=1, wk2=1, wk3=1, wk4=1, wk5=1
Totals: MI 8, CSK 5. Every matrix cell must equal the per-week
schedule-nudges payload for the same (team, week).
"""

import sqlite3
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.database import get_db
from api.routers import leagues

SCHEMA = Path(__file__).resolve().parent / "schema.sql"
COUNTS = {
    "MI": {1: 2, 2: 1, 3: 3, 5: 2},
    "CSK": {1: 1, 2: 1, 3: 1, 4: 1, 5: 1},
}


def _seed(con):
    con.execute("INSERT INTO users (name) VALUES ('w15-owner')")
    league = con.execute(
        "INSERT INTO leagues (name, invite_code, commissioner_id,"
        " season, settings, status) VALUES ('w15-league', 'CODE-w15',"
        " 1, '2027', '{}', 'in_season')").lastrowid
    for code, weeks in COUNTS.items():
        for wk, games in weeks.items():
            con.execute(
                "INSERT INTO team_weekly_games (season, week_no,"
                " week_start, week_end, ipl_team_code, games, source)"
                " VALUES ('2027', ?, '2027-03-08', '2027-03-14', ?, ?,"
                " 'standin-2026')", (wk, code, games))
    con.commit()
    return {"league": league}


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / "matrix.db"
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA.read_text())
    ids = _seed(con)
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


def test_matrix_matches_nudges_cell_for_cell(client):
    tc, ids = client
    r = tc.get(f"/api/leagues/{ids['league']}/schedule-matrix")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["source"] == "standin-2026"
    assert body["weeks_available"] == [1, 2, 3, 4, 5]
    rows = {row["ipl_team_code"]: row for row in body["rows"]}
    assert rows["MI"]["games_by_week"] == [2, 1, 3, 0, 2, 0, 0, 0]
    assert rows["MI"]["total"] == 8
    assert rows["CSK"]["games_by_week"] == [1, 1, 1, 1, 1, 0, 0, 0]
    assert rows["CSK"]["total"] == 5
    for wk in range(1, 9):
        nudges = tc.get(
            f"/api/leagues/{ids['league']}/schedule-nudges",
            params={"week_no": wk}).json()
        per_code = {g["ipl_team_code"]: g["games"] for g in nudges["games"]}
        for code, row in rows.items():
            assert row["games_by_week"][wk - 1] == per_code.get(code, 0), \
                (code, wk)


def test_matrix_empty_until_fixture_imports(client):
    tc, ids = client
    # A second league in a season with no fixture rows at all.
    r = tc.get(f"/api/leagues/{ids['league']}/schedule-matrix")
    assert r.status_code == 200
    assert tc.get("/api/leagues/99999/schedule-matrix").status_code == 404
