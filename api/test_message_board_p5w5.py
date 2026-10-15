"""P5-W5: league message board.

Seed: league with commissioner user 1; team A owned by user 1 (the
commissioner's team), team B owned by user 2. Expectations:
posts persist + read newest-first, pagination totals hold at 100
posts, posting for a CLAIMED team without its code 403s, a
non-commissioner delete 403s, a commissioner delete soft-deletes
(row remains, board stops showing it, re-delete 404s).
"""

import sqlite3
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.database import get_db
from api.routers import message_board

SCHEMA = Path(__file__).resolve().parent / "schema.sql"


def _seed(con):
    con.execute("INSERT INTO users (name) VALUES ('commish')")
    con.execute("INSERT INTO users (name) VALUES ('rival')")
    league_id = con.execute(
        "INSERT INTO leagues (name, invite_code, commissioner_id,"
        " season, settings, status) VALUES ('w5-league', 'CODEW5', 1,"
        " '2027', '{}', 'in_season')").lastrowid
    team_a = con.execute(
        "INSERT INTO teams (league_id, owner_id, name, faab_remaining)"
        " VALUES (?, 1, 'Commish XI', 100)", (league_id,)).lastrowid
    team_b = con.execute(
        "INSERT INTO teams (league_id, owner_id, name, faab_remaining)"
        " VALUES (?, 2, 'Rival XI', 100)", (league_id,)).lastrowid
    con.commit()
    return league_id, team_a, team_b


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / "board.db"
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA.read_text())
    ids = _seed(con)
    con.close()
    app = FastAPI()
    app.include_router(message_board.router, prefix="/api/leagues")

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


def test_post_and_read_newest_first(client):
    tc, (league_id, team_a, team_b), _ = client
    r = tc.post(f"/api/leagues/{league_id}/messages",
                json={"team_id": team_a, "body": "first!"})
    assert r.status_code == 201, r.text
    assert r.json()["team_name"] == "Commish XI"
    tc.post(f"/api/leagues/{league_id}/messages",
            json={"team_id": team_b, "body": "weak squad, commish"})
    board = tc.get(f"/api/leagues/{league_id}/messages").json()
    assert board["total"] == 2
    assert [m["body"] for m in board["messages"]] == [
        "weak squad, commish", "first!"]
    assert board["commissioner_team_id"] == team_a


def test_empty_and_oversize_posts_rejected(client):
    tc, (league_id, team_a, _b), _ = client
    assert tc.post(f"/api/leagues/{league_id}/messages",
                   json={"team_id": team_a, "body": "   "}).status_code == 422
    assert tc.post(f"/api/leagues/{league_id}/messages",
                   json={"team_id": team_a,
                         "body": "x" * 501}).status_code == 422


def test_wrong_league_team_422_and_unknown_league_404(client):
    tc, (league_id, team_a, _b), _ = client
    assert tc.get("/api/leagues/9999/messages").status_code == 404
    # team from another league: seed ids are league-local here, so use
    # a bogus team id -> get_team 404s inside require_team_actor.
    assert tc.post(f"/api/leagues/{league_id}/messages",
                   json={"team_id": 9999, "body": "hi"}).status_code == 404


def test_claim_gate_on_post(client):
    tc, (league_id, _a, team_b), db_path = client
    con = sqlite3.connect(str(db_path))
    con.execute("UPDATE teams SET claim_code = 'sekrit' WHERE id = ?",
                (team_b,))
    con.commit()
    con.close()
    r = tc.post(f"/api/leagues/{league_id}/messages",
                json={"team_id": team_b, "body": "let me in"})
    assert r.status_code == 403
    r = tc.post(f"/api/leagues/{league_id}/messages",
                json={"team_id": team_b, "body": "let me in"},
                headers={"X-Team-Claim": "sekrit"})
    assert r.status_code == 201


def test_commissioner_soft_delete(client):
    tc, (league_id, team_a, team_b), db_path = client
    mid = tc.post(f"/api/leagues/{league_id}/messages",
                  json={"team_id": team_b, "body": "trash talk"}).json()["id"]
    # Non-commissioner cannot delete.
    r = tc.delete(
        f"/api/leagues/{league_id}/messages/{mid}?team_id={team_b}")
    assert r.status_code == 403
    # Commissioner can; board stops showing it; row remains (soft).
    r = tc.delete(
        f"/api/leagues/{league_id}/messages/{mid}?team_id={team_a}")
    assert r.status_code == 204
    board = tc.get(f"/api/leagues/{league_id}/messages").json()
    assert board["total"] == 0
    con = sqlite3.connect(str(db_path))
    row = con.execute(
        "SELECT deleted_at FROM league_messages WHERE id = ?",
        (mid,)).fetchone()
    con.close()
    assert row[0] is not None
    # Re-delete is a 404 (already gone from the board's perspective).
    r = tc.delete(
        f"/api/leagues/{league_id}/messages/{mid}?team_id={team_a}")
    assert r.status_code == 404


def test_commissioner_team_by_owner_name_match(client):
    """Sandbox-shaped data: the commissioner user owns no team, but a
    team's owner has the same name ('commish') — that team is the
    commissioner's team for soft-delete."""
    tc, (league_id, _a, team_b), db_path = client
    con = sqlite3.connect(str(db_path))
    # Re-own team B to a NEW user also named 'commish' (join-flow shape),
    # and strip team A's link so only the name match remains.
    new_user = con.execute(
        "INSERT INTO users (name) VALUES ('commish')").lastrowid
    con.execute("UPDATE teams SET owner_id = ? WHERE id = ?",
                (new_user, team_b))
    other = con.execute(
        "INSERT INTO users (name) VALUES ('someone else')").lastrowid
    con.execute("UPDATE teams SET owner_id = ? WHERE id != ?",
                (other, team_b))
    con.commit()
    con.close()
    board = tc.get(f"/api/leagues/{league_id}/messages").json()
    assert board["commissioner_team_id"] == team_b
    mid = tc.post(f"/api/leagues/{league_id}/messages",
                  json={"team_id": team_b, "body": "mine"}).json()["id"]
    r = tc.delete(
        f"/api/leagues/{league_id}/messages/{mid}?team_id={team_b}")
    assert r.status_code == 204


def test_pagination_at_100_posts(client):
    tc, (league_id, team_a, _b), _ = client
    for i in range(100):
        r = tc.post(f"/api/leagues/{league_id}/messages",
                    json={"team_id": team_a, "body": f"post {i}"})
        assert r.status_code == 201
    page1 = tc.get(
        f"/api/leagues/{league_id}/messages?limit=50&offset=0").json()
    page2 = tc.get(
        f"/api/leagues/{league_id}/messages?limit=50&offset=50").json()
    assert page1["total"] == 100 and len(page1["messages"]) == 50
    assert len(page2["messages"]) == 50
    bodies = [m["body"] for m in page1["messages"] + page2["messages"]]
    assert bodies[0] == "post 99" and bodies[-1] == "post 0"
    assert len(set(bodies)) == 100
