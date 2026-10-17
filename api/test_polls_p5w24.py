"""P5-W24: league polls — hand-derived fixture.

League (commissioner = user 1, who owns team C):
  teams A (user 2), B (user 3), C (user 1 = commissioner team).
  A creates "Draft day?" with options [Sat, Sun, Mon].
  Votes: A->Sat, B->Sun, C->Sat  =>  Sat 2 (66.7%), Sun 1 (33.3%),
  Mon 0 (0.0%), total 3. B changes to Sat => Sat 3 (100.0%).
  Claim gate: once A is claimed, creating/voting as A without A's
  code -> 403 (B cannot vote as A). Close: B (not creator, not
  commissioner) -> 403; C (commissioner team) closes -> votes then
  422. Polls survive a restart (second app instance, same DB file).
"""
import sqlite3
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.database import get_db
from api.routers import polls

SCHEMA = Path(__file__).resolve().parent / "schema.sql"


def _seed(con):
    for name in ("Commish", "OwnerA", "OwnerB"):
        con.execute("INSERT INTO users (name) VALUES (?)", (name,))
    league = con.execute(
        "INSERT INTO leagues (name, invite_code, commissioner_id, season, settings, status)"
        " VALUES ('w24-league','CODE-w24',1,'2027','{}','setup')").lastrowid
    teams = {}
    for label, owner in (("A", 2), ("B", 3), ("C", 1)):
        teams[label] = con.execute(
            "INSERT INTO teams (league_id, owner_id, name, faab_remaining)"
            " VALUES (?,?,?,100)", (league, owner, f"w24-{label}")).lastrowid
    con.commit()
    return league, teams


def _app(db_path):
    app = FastAPI()
    app.include_router(polls.router, prefix="/api/leagues")

    def override():
        c = sqlite3.connect(str(db_path)); c.row_factory = sqlite3.Row
        try: yield c
        finally: c.close()
    app.dependency_overrides[get_db] = override
    return TestClient(app)


@pytest.fixture()
def ctx(tmp_path):
    db_path = tmp_path / "w24.db"
    con = sqlite3.connect(str(db_path)); con.row_factory = sqlite3.Row
    con.executescript(SCHEMA.read_text())
    league, teams = _seed(con)
    con.close()
    return _app(db_path), league, teams, db_path


def _create(tc, league, team, **kw):
    r = tc.post(f"/api/leagues/{league}/polls",
                json={"team_id": team, "question": "Draft day?",
                      "options": ["Sat", "Sun", "Mon"]}, **kw)
    assert r.status_code == 201, r.text
    return r.json()


def _vote(tc, league, poll_id, team, option_id, **kw):
    return tc.post(f"/api/leagues/{league}/polls/{poll_id}/vote",
                   json={"team_id": team, "option_id": option_id}, **kw)


def test_create_vote_percentages_and_change(ctx):
    tc, league, teams, _ = ctx
    poll = _create(tc, league, teams["A"])
    assert poll["closed"] is False and poll["total_votes"] == 0
    assert [o["label"] for o in poll["options"]] == ["Sat", "Sun", "Mon"]
    sat, sun, mon = (o["id"] for o in poll["options"])

    assert _vote(tc, league, poll["id"], teams["A"], sat).status_code == 200
    assert _vote(tc, league, poll["id"], teams["B"], sun).status_code == 200
    r = _vote(tc, league, poll["id"], teams["C"], sat)
    body = r.json()
    assert body["total_votes"] == 3
    got = {o["label"]: (o["votes"], o["pct"]) for o in body["options"]}
    assert got == {"Sat": (2, 66.7), "Sun": (1, 33.3), "Mon": (0, 0.0)}
    assert body["my_option_id"] == sat  # viewer is C, who voted Sat

    # B changes its vote: still ONE vote for B, now on Sat.
    r = _vote(tc, league, poll["id"], teams["B"], sat)
    body = r.json()
    assert body["total_votes"] == 3
    got = {o["label"]: (o["votes"], o["pct"]) for o in body["options"]}
    assert got["Sat"] == (3, 100.0) and got["Sun"] == (0, 0.0)

    listed = tc.get(f"/api/leagues/{league}/polls",
                    params={"team_id": teams["B"]}).json()
    assert listed["total"] == 1
    assert listed["polls"][0]["my_option_id"] == sat
    assert listed["commissioner_team_id"] == teams["C"]


def test_create_validation(ctx):
    tc, league, teams, _ = ctx
    base = f"/api/leagues/{league}/polls"
    r = tc.post(base, json={"team_id": teams["A"], "question": "Q?",
                            "options": ["only"]})
    assert r.status_code == 422  # fewer than 2 options (schema)
    r = tc.post(base, json={"team_id": teams["A"], "question": "Q?",
                            "options": ["x", " x ", ""]})
    assert r.status_code == 422  # dedupes/trims to a single option
    r = tc.post(base, json={"team_id": teams["A"], "question": "  ",
                            "options": ["a", "b"]})
    assert r.status_code == 422  # empty question after trim
    r = tc.post("/api/leagues/99999/polls",
                json={"team_id": teams["A"], "question": "Q?",
                      "options": ["a", "b"]})
    assert r.status_code == 404


def test_claim_gate_and_close_rules(ctx):
    tc, league, teams, db_path = ctx
    con = sqlite3.connect(str(db_path))
    con.execute("UPDATE teams SET claim_code = 'SECRET1234' WHERE id = ?",
                (teams["A"],))
    con.commit(); con.close()

    # A is claimed: creating as A without the code 403s...
    r = tc.post(f"/api/leagues/{league}/polls",
                json={"team_id": teams["A"], "question": "Draft day?",
                      "options": ["Sat", "Sun"]})
    assert r.status_code == 403
    # ...and B cannot create/vote as A either (no code) — with the
    # code, A creates fine.
    poll = _create(tc, league, teams["A"],
                   headers={"X-Team-Claim": "SECRET1234"})
    sat = poll["options"][0]["id"]
    r = _vote(tc, league, poll["id"], teams["A"], sat)
    assert r.status_code == 403  # B-as-A attempt shape: no header
    r = _vote(tc, league, poll["id"], teams["A"], sat,
              headers={"X-Team-Claim": "SECRET1234"})
    assert r.status_code == 200

    # Close: B is neither creator nor commissioner -> 403.
    r = tc.post(f"/api/leagues/{league}/polls/{poll['id']}/close",
                params={"team_id": teams["B"]})
    assert r.status_code == 403
    # Commissioner team C closes it.
    r = tc.post(f"/api/leagues/{league}/polls/{poll['id']}/close",
                params={"team_id": teams["C"]})
    assert r.status_code == 200 and r.json()["closed"] is True
    # Closed polls reject votes.
    r = _vote(tc, league, poll["id"], teams["B"], sat)
    assert r.status_code == 422
    # Closing again is an idempotent no-op.
    r = tc.post(f"/api/leagues/{league}/polls/{poll['id']}/close",
                params={"team_id": teams["C"]})
    assert r.status_code == 200 and r.json()["closed"] is True


def test_persistence_across_restart(ctx):
    tc, league, teams, db_path = ctx
    poll = _create(tc, league, teams["B"])
    sat = poll["options"][0]["id"]
    assert _vote(tc, league, poll["id"], teams["B"], sat).status_code == 200
    tc2 = _app(db_path)  # fresh app instance over the same DB file
    listed = tc2.get(f"/api/leagues/{league}/polls").json()
    assert listed["total"] == 1
    assert listed["polls"][0]["question"] == "Draft day?"
    assert listed["polls"][0]["total_votes"] == 1
