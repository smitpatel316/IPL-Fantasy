"""P5-W2: per-team player watchlist.

Star/unstar players from the players list / waiver wire; the watched
section is persisted per league+team and derives ownership % / avg
points with the same maps as the players list (P4-W19). Writes are
claim-aware: a CLAIMED team's star/unstar must present its claim code
in X-Team-Claim (P4-W18, require_team_actor); reads are open.

Hand-derived expectations:
  * Starred BAT "Alpha" is rostered in 1 of 2 seeded leagues ->
    ownership_pct 50.0; two scored matches at 10 and 20 fantasy
    points -> avg_points 15.0; owned_by_team_id = his league-1 owner.
  * Re-starring returns the same watch_id; unstarring twice is 204
    both times (idempotent end state).
"""

import sqlite3
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.database import get_db
from api.routers import watchlist

SCHEMA = Path(__file__).resolve().parent / "schema.sql"


def _seed(con):
    """2 leagues x 2 teams; 'Alpha' (BAT, MI) rostered by league-1
    team A; two scored matches for Alpha (10, 20 pts)."""
    con.execute("INSERT INTO users (name) VALUES ('w2-owner')")
    ids = {}
    for lg in (1, 2):
        league_id = con.execute(
            "INSERT INTO leagues (name, invite_code, commissioner_id,"
            " season, settings, status) VALUES (?, ?, 1, '2027', '{}',"
            " 'in_season')",
            (f"w2-league-{lg}", f"CODE-w2-{lg}"),
        ).lastrowid
        ids[f"league{lg}"] = league_id
        for label in ("A", "B"):
            t = con.execute(
                "INSERT INTO teams (league_id, owner_id, name,"
                " faab_remaining) VALUES (?, 1, ?, 100)",
                (league_id, f"w2-L{lg}-{label}"),
            ).lastrowid
            ids[f"team{lg}{label}"] = t
    alpha = con.execute(
        "INSERT INTO players (name, season) VALUES ('Alpha', '2027')"
    ).lastrowid
    beta = con.execute(
        "INSERT INTO players (name, season) VALUES ('Beta', '2027')"
    ).lastrowid
    con.execute(
        "INSERT INTO player_roles (player_id, season, role, is_overseas,"
        " ipl_team_code) VALUES (?, '2027', 'BAT', 0, 'MI')", (alpha,))
    con.execute(
        "INSERT INTO player_roles (player_id, season, role, is_overseas,"
        " ipl_team_code) VALUES (?, '2027', 'BOWL', 1, 'CSK')", (beta,))
    ids["alpha"], ids["beta"] = alpha, beta
    # Alpha sits on league-1 team A's construction roster only.
    con.execute(
        "INSERT INTO roster_slots (team_id, player_id, slot)"
        " VALUES (?, ?, 'BAT')",
        (ids["team1A"], alpha))
    for pts in (10, 20):
        m = con.execute(
            "INSERT INTO matches (season, week_no, status)"
            " VALUES ('2027', 1, 'completed')").lastrowid
        con.execute(
            "INSERT INTO player_match_stats (match_id, player_id,"
            " player_name, fantasy_points) VALUES (?, ?, 'Alpha', ?)",
            (m, alpha, pts))
    con.commit()
    return ids


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / "watchlist.db"
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA.read_text())
    ids = _seed(con)
    con.close()

    app = FastAPI()
    app.include_router(watchlist.router, prefix="/api/watchlist")

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


def _claim_code(db_path, team_id, code):
    con = sqlite3.connect(str(db_path))
    con.execute("UPDATE teams SET claim_code = ? WHERE id = ?",
                (code, team_id))
    con.commit()
    con.close()


def test_star_persists_and_derives_ownership_and_avg(client):
    tc, ids, _ = client
    r = tc.post("/api/watchlist", json={
        "league_id": ids["league1"], "team_id": ids["team1A"],
        "player_id": ids["alpha"]})
    assert r.status_code == 200, r.text
    entry = r.json()
    # Hand-derived: rostered in 1 of 2 leagues -> 50%; (10+20)/2 = 15.0.
    assert entry["name"] == "Alpha"
    assert entry["role"] == "BAT"
    assert entry["ipl_team_code"] == "MI"
    assert entry["ownership_pct"] == 50.0
    assert entry["avg_points"] == 15.0
    assert entry["owned_by_team_id"] == ids["team1A"]
    got = tc.get("/api/watchlist", params={
        "league_id": ids["league1"], "team_id": ids["team1A"]})
    assert [e["id"] for e in got.json()] == [ids["alpha"]]


def test_restar_is_idempotent(client):
    tc, ids, _ = client
    body = {"league_id": ids["league1"], "team_id": ids["team1A"],
            "player_id": ids["beta"]}
    first = tc.post("/api/watchlist", json=body).json()
    second = tc.post("/api/watchlist", json=body).json()
    assert first["watch_id"] == second["watch_id"]
    got = tc.get("/api/watchlist", params={
        "league_id": ids["league1"], "team_id": ids["team1A"]})
    assert len(got.json()) == 1


def test_unstar_is_idempotent(client):
    tc, ids, _ = client
    body = {"league_id": ids["league1"], "team_id": ids["team1A"],
            "player_id": ids["beta"]}
    tc.post("/api/watchlist", json=body)
    params = {"league_id": ids["league1"], "team_id": ids["team1A"],
              "player_id": ids["beta"]}
    assert tc.delete("/api/watchlist", params=params).status_code == 204
    assert tc.delete("/api/watchlist", params=params).status_code == 204
    got = tc.get("/api/watchlist", params={
        "league_id": ids["league1"], "team_id": ids["team1A"]})
    assert got.json() == []


def test_watchlist_is_per_team_and_per_league(client):
    tc, ids, _ = client
    tc.post("/api/watchlist", json={
        "league_id": ids["league1"], "team_id": ids["team1A"],
        "player_id": ids["alpha"]})
    for params in (
        {"league_id": ids["league1"], "team_id": ids["team1B"]},
        {"league_id": ids["league2"], "team_id": ids["team2A"]},
    ):
        got = tc.get("/api/watchlist", params=params)
        assert got.json() == []


def test_claimed_team_write_requires_code(client):
    tc, ids, db_path = client
    _claim_code(db_path, ids["team1A"], "SECRET1234")
    body = {"league_id": ids["league1"], "team_id": ids["team1A"],
            "player_id": ids["alpha"]}
    # No header and wrong header are both rejected; the read is open.
    assert tc.post("/api/watchlist", json=body).status_code == 403
    assert tc.post("/api/watchlist", json=body,
                   headers={"X-Team-Claim": "WRONG"}).status_code == 403
    r = tc.post("/api/watchlist", json=body,
                headers={"X-Team-Claim": "SECRET1234"})
    assert r.status_code == 200, r.text
    params = {"league_id": ids["league1"], "team_id": ids["team1A"],
              "player_id": ids["alpha"]}
    assert tc.delete("/api/watchlist", params=params).status_code == 403
    assert tc.delete("/api/watchlist", params=params,
                     headers={"X-Team-Claim": "SECRET1234"}).status_code == 204
    got = tc.get("/api/watchlist", params={
        "league_id": ids["league1"], "team_id": ids["team1A"]})
    assert got.json() == []


def test_validation_errors(client):
    tc, ids, _ = client
    # Unknown player / league / team.
    assert tc.post("/api/watchlist", json={
        "league_id": ids["league1"], "team_id": ids["team1A"],
        "player_id": 99999}).status_code == 404
    assert tc.post("/api/watchlist", json={
        "league_id": 99999, "team_id": ids["team1A"],
        "player_id": ids["alpha"]}).status_code == 404
    assert tc.post("/api/watchlist", json={
        "league_id": ids["league1"], "team_id": 99999,
        "player_id": ids["alpha"]}).status_code == 404
    # Team from another league.
    assert tc.post("/api/watchlist", json={
        "league_id": ids["league2"], "team_id": ids["team1A"],
        "player_id": ids["alpha"]}).status_code == 422
    assert tc.get("/api/watchlist", params={
        "league_id": ids["league2"],
        "team_id": ids["team1A"]}).status_code == 422
