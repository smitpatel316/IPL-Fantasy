"""P5-W7: trade block — league-wide "on the block" board.

A manager lists their own rostered players with a short seeking note;
other teams' listings are read-only; writes are claim-aware (P4-W18);
a listing auto-expires when the player leaves the roster.

Hand-derived expectations:
  * Alpha (BAT, MI) is rostered by league-1 team A; listing him with
    seeking "want a BOWL" round-trips with team/player names + role.
  * Re-posting the same player updates the note, same listing id.
  * Listing a free agent or another team's player -> 422.
  * Once Alpha's roster_slot moves to team B, the listing vanishes
    from the board (auto-expire) and the row is pruned.
"""

import sqlite3
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.database import get_db
from api.routers import trade_block

SCHEMA = Path(__file__).resolve().parent / "schema.sql"


def _seed(con):
    con.execute("INSERT INTO users (name) VALUES ('w7-owner')")
    ids = {}
    league_id = con.execute(
        "INSERT INTO leagues (name, invite_code, commissioner_id,"
        " season, settings, status) VALUES ('w7-league', 'CODE-w7', 1,"
        " '2027', '{}', 'in_season')").lastrowid
    ids["league"] = league_id
    for label in ("A", "B"):
        t = con.execute(
            "INSERT INTO teams (league_id, owner_id, name,"
            " faab_remaining) VALUES (?, 1, ?, 100)",
            (league_id, f"w7-{label}")).lastrowid
        ids[f"team{label}"] = t
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
    # Alpha rostered by team A; Beta is a free agent.
    con.execute(
        "INSERT INTO roster_slots (team_id, player_id, slot)"
        " VALUES (?, ?, 'BAT')", (ids["teamA"], alpha))
    con.commit()
    return ids


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / "trade_block.db"
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA.read_text())
    ids = _seed(con)
    con.close()

    app = FastAPI()
    app.include_router(trade_block.router, prefix="/api/trade-block")

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


def _post(tc, ids, **kw):
    body = {"league_id": ids["league"], "team_id": ids["teamA"],
            "player_id": ids["alpha"], "seeking": "want a BOWL"}
    body.update(kw)
    return tc.post("/api/trade-block", json=body)


def test_post_and_list_round_trip(client):
    tc, ids, _ = client
    r = _post(tc, ids)
    assert r.status_code == 200, r.text
    e = r.json()
    assert e["name"] == "Alpha" and e["role"] == "BAT"
    assert e["ipl_team_code"] == "MI" and e["team_name"] == "w7-A"
    assert e["seeking"] == "want a BOWL"
    board = tc.get("/api/trade-block",
                   params={"league_id": ids["league"]}).json()
    assert [x["player_id"] for x in board] == [ids["alpha"]]


def test_repost_updates_note_same_listing(client):
    tc, ids, _ = client
    first = _post(tc, ids).json()
    second = _post(tc, ids, seeking="will move for an AR").json()
    assert first["id"] == second["id"]
    assert second["seeking"] == "will move for an AR"
    board = tc.get("/api/trade-block",
                   params={"league_id": ids["league"]}).json()
    assert len(board) == 1


def test_only_own_roster_can_be_listed(client):
    tc, ids, _ = client
    # Free agent Beta cannot be listed by anyone.
    assert _post(tc, ids, player_id=ids["beta"]).status_code == 422
    # Team B cannot list team A's player.
    assert _post(tc, ids, team_id=ids["teamB"]).status_code == 422


def test_remove_is_idempotent(client):
    tc, ids, _ = client
    _post(tc, ids)
    params = {"league_id": ids["league"], "team_id": ids["teamA"],
              "player_id": ids["alpha"]}
    assert tc.delete("/api/trade-block", params=params).status_code == 204
    assert tc.delete("/api/trade-block", params=params).status_code == 204
    board = tc.get("/api/trade-block",
                   params={"league_id": ids["league"]}).json()
    assert board == []


def test_listing_auto_expires_when_player_moves(client):
    tc, ids, db_path = client
    _post(tc, ids)
    con = sqlite3.connect(str(db_path))
    con.execute("UPDATE roster_slots SET team_id = ? WHERE player_id = ?",
                (ids["teamB"], ids["alpha"]))
    con.commit()
    con.close()
    board = tc.get("/api/trade-block",
                   params={"league_id": ids["league"]}).json()
    assert board == []
    con = sqlite3.connect(str(db_path))
    assert con.execute("SELECT COUNT(*) FROM trade_block").fetchone()[0] == 0
    con.close()


def test_claimed_team_write_requires_code(client):
    tc, ids, db_path = client
    _claim_code(db_path, ids["teamA"], "SECRET1234")
    assert _post(tc, ids).status_code == 403
    r = tc.post("/api/trade-block", json={
        "league_id": ids["league"], "team_id": ids["teamA"],
        "player_id": ids["alpha"], "seeking": "want a BOWL"},
        headers={"X-Team-Claim": "SECRET1234"})
    assert r.status_code == 200, r.text
    params = {"league_id": ids["league"], "team_id": ids["teamA"],
              "player_id": ids["alpha"]}
    assert tc.delete("/api/trade-block", params=params).status_code == 403
    assert tc.delete("/api/trade-block", params=params,
                     headers={"X-Team-Claim": "SECRET1234"}).status_code == 204


def test_validation_errors(client):
    tc, ids, _ = client
    assert _post(tc, ids, player_id=99999).status_code == 404
    assert _post(tc, ids, league_id=99999).status_code == 404
    assert _post(tc, ids, team_id=99999).status_code == 404
    assert tc.get("/api/trade-block",
                  params={"league_id": 99999}).status_code == 404
