"""P5-W39: pinned commissioner announcements.

Seed: league with commissioner user 1; team A owned by user 1 (the
commissioner's team), team B owned by user 2. Expectations:
- pin by the commissioner's team stamps pinned_at; the post leaves
  the feed and arrives as board.pinned_message (the strip).
- pinning a second post unpins the first (one active pin).
- a non-commissioner pin attempt 403s; pinning another team's post 422s.
- unpin clears the strip and restores normal feed order.
- deleting a pinned post clears the strip.
- pinning a missing or soft-deleted post 404s; unpinning a
  non-pinned post 422s.
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
        " season, settings, status) VALUES ('w39-league', 'CODEW39', 1,"
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
    db_path = tmp_path / "pins.db"
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


def _post(tc, league_id, team_id, body):
    r = tc.post(f"/api/leagues/{league_id}/messages",
                json={"team_id": team_id, "body": body})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_pin_round_trip_strip_above_feed(client):
    tc, (league_id, team_a, team_b), _ = client
    older = _post(tc, league_id, team_a, "old commish note")
    _post(tc, league_id, team_b, "rival chatter")
    r = tc.post(f"/api/leagues/{league_id}/messages/{older}/pin",
                params={"team_id": team_a})
    assert r.status_code == 200, r.text
    assert r.json()["pinned_at"] is not None

    board = tc.get(f"/api/leagues/{league_id}/messages").json()
    assert board["pinned_message"]["id"] == older
    assert board["pinned_message"]["pinned_at"] is not None
    # pinned post leaves the feed (no duplicate render)
    assert [m["id"] for m in board["messages"]] != [older]
    assert all(m["id"] != older for m in board["messages"])
    assert board["total"] == 1
    assert [m["body"] for m in board["messages"]] == ["rival chatter"]


def test_pinning_new_one_unpins_old(client):
    tc, (league_id, team_a, _), _ = client
    first = _post(tc, league_id, team_a, "first announcement")
    second = _post(tc, league_id, team_a, "second announcement")
    r = tc.post(f"/api/leagues/{league_id}/messages/{first}/pin",
                params={"team_id": team_a})
    assert r.status_code == 200, r.text
    r = tc.post(f"/api/leagues/{league_id}/messages/{second}/pin",
                params={"team_id": team_a})
    assert r.status_code == 200, r.text

    board = tc.get(f"/api/leagues/{league_id}/messages").json()
    assert board["pinned_message"]["id"] == second
    # old pin is back in the feed in normal newest-first order
    assert [m["body"] for m in board["messages"]] == ["first announcement"]


def test_non_commissioner_pin_forbidden(client):
    tc, (league_id, team_a, team_b), _ = client
    msg = _post(tc, league_id, team_a, "commish note")
    r = tc.post(f"/api/leagues/{league_id}/messages/{msg}/pin",
                params={"team_id": team_b})
    assert r.status_code == 403, r.text
    r = tc.post(f"/api/leagues/{league_id}/messages/{msg}/unpin",
                params={"team_id": team_b})
    assert r.status_code == 403, r.text
    board = tc.get(f"/api/leagues/{league_id}/messages").json()
    assert board["pinned_message"] is None


def test_cannot_pin_another_teams_post(client):
    tc, (league_id, team_a, team_b), _ = client
    msg = _post(tc, league_id, team_b, "rival note")
    r = tc.post(f"/api/leagues/{league_id}/messages/{msg}/pin",
                params={"team_id": team_a})
    assert r.status_code == 422, r.text
    board = tc.get(f"/api/leagues/{league_id}/messages").json()
    assert board["pinned_message"] is None


def test_unpin_restores_feed_order(client):
    tc, (league_id, team_a, team_b), _ = client
    old = _post(tc, league_id, team_a, "old commish note")
    _post(tc, league_id, team_b, "rival chatter")
    r = tc.post(f"/api/leagues/{league_id}/messages/{old}/pin",
                params={"team_id": team_a})
    assert r.status_code == 200, r.text
    r = tc.post(f"/api/leagues/{league_id}/messages/{old}/unpin",
                params={"team_id": team_a})
    assert r.status_code == 200, r.text
    assert r.json()["pinned_at"] is None

    board = tc.get(f"/api/leagues/{league_id}/messages").json()
    assert board["pinned_message"] is None
    assert board["total"] == 2
    assert [m["body"] for m in board["messages"]] == [
        "rival chatter", "old commish note"]


def test_deleted_pinned_post_clears_strip(client):
    tc, (league_id, team_a, team_b), _ = client
    msg = _post(tc, league_id, team_a, "doomed announcement")
    r = tc.post(f"/api/leagues/{league_id}/messages/{msg}/pin",
                params={"team_id": team_a})
    assert r.status_code == 200, r.text
    r = tc.delete(f"/api/leagues/{league_id}/messages/{msg}",
                  params={"team_id": team_a})
    assert r.status_code == 204, r.text

    board = tc.get(f"/api/leagues/{league_id}/messages").json()
    assert board["pinned_message"] is None
    assert board["total"] == 0
    assert board["messages"] == []


def test_pin_missing_or_deleted_is_404_and_unpin_not_pinned_is_422(client):
    tc, (league_id, team_a, _), _ = client
    r = tc.post(f"/api/leagues/{league_id}/messages/9999/pin",
                params={"team_id": team_a})
    assert r.status_code == 404, r.text
    msg = _post(tc, league_id, team_a, "gone announcement")
    r = tc.delete(f"/api/leagues/{league_id}/messages/{msg}",
                  params={"team_id": team_a})
    assert r.status_code == 204, r.text
    r = tc.post(f"/api/leagues/{league_id}/messages/{msg}/pin",
                params={"team_id": team_a})
    assert r.status_code == 404, r.text

    other = _post(tc, league_id, team_a, "never pinned")
    r = tc.post(f"/api/leagues/{league_id}/messages/{other}/unpin",
                params={"team_id": team_a})
    assert r.status_code == 422, r.text
