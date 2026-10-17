"""P5-W17: private player notes — privacy is the feature.

Fixture: league with teams A (claimed, claim_code CODE-A) and B
(unclaimed), players P1/P2. Every assertion about team B's view is an
assertion that A's notes leave NO trace: B's own list is empty, and
asking for A's list without A's code is a 403, never data.
"""

import sqlite3
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.database import get_db
from api.routers import player_notes

SCHEMA = Path(__file__).resolve().parent / "schema.sql"
HDR_A = {"X-Team-Claim": "CODE-A"}


def _seed(con):
    con.execute("INSERT INTO users (name) VALUES ('w17-owner')")
    league = con.execute(
        "INSERT INTO leagues (name, invite_code, commissioner_id,"
        " season, settings, status) VALUES ('w17-league', 'CODE-w17',"
        " 1, '2027', '{}', 'in_season')").lastrowid
    a = con.execute(
        "INSERT INTO teams (league_id, owner_id, name, faab_remaining,"
        " claim_code) VALUES (?, 1, 'w17-A', 100, 'CODE-A')",
        (league,)).lastrowid
    b = con.execute(
        "INSERT INTO teams (league_id, owner_id, name, faab_remaining)"
        " VALUES (?, 1, 'w17-B', 100)", (league,)).lastrowid
    p1 = con.execute(
        "INSERT INTO players (name, season) VALUES ('Player One',"
        " '2027')").lastrowid
    p2 = con.execute(
        "INSERT INTO players (name, season) VALUES ('Player Two',"
        " '2027')").lastrowid
    con.commit()
    return {"league": league, "a": a, "b": b, "p1": p1, "p2": p2}


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / "notes.db"
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA.read_text())
    ids = _seed(con)
    con.close()

    app = FastAPI()
    app.include_router(player_notes.router, prefix="/api/player-notes")

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


def _put(tc, ids, note="injury watch", headers=HDR_A, team=None, pid=None):
    return tc.put("/api/player-notes", headers=headers, json={
        "league_id": ids["league"], "team_id": team or ids["a"],
        "player_id": pid or ids["p1"], "note": note})


def test_note_round_trip_and_upsert(client):
    tc, ids = client
    r = _put(tc, ids)
    assert r.status_code == 200, r.text
    assert r.json()["note"] == "injury watch"
    assert r.json()["player_name"] == "Player One"
    # Upsert: same (league, team, player) replaces, never duplicates.
    r = _put(tc, ids, note="round-8 target")
    assert r.status_code == 200
    rows = tc.get("/api/player-notes", headers=HDR_A,
                  params={"league_id": ids["league"],
                          "team_id": ids["a"]}).json()
    assert len(rows) == 1 and rows[0]["note"] == "round-8 target"
    # Delete is idempotent.
    for _ in range(2):
        d = tc.delete("/api/player-notes", headers=HDR_A, params={
            "league_id": ids["league"], "team_id": ids["a"],
            "player_id": ids["p1"]})
        assert d.status_code == 204
    rows = tc.get("/api/player-notes", headers=HDR_A,
                  params={"league_id": ids["league"],
                          "team_id": ids["a"]}).json()
    assert rows == []


def test_notes_never_leak_to_other_teams(client):
    tc, ids = client
    assert _put(tc, ids).status_code == 200
    # Team B's own list: empty, no trace of A's note.
    rows_b = tc.get("/api/player-notes",
                    params={"league_id": ids["league"],
                            "team_id": ids["b"]})
    assert rows_b.status_code == 200 and rows_b.json() == []
    # Asking for A's notes without A's claim code: 403, not data.
    snooped = tc.get("/api/player-notes",
                     params={"league_id": ids["league"],
                             "team_id": ids["a"]})
    assert snooped.status_code == 403
    assert "injury watch" not in snooped.text
    # Writes are gated the same way.
    assert _put(tc, ids, headers={}).status_code == 403
    assert _put(tc, ids, headers={"X-Team-Claim": "WRONG"}
                ).status_code == 403
    d = tc.delete("/api/player-notes", params={
        "league_id": ids["league"], "team_id": ids["a"],
        "player_id": ids["p1"]})
    assert d.status_code == 403
    # And B writing its OWN note on the same player is independent.
    assert _put(tc, ids, note="B's take", headers={}, team=ids["b"]
                ).status_code == 200
    rows_a = tc.get("/api/player-notes", headers=HDR_A,
                    params={"league_id": ids["league"],
                            "team_id": ids["a"]}).json()
    assert [r["note"] for r in rows_a] == ["injury watch"]


def test_note_validation(client):
    tc, ids = client
    assert _put(tc, ids, note="   ").status_code == 422
    assert _put(tc, ids, note="x" * 501).status_code == 422
    assert _put(tc, ids, pid=99999).status_code == 404
    assert tc.get("/api/player-notes", headers=HDR_A,
                  params={"league_id": 99999, "team_id": ids["a"]}
                  ).status_code == 404
