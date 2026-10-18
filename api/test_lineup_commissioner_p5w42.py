"""P5-W42: commissioner lineup management — hand-derived.

Commissioner (team COMM) sets another team's (TARGET) week-1 lineup:
  1. commish PUT -> 200, week-1 snapshot replaced, league_adjustments row
     (kind 'lineup_set') carries the mandatory audit note, and the target
     team's ledger renders "Commissioner set lineup — Week 1 — <note>".
  2. a non-commissioner team acting as commissioner_team_id -> 403.
  3. a week past the D5 lock -> 422 (lock enforced unchanged).
  4. empty audit note -> 422 (note is mandatory).
  5. commissioner's claimed team without its claim code -> 403 (P4-W18).
The manager's own PUT path still round-trips (regression via refactor).
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.database import get_db
from api.routers import ledger, lineups

SCHEMA = Path(__file__).resolve().parent / "schema.sql"

PLAN = ["WK", "BAT", "BAT", "BAT", "AR", "AR", "BOWL", "BOWL",
        "BOWL", "BAT", "AR", "BOWL", "BAT", "WK"]


def _player(con, name, role, team_id):
    pid = con.execute(
        "INSERT INTO players (name, season) VALUES (?, '2027')",
        (name,)).lastrowid
    con.execute(
        "INSERT INTO player_roles (player_id, season, role, is_overseas,"
        " ipl_team_code, status) VALUES (?, '2027', ?, 0, 'MI', 'active')",
        (pid, role))
    con.execute(
        "INSERT INTO roster_slots (team_id, player_id, slot)"
        " VALUES (?, ?, 'BN')", (team_id, pid))
    return pid


def _seed(con):
    con.execute("INSERT INTO users (name) VALUES ('w42-comm-owner')")
    con.execute("INSERT INTO users (name) VALUES ('w42-other-owner')")
    league = con.execute(
        "INSERT INTO leagues (name, invite_code, commissioner_id,"
        " season, settings, status) VALUES ('w42-league', 'CODE-w42',"
        " 1, '2027', '{}', 'in_season')").lastrowid
    comm = con.execute(
        "INSERT INTO teams (league_id, owner_id, name, faab_remaining)"
        " VALUES (?, 1, 'w42-COMM', 100)", (league,)).lastrowid
    target = con.execute(
        "INSERT INTO teams (league_id, owner_id, name, faab_remaining)"
        " VALUES (?, 2, 'w42-TARGET', 100)", (league,)).lastrowid
    other = con.execute(
        "INSERT INTO teams (league_id, owner_id, name, faab_remaining)"
        " VALUES (?, 2, 'w42-OTHER', 100)", (league,)).lastrowid
    ids = {"league": league, "comm": comm, "target": target, "other": other}
    ids["t"] = [_player(con, f"T{i + 1}", role, target)
                for i, role in enumerate(PLAN)]
    con.commit()
    return ids


def _xi(t):
    return {"WK": [t[0]], "BAT": t[1:4], "AR": t[4:6], "BOWL": t[6:9],
            "UTIL": t[9:11], "BN": t[11:14], "IL": []}


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / "comm_lineup.db"
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA.read_text())
    ids = _seed(con)
    con.close()
    app = FastAPI()
    app.include_router(lineups.router, prefix="/api")
    app.include_router(ledger.router, prefix="/api/leagues")

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


def _comm_put(tc, ids, **over):
    body = {"commissioner_team_id": ids["comm"], "week_no": 1,
            "slots": _xi(ids["t"]), "note": "manager asked over chat"}
    body.update(over)
    return tc.put(f"/api/teams/{ids['target']}/lineup/commissioner", json=body)


def test_commissioner_sets_other_team_lineup(client):
    tc, ids, db_path = client
    r = _comm_put(tc, ids)
    assert r.status_code == 200, r.text
    assert r.json()["team_id"] == ids["target"]
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    wk1 = con.execute(
        "SELECT player_id FROM roster_slots WHERE team_id = ? AND week_no = 1",
        (ids["target"],)).fetchall()
    assert {x["player_id"] for x in wk1} == set(ids["t"])
    adj = con.execute(
        "SELECT kind, note, faab_delta FROM league_adjustments"
        " WHERE team_id = ?", (ids["target"],)).fetchall()
    con.close()
    assert len(adj) == 1
    assert adj[0]["kind"] == "lineup_set"
    assert adj[0]["faab_delta"] == 0
    assert "Week 1" in adj[0]["note"] and "manager asked over chat" in adj[0]["note"]
    # the target team's ledger shows the audit note
    lg = tc.get(f"/api/leagues/{ids['league']}/teams/{ids['target']}/ledger")
    assert lg.status_code == 200, lg.text
    entries = lg.json()["entries"] if isinstance(lg.json(), dict) else lg.json()
    texts = [e["text"] for e in entries]
    assert any("Commissioner set lineup" in t and "manager asked over chat" in t
               for t in texts), texts


def test_non_commissioner_403(client):
    tc, ids, _ = client
    r = _comm_put(tc, ids, commissioner_team_id=ids["other"])
    assert r.status_code == 403, r.text


def test_locked_week_422(client, monkeypatch):
    tc, ids, _ = client
    past = datetime(2020, 1, 1, tzinfo=timezone.utc)
    monkeypatch.setattr(lineups, "lineup_lock_at",
                        lambda con, lid, week: past)
    r = _comm_put(tc, ids)
    assert r.status_code == 422, r.text
    assert "locked" in r.text


def test_missing_note_422(client):
    tc, ids, _ = client
    r = _comm_put(tc, ids, note="")
    assert r.status_code == 422, r.text


def test_commissioner_claim_gate_403(client):
    tc, ids, db_path = client
    con = sqlite3.connect(str(db_path))
    con.execute("UPDATE teams SET claim_code = 'SECRET' WHERE id = ?",
                (ids["comm"],))
    con.commit()
    con.close()
    r = _comm_put(tc, ids)  # no X-Team-Claim header
    assert r.status_code == 403, r.text
    r2 = tc.put(f"/api/teams/{ids['target']}/lineup/commissioner",
                headers={"X-Team-Claim": "SECRET"},
                json={"commissioner_team_id": ids["comm"], "week_no": 1,
                      "slots": _xi(ids["t"]), "note": "with code"})
    assert r2.status_code == 200, r2.text
