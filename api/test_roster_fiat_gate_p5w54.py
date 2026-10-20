"""P5-W54: POST /api/leagues/{id}/roster-moves is commissioner-gated —
hand-derived.

Scratch league: commissioner user 1 owns the commissioner's team; a
second team belongs to user 2. The commissioner's team carries 15
rostered players (so a fiat drop clears the P4-W29 floor of 14); one
free-agent player sits unowned. Expectations are computed by hand:

1. a non-commissioner team named as commissioner_team_id -> 403, and
   both teams' rosters plus the adjustments log are byte-identical to
   before (nothing was written).
2. the claimed commissioner's team without its X-Team-Claim header ->
   403 (P4-W18 claim gate), roster unchanged.
3. the claimed commissioner's team with a wrong code -> 403.
4. the claimed commissioner's team with the right code -> 200; the add
   lands on the target team and the league_adjustments row carries
   kind='roster_add' with the audit note.
5. an UNCLAIMED commissioner's team acts without a header -> 200
   (honor-system, same as P4-W18); a drop lands and is audited.
6. a body with no commissioner_team_id at all -> 422 (schema rejects).
"""

import sqlite3
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.database import get_db
from api.routers import leagues

SCHEMA = Path(__file__).resolve().parent / "schema.sql"
COMM_CODE = "ROSTERF01"
ROSTER_N = 15  # commissioner's team construction roster


def _seed(con, claim_code=None):
    con.execute("INSERT INTO users (name) VALUES ('comm')")
    con.execute("INSERT INTO users (name) VALUES ('rival')")
    league = con.execute(
        "INSERT INTO leagues (name, invite_code, commissioner_id,"
        " season, settings, status) VALUES ('fiat', 'CODE-fiat', 1,"
        " '2027', '{}', 'setup')").lastrowid
    comm = con.execute(
        "INSERT INTO teams (league_id, name, owner_id) VALUES"
        " (?, 'Comm XI', 1)", (league,)).lastrowid
    other = con.execute(
        "INSERT INTO teams (league_id, name, owner_id) VALUES"
        " (?, 'Rival XI', 2)", (league,)).lastrowid
    if claim_code is not None:
        con.execute("UPDATE teams SET claim_code = ? WHERE id = ?",
                    (claim_code, comm))
    roster_pids = []
    for i in range(ROSTER_N):
        pid = con.execute(
            "INSERT INTO players (name, season) VALUES (?, '2027')",
            (f"Roster P{i}",)).lastrowid
        roster_pids.append(pid)
        con.execute(
            "INSERT INTO roster_slots (team_id, player_id, slot, week_no)"
            " VALUES (?, ?, 'BN', NULL)", (comm, pid))
    free = con.execute(
        "INSERT INTO players (name, season) VALUES ('Free Agent FA',"
        " '2027')").lastrowid
    con.commit()
    return league, comm, other, roster_pids, free


def _app(db_path):
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
    return app


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / "fiat.db"
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA.read_text())
    league, comm, other, roster_pids, free = _seed(con, claim_code=COMM_CODE)
    con.close()
    return (TestClient(_app(db_path)), db_path, league, comm, other,
            roster_pids, free)


@pytest.fixture()
def unclaimed_client(tmp_path):
    """Same shape but the commissioner's team is NOT claimed: no header
    needed (P4-W18 honor-system for unclaimed teams)."""
    db_path = tmp_path / "fiatu.db"
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA.read_text())
    league, comm, other, roster_pids, free = _seed(con, claim_code=None)
    con.close()
    return (TestClient(_app(db_path)), db_path, league, comm, other,
            roster_pids, free)


def _roster_snapshot(db_path):
    """Hand-computed baseline: every roster slot row + the count of
    audit rows. Any write by the endpoint would move this."""
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    slots = [tuple(r) for r in con.execute(
        "SELECT team_id, player_id, slot, week_no FROM roster_slots"
        " ORDER BY team_id, player_id")]
    adj = con.execute("SELECT COUNT(*) FROM league_adjustments").fetchone()[0]
    con.close()
    return slots, adj


def _adjustments(db_path, league):
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    rows = [dict(r) for r in con.execute(
        "SELECT team_id, kind, player_id, player_name, note"
        " FROM league_adjustments WHERE league_id = ? ORDER BY id",
        (league,))]
    con.close()
    return rows


def test_non_commissioner_403_and_roster_unchanged(client):
    tc, db_path, league, comm, other, roster_pids, free = client
    before = _roster_snapshot(db_path)
    r = tc.post(f"/api/leagues/{league}/roster-moves",
                json={"team_id": comm, "player_id": free, "action": "add",
                      "note": "rival tries fiat", "commissioner_team_id": other})
    assert r.status_code == 403, r.text
    assert "only the commissioner's team" in r.json()["detail"]
    # nothing was written: rosters and the audit log are byte-identical.
    assert _roster_snapshot(db_path) == before


def test_claimed_commissioner_needs_claim_code(client):
    tc, db_path, league, comm, other, roster_pids, free = client
    before = _roster_snapshot(db_path)
    r = tc.post(f"/api/leagues/{league}/roster-moves",
                json={"team_id": comm, "player_id": free, "action": "add",
                      "note": "no header", "commissioner_team_id": comm})
    assert r.status_code == 403, r.text
    assert _roster_snapshot(db_path) == before


def test_claimed_commissioner_wrong_code_403(client):
    tc, db_path, league, comm, other, roster_pids, free = client
    before = _roster_snapshot(db_path)
    r = tc.post(f"/api/leagues/{league}/roster-moves",
                json={"team_id": comm, "player_id": free, "action": "add",
                      "note": "wrong code", "commissioner_team_id": comm},
                headers={"X-Team-Claim": "WRONGCODE"})
    assert r.status_code == 403, r.text
    assert _roster_snapshot(db_path) == before


def test_commissioner_with_code_200_and_applies(client):
    tc, db_path, league, comm, other, roster_pids, free = client
    r = tc.post(f"/api/leagues/{league}/roster-moves",
                json={"team_id": other, "player_id": free, "action": "add",
                      "note": "fiat add to rival", "commissioner_team_id": comm},
                headers={"X-Team-Claim": COMM_CODE})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["team_id"] == other
    assert body["team_name"] == "Rival XI"
    assert body["kind"] == "roster_add"
    assert body["player_name"] == "Free Agent FA"
    assert body["note"] == "fiat add to rival"
    # the DB agrees: slot row on the target team + audited adjustment row.
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    slot = con.execute(
        "SELECT 1 FROM roster_slots WHERE team_id = ? AND player_id = ?"
        " AND week_no IS NULL", (other, free)).fetchone()
    con.close()
    assert slot is not None
    adj = _adjustments(db_path, league)
    assert len(adj) == 1
    assert adj[0] == {"team_id": other, "kind": "roster_add",
                      "player_id": free, "player_name": "Free Agent FA",
                      "note": "fiat add to rival"}


def test_unclaimed_commissioner_honor_system_200(unclaimed_client):
    tc, db_path, league, comm, other, roster_pids, free = unclaimed_client
    r = tc.post(f"/api/leagues/{league}/roster-moves",
                json={"team_id": comm, "player_id": roster_pids[0],
                      "action": "drop", "note": "fiat drop",
                      "commissioner_team_id": comm})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["kind"] == "roster_drop"
    assert body["player_name"] == "Roster P0"
    assert body["note"] == "fiat drop"
    # the player left the construction roster and the drop was audited.
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    slot = con.execute(
        "SELECT 1 FROM roster_slots WHERE team_id = ? AND player_id = ?",
        (comm, roster_pids[0])).fetchone()
    remaining = con.execute(
        "SELECT COUNT(*) FROM roster_slots WHERE team_id = ?"
        " AND week_no IS NULL", (comm,)).fetchone()[0]
    con.close()
    assert slot is None
    assert remaining == ROSTER_N - 1
    adj = _adjustments(db_path, league)
    assert len(adj) == 1
    assert adj[0]["kind"] == "roster_drop"
    assert adj[0]["player_id"] == roster_pids[0]
    assert adj[0]["note"] == "fiat drop"


def test_missing_identity_422(client):
    tc, db_path, league, comm, other, roster_pids, free = client
    r = tc.post(f"/api/leagues/{league}/roster-moves",
                json={"team_id": comm, "player_id": free, "action": "add",
                      "note": "no identity"},
                headers={"X-Team-Claim": COMM_CODE})
    assert r.status_code == 422, r.text
