"""P5-W36: counter-trade proposals — hand-derived fixture.

Three teams A/B/C, each with a fieldable 14-man domestic roster
(WK2 BAT4 AR3 BOWL5). A proposes to B (A's BAT1 for B's BOWL1).

  * B counters with B's BAT1 for A's AR1 (sides reversed through the
    existing propose path) -> the new trade carries counter_of =
    original id; the original's list entry gains countered_by =
    [counter id] and is otherwise byte-identical.
  * A (the proposer) or C (a non-party) countering -> 422 (only the
    original's recipient can counter).
  * A counter that strips B of both WKs (2-for-2 for A BATs) leaves
    B unable to field a legal XI -> 422 via the P4-W24 D8 guard on
    the propose path, and no trade is created.
  * Countering a rejected (non-pending) trade -> 422; unknown trade
    -> 404.
"""

import sqlite3
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import services
from api.database import get_db
from api.routers import trades

SCHEMA = Path(__file__).resolve().parent / "schema.sql"
ROSTER = ["WK", "WK", "BAT", "BAT", "BAT", "BAT",
          "AR", "AR", "AR", "BOWL", "BOWL", "BOWL", "BOWL", "BOWL"]


def _seed(con):
    con.execute("INSERT INTO users (name) VALUES ('w36-owner')")
    league = con.execute(
        "INSERT INTO leagues (name, invite_code, commissioner_id,"
        " season, settings, status) VALUES ('w36-league', 'CODE-w36',"
        " 1, '2027', '{}', 'in_season')").lastrowid
    ids = {"league": league}
    for label in "ABC":
        tid = con.execute(
            "INSERT INTO teams (league_id, owner_id, name,"
            " faab_remaining) VALUES (?, 1, ?, 100)",
            (league, f"w36-{label}")).lastrowid
        ids[label.lower()] = tid
        for i, role in enumerate(ROSTER, start=1):
            pid = con.execute(
                "INSERT INTO players (name, season) VALUES (?, '2027')",
                (f"{label}-{role}-{i}",)).lastrowid
            con.execute(
                "INSERT INTO player_roles (player_id, season, role,"
                " is_overseas, ipl_team_code) VALUES (?, '2027', ?, 0,"
                " 'MI')", (pid, role))
            con.execute(
                "INSERT INTO roster_slots (team_id, player_id, slot)"
                " VALUES (?, ?, 'BN')", (tid, pid))
            ids[f"{label.lower()}_{role.lower()}{ROSTER[:i].count(role)}"] = pid
    con.commit()
    return ids


@pytest.fixture()
def client(tmp_path):
    services._registry.clear()  # engine cache is keyed by league id
    db_path = tmp_path / "counter.db"
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA.read_text())
    ids = _seed(con)
    con.close()
    app = FastAPI()
    app.include_router(trades.router, prefix="/api/trades")

    def override():
        c = sqlite3.connect(str(db_path))
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys = ON")
        try:
            yield c
        finally:
            c.close()

    app.dependency_overrides[get_db] = override
    yield TestClient(app), ids
    services._registry.clear()


def _propose(tc, ids):
    r = tc.post("/api/trades", json={
        "league_id": ids["league"], "from_team_id": ids["a"],
        "to_team_id": ids["b"], "gives": [ids["a_bat1"]],
        "receives": [ids["b_bowl1"]]})
    assert r.status_code == 200, r.text
    return r.json()


def _list(tc, ids):
    r = tc.get("/api/trades", params={"league_id": ids["league"]})
    assert r.status_code == 200, r.text
    return {t["id"]: t for t in r.json()}


def test_counter_round_trip_and_original_untouched(client):
    tc, ids = client
    original = _propose(tc, ids)
    before = _list(tc, ids)[original["id"]]
    assert before["counter_of"] is None and before["countered_by"] == []

    r = tc.post(f"/api/trades/{original['id']}/counter", json={
        "from_team_id": ids["b"], "gives": [ids["b_bat1"]],
        "receives": [ids["a_ar1"]]})
    assert r.status_code == 200, r.text
    counter = r.json()
    assert counter["id"] != original["id"]
    assert counter["from_team_id"] == ids["b"]
    assert counter["to_team_id"] == ids["a"]
    assert counter["gives"] == [ids["b_bat1"]]
    assert counter["receives"] == [ids["a_ar1"]]
    assert counter["status"] == "proposed"
    assert counter["counter_of"] == original["id"]
    assert counter["countered_by"] == []

    after = _list(tc, ids)
    assert after[counter["id"]]["counter_of"] == original["id"]
    orig_after = after[original["id"]]
    assert orig_after.pop("countered_by") == [counter["id"]]
    before.pop("countered_by")
    assert orig_after == before  # otherwise byte-identical


def test_counter_only_by_recipient(client):
    tc, ids = client
    original = _propose(tc, ids)
    for bad_team in (ids["a"], ids["c"]):
        r = tc.post(f"/api/trades/{original['id']}/counter", json={
            "from_team_id": bad_team, "gives": [ids["b_bat1"]],
            "receives": [ids["a_ar1"]]})
        assert r.status_code == 422, (bad_team, r.text)
    assert len(_list(tc, ids)) == 1  # nothing created


def test_counter_d8_brick_rejected(client):
    tc, ids = client
    original = _propose(tc, ids)
    r = tc.post(f"/api/trades/{original['id']}/counter", json={
        "from_team_id": ids["b"],
        "gives": [ids["b_wk1"], ids["b_wk2"]],
        "receives": [ids["a_bat1"], ids["a_bat2"]]})
    assert r.status_code == 422, r.text
    assert "legal XI" in r.json()["detail"]
    assert len(_list(tc, ids)) == 1


def test_counter_non_pending_and_unknown(client):
    tc, ids = client
    original = _propose(tc, ids)
    r = tc.post(f"/api/trades/{original['id']}/reject")
    assert r.status_code == 200, r.text
    r = tc.post(f"/api/trades/{original['id']}/counter", json={
        "from_team_id": ids["b"], "gives": [ids["b_bat1"]],
        "receives": [ids["a_ar1"]]})
    assert r.status_code == 422, r.text
    r = tc.post("/api/trades/99999/counter", json={
        "from_team_id": ids["b"], "gives": [ids["b_bat1"]],
        "receives": [ids["a_ar1"]]})
    assert r.status_code == 404, r.text
