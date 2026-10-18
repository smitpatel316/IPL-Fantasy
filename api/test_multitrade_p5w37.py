"""P5-W37: multi-team trades — hand-derived fixture.

Four teams A/B/C/D, each with a fieldable 14-man domestic roster
(WK2 BAT4 AR3 BOWL5). Deal legs are directed: {giver_id, receiver_id,
player_ids}; the first leg's giver is the proposer and counts as
accepted.

  * 3-team cyclic deal (A->B bat1, B->C bowl1, C->A ar1) round-trips
    through the API: proposed (accepts=[A]) -> B accepts -> C accepts
    -> under_review with a review deadline -> (review window forced
    shut) -> executed, and the roster swap is verified in roster_slots.
    Deal rows never leak into the 2-team GET /api/trades list.
  * A single reject by any party dissolves the whole deal (rejected);
    a later accept 422s.
  * A leg that would leave a team unable to field a D8-legal XI
    (B gives both WKs) 422s at proposal time and creates no deal row.
  * A leg set that breaks per-team roster-count invariance
    (A gives 2, receives 1) 422s.
  * Party guards: a non-party team cannot accept (422); a team cannot
    accept twice (422); only the proposer can withdraw (422 for anyone
    else); the proposer withdrawing dissolves the whole deal; an
    unknown deal id 404s; a party team cannot veto (422).
  * A non-party team (D) vetoing a 3-team deal in a 4-team league hits
    the one-third threshold (ceil((4-2)/3) = 1) and vetoes the deal.
"""

import sqlite3
import time
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
    con.execute("INSERT INTO users (name) VALUES ('w37-owner')")
    league = con.execute(
        "INSERT INTO leagues (name, invite_code, commissioner_id,"
        " season, settings, status) VALUES ('w37-league', 'CODE-w37',"
        " 1, '2027', '{}', 'in_season')").lastrowid
    ids = {"league": league}
    for label in "ABCD":
        tid = con.execute(
            "INSERT INTO teams (league_id, owner_id, name,"
            " faab_remaining) VALUES (?, 1, ?, 100)",
            (league, f"w37-{label}")).lastrowid
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
    db_path = tmp_path / "multitrade.db"
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA.read_text())
    ids = _seed(con)
    con.close()
    ids["db_path"] = str(db_path)
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


def _connect(ids):
    con = sqlite3.connect(ids["db_path"])
    con.row_factory = sqlite3.Row
    return con


def _roster_pids(ids, team_id):
    con = _connect(ids)
    try:
        return {r["player_id"] for r in con.execute(
            "SELECT player_id FROM roster_slots WHERE team_id = ?"
            " AND week_no IS NULL", (team_id,))}
    finally:
        con.close()


def _deal_count(ids):
    con = _connect(ids)
    try:
        cols = {r["name"] for r in con.execute("PRAGMA table_info(trades)")}
        if "kind" not in cols:
            return 0
        return con.execute(
            "SELECT COUNT(*) FROM trades WHERE league_id = ? AND kind = 'deal'",
            (ids["league"],)).fetchone()[0]
    finally:
        con.close()


def _propose_cyclic(tc, ids):
    r = tc.post("/api/trades/deal", json={
        "league_id": ids["league"],
        "legs": [
            {"giver_id": ids["a"], "receiver_id": ids["b"],
             "player_ids": [ids["a_bat1"]]},
            {"giver_id": ids["b"], "receiver_id": ids["c"],
             "player_ids": [ids["b_bowl1"]]},
            {"giver_id": ids["c"], "receiver_id": ids["a"],
             "player_ids": [ids["c_ar1"]]},
        ]})
    assert r.status_code == 200, r.text
    return r.json()


def _accept(tc, deal_id, team_id):
    return tc.post(f"/api/trades/deal/{deal_id}/accept",
                   json={"team_id": team_id})


def _force_review_closed(ids, deal_db_id):
    """Shut the deal's 2-day review window on the cached engine so the
    next API read/write settles (executes) it — the test stand-in for
    waiting out the window."""
    eng = services._registry[("trade", ids["league"])]
    con = _connect(ids)
    try:
        eid = con.execute("SELECT engine_id FROM trades WHERE id = ?",
                          (deal_db_id,)).fetchone()["engine_id"]
    finally:
        con.close()
    eng._deals[eid]["review_until"] = time.time() - 1


def test_deal_round_trip_3team_cyclic_executes(client):
    tc, ids = client
    deal = _propose_cyclic(tc, ids)
    assert deal["status"] == "proposed"
    assert deal["proposer"] == ids["a"]
    assert deal["parties"] == sorted([ids["a"], ids["b"], ids["c"]])
    assert deal["accepts"] == [ids["a"]]  # proposer counts as accepted
    assert deal["review_deadline"] is None
    assert [l["player_ids"] for l in deal["legs"]] == [
        [ids["a_bat1"]], [ids["b_bowl1"]], [ids["c_ar1"]]]
    assert deal["veto_count"] == 0 and deal["executed_at"] is None

    # Deals never leak into the 2-team trade list.
    r = tc.get("/api/trades", params={"league_id": ids["league"]})
    assert r.status_code == 200, r.text
    assert r.json() == []

    r = _accept(tc, deal["id"], ids["b"])
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["status"] == "proposed"
    assert sorted(d["accepts"]) == sorted([ids["a"], ids["b"]])

    r = _accept(tc, deal["id"], ids["c"])
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["status"] == "accepted"  # under_review projects to accepted
    assert d["review_deadline"] is not None
    assert d["accepted_at"] is not None

    _force_review_closed(ids, deal["id"])
    r = tc.get("/api/trades/deals", params={"league_id": ids["league"]})
    assert r.status_code == 200, r.text
    done = {x["id"]: x for x in r.json()}[deal["id"]]
    assert done["status"] == "accepted"  # executed projects to accepted
    assert done["executed_at"] is not None

    # The 3-way roster swap actually happened.
    ra, rb, rc = (_roster_pids(ids, ids[t]) for t in "abc")
    assert ids["c_ar1"] in ra and ids["a_bat1"] not in ra
    assert ids["a_bat1"] in rb and ids["b_bowl1"] not in rb
    assert ids["b_bowl1"] in rc and ids["c_ar1"] not in rc
    assert len(ra) == len(rb) == len(rc) == 14  # counts invariant


def test_single_reject_dissolves_whole_deal(client):
    tc, ids = client
    deal = _propose_cyclic(tc, ids)
    r = _accept(tc, deal["id"], ids["b"])
    assert r.status_code == 200, r.text

    r = tc.post(f"/api/trades/deal/{deal['id']}/reject",
                json={"team_id": ids["c"]})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "rejected"

    # The whole deal is terminal: no further accepts.
    r = _accept(tc, deal["id"], ids["c"])
    assert r.status_code == 422, r.text
    r = tc.get(f"/api/trades/deal/{deal['id']}")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "rejected"


def test_d8_bricking_leg_rejected_422(client):
    tc, ids = client
    # B gives away both WKs for two BATs: B can no longer field a
    # D8-legal XI (P4-W24 guard, applied to every participating team).
    r = tc.post("/api/trades/deal", json={
        "league_id": ids["league"],
        "legs": [
            {"giver_id": ids["a"], "receiver_id": ids["b"],
             "player_ids": [ids["a_bat1"], ids["a_bat2"]]},
            {"giver_id": ids["b"], "receiver_id": ids["a"],
             "player_ids": [ids["b_wk1"], ids["b_wk2"]]},
        ]})
    assert r.status_code == 422, r.text
    assert "legal XI" in r.json()["detail"]
    assert _deal_count(ids) == 0  # nothing persisted


def test_unbalanced_deal_rejected_422(client):
    tc, ids = client
    # A gives 1 but receives 2: per-team roster-count invariance.
    # (Both post-swap rosters stay D8-fieldable, so the failure is the
    # invariance check, not the D8 guard.)
    r = tc.post("/api/trades/deal", json={
        "league_id": ids["league"],
        "legs": [
            {"giver_id": ids["a"], "receiver_id": ids["b"],
             "player_ids": [ids["a_bat1"]]},
            {"giver_id": ids["b"], "receiver_id": ids["a"],
             "player_ids": [ids["b_bowl1"], ids["b_bowl2"]]},
        ]})
    assert r.status_code == 422, r.text
    assert "invariance" in r.json()["detail"]
    assert _deal_count(ids) == 0


def test_deal_party_guards(client):
    tc, ids = client
    deal = _propose_cyclic(tc, ids)

    # D is not a party: cannot accept.
    r = _accept(tc, deal["id"], ids["d"])
    assert r.status_code == 422, r.text

    r = _accept(tc, deal["id"], ids["b"])
    assert r.status_code == 200, r.text
    # B cannot accept twice.
    r = _accept(tc, deal["id"], ids["b"])
    assert r.status_code == 422, r.text

    # Only the proposer (A) may withdraw; B's attempt 422s.
    r = tc.post(f"/api/trades/deal/{deal['id']}/withdraw",
                json={"team_id": ids["b"]})
    assert r.status_code == 422, r.text
    r = tc.post(f"/api/trades/deal/{deal['id']}/withdraw",
                json={"team_id": ids["a"]})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "rejected"  # withdrawn projects to rejected

    # Unknown deal 404s on every deal endpoint.
    for method, url, kwargs in [
            ("post", "/api/trades/deal/99999/accept", {"json": {"team_id": ids["a"]}}),
            ("post", "/api/trades/deal/99999/reject", {"json": {"team_id": ids["a"]}}),
            ("get", "/api/trades/deal/99999", {}),
            ("post", "/api/trades/deal/99999/veto", {}),
    ]:
        r = tc.request(method, url, params={"team_id": ids["d"]}, **kwargs)
        assert r.status_code == 404, (method, url, r.text)

    # A 2-team trade id is not a deal.
    r = tc.post("/api/trades", json={
        "league_id": ids["league"], "from_team_id": ids["a"],
        "to_team_id": ids["b"], "gives": [ids["a_bat1"]],
        "receives": [ids["b_bowl1"]]})
    assert r.status_code == 200, r.text
    trade_id = r.json()["id"]
    r = _accept(tc, trade_id, ids["b"])
    assert r.status_code == 404, r.text


def test_deal_veto_by_nonparty(client):
    tc, ids = client
    deal = _propose_cyclic(tc, ids)
    assert _accept(tc, deal["id"], ids["b"]).status_code == 200
    assert _accept(tc, deal["id"], ids["c"]).status_code == 200

    # A party team may not veto its own deal.
    r = tc.post(f"/api/trades/deal/{deal['id']}/veto",
                params={"team_id": ids["a"]})
    assert r.status_code == 422, r.text

    # D is not a party: one veto hits the one-third threshold in a
    # 4-team league (ceil((4-2)/3) = 1) and vetoes the whole deal.
    r = tc.post(f"/api/trades/deal/{deal['id']}/veto",
                params={"team_id": ids["d"]})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["status"] == "vetoed"
    assert d["veto_count"] == 1
    assert d["vetoed_at"] is not None
