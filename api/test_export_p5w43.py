"""P5-W43: commissioner full-league export — hand-derived.

Scratch league with 2 teams (A = commissioner's claimed team, B = claimed
rival), a completed mini-draft, rosters, an executed 2-team trade, a won
waiver claim, a poll with a vote, and a pinned message.

Checks: commissioner 200 + JSON re-parses with all 8 teams/rosters present
(both teams + their rosters), draft picks, trades (legs JSON parsed),
waiver claims, polls, messages, per-team ledger rows; no claim_code leaks
anywhere in the payload; non-commissioner team 403s; commissioner without
their claim header 403s; missing team_id 422s.
"""

import json
import sqlite3
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.database import get_db
from api.routers import export

SCHEMA = Path(__file__).resolve().parent / "schema.sql"


@pytest.fixture
def db_path(tmp_path):
    p = tmp_path / "w43.db"
    c = sqlite3.connect(str(p))
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA.read_text())
    c.execute("PRAGMA foreign_keys = ON")
    c.close()
    return p


def _seed(con):
    con.execute("INSERT INTO users (name) VALUES ('commish')")
    league = con.execute(
        "INSERT INTO leagues (name, invite_code, commissioner_id,"
        " season, settings, status) VALUES ('w43', 'CODE-w43', 1,"
        " '2027', '{\"faab_budget\": 100}', 'in_season')").lastrowid
    a = con.execute(
        "INSERT INTO teams (league_id, name, owner_id, faab_remaining,"
        " claim_code) VALUES (?, 'A', 1, 93, 'COMMISH')",
        (league,)).lastrowid
    b = con.execute(
        "INSERT INTO teams (league_id, name, owner_id, faab_remaining,"
        " claim_code) VALUES (?, 'B', 1, 100, 'RIVAL')",
        (league,)).lastrowid
    p = {}
    for name in ("P1", "P2", "P3", "P4"):
        p[name] = con.execute(
            "INSERT INTO players (name, season) VALUES (?, '2027')",
            (name,)).lastrowid
    # rosters (week_no NULL = construction roster)
    con.execute("INSERT INTO roster_slots (team_id, player_id, slot, week_no)"
                " VALUES (?, ?, 'BAT', NULL)", (a, p["P1"]))
    con.execute("INSERT INTO roster_slots (team_id, player_id, slot, week_no)"
                " VALUES (?, ?, 'BOWL', NULL)", (b, p["P2"]))
    # draft: 1 round, 2 picks
    d = con.execute(
        "INSERT INTO drafts (league_id, draft_order, rounds, status,"
        " current_pick_no) VALUES (?, ?, 1, 'complete', 2)",
        (league, json.dumps([a, b]))).lastrowid
    con.execute("INSERT INTO draft_picks (draft_id, pick_no, round_no,"
                " team_id, player_id, is_auto) VALUES (?, 1, 1, ?, ?, 0)",
                (d, a, p["P1"]))
    con.execute("INSERT INTO draft_picks (draft_id, pick_no, round_no,"
                " team_id, player_id, is_auto) VALUES (?, 2, 1, ?, ?, 0)",
                (d, b, p["P2"]))
    # executed 2-team trade A<->B
    con.execute(
        "INSERT INTO trades (league_id, from_team_id, to_team_id, gives,"
        " receives, status, executed_at, kind)"
        " VALUES (?, ?, ?, ?, ?, 'executed', '2027-03-11T00:00:00', 'trade')",
        (league, a, b, json.dumps([p["P1"]]), json.dumps([p["P2"]])))
    # won waiver claim for A
    con.execute(
        "INSERT INTO waiver_claims (league_id, week_no, team_id,"
        " add_player_id, bid, status) VALUES (?, 1, ?, ?, 17, 'won')",
        (league, a, p["P3"]))
    # poll + vote
    poll = con.execute(
        "INSERT INTO polls (league_id, team_id, question)"
        " VALUES (?, ?, 'Keep FAAB at 100?')", (league, a)).lastrowid
    opt = con.execute(
        "INSERT INTO poll_options (poll_id, label, position)"
        " VALUES (?, 'Yes', 0)", (poll,)).lastrowid
    con.execute(
        "INSERT INTO poll_votes (poll_id, team_id, option_id)"
        " VALUES (?, ?, ?)", (poll, b, opt))
    # pinned message from the commissioner team
    con.execute(
        "INSERT INTO league_messages (league_id, team_id, body, pinned_at)"
        " VALUES (?, ?, 'Draft is Sunday', '2027-03-10T00:00:00')",
        (league, a))
    con.commit()
    return {"league": league, "a": a, "b": b, "players": p}


@pytest.fixture
def client(db_path):
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    ids = _seed(con)
    con.close()

    app = FastAPI()
    app.include_router(export.router, prefix="/api/leagues")

    def override():
        c = sqlite3.connect(str(db_path))
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys = ON")
        try:
            yield c
        finally:
            c.close()

    app.dependency_overrides[get_db] = override
    cli = TestClient(app)
    cli.seeds = ids
    return cli


def test_commissioner_export_round_trips(client):
    s = client.seeds
    r = client.get(f"/api/leagues/{s['league']}/export.json",
                   params={"team_id": s["a"]},
                   headers={"X-Team-Claim": "COMMISH"})
    assert r.status_code == 200, r.text
    body = json.loads(r.text)  # re-parses
    assert body["exported_by_team_id"] == s["a"]
    assert body["league"]["name"] == "w43"
    assert body["league"]["settings"] == {"faab_budget": 100}
    teams = {t["name"]: t for t in body["teams"]}
    assert set(teams) == {"A", "B"}
    assert teams["A"]["claimed"] is True
    assert "claim_code" not in json.dumps(body)  # no claim codes leak
    # rosters: both teams present, names resolved
    assert len(body["rosters"][str(s["a"])]) == 1
    assert body["rosters"][str(s["a"])][0]["player_name"] == "P1"
    assert body["rosters"][str(s["b"])][0]["player_name"] == "P2"
    # draft picks
    assert body["draft"]["rounds"] == 1
    picks = body["draft"]["picks"]
    assert len(picks) == 2
    assert [x["player_name"] for x in picks] == ["P1", "P2"]
    assert picks[0]["pick_no"] == 1 and picks[1]["pick_no"] == 2
    # trades: legs JSON parsed (None for 2-team trade)
    assert len(body["trades"]) == 1
    assert body["trades"][0]["kind"] == "trade"
    assert body["trades"][0]["legs"] is None
    assert body["trades"][0]["gives"] == [s["players"]["P1"]]
    # waiver history, polls, messages
    assert len(body["waiver_claims"]) == 1
    assert body["waiver_claims"][0]["status"] == "won"
    assert len(body["polls"]) == 1
    assert body["polls"][0]["options"][0]["label"] == "Yes"
    assert len(body["polls"][0]["votes"]) == 1
    assert len(body["messages"]) == 1
    assert body["messages"][0]["pinned_at"] is not None
    # ledger: per-team raw rows
    assert set(body["ledger"]) == {str(s["a"]), str(s["b"])}
    assert any(e["kind"] == "waiver_won" for e in body["ledger"][str(s["a"])])


def test_non_commissioner_forbidden(client):
    s = client.seeds
    r = client.get(f"/api/leagues/{s['league']}/export.json",
                   params={"team_id": s["b"]},
                   headers={"X-Team-Claim": "RIVAL"})
    assert r.status_code == 403


def test_commissioner_without_claim_header_forbidden(client):
    s = client.seeds
    r = client.get(f"/api/leagues/{s['league']}/export.json",
                   params={"team_id": s["a"]})
    assert r.status_code == 403


def test_missing_team_id_rejected(client):
    s = client.seeds
    r = client.get(f"/api/leagues/{s['league']}/export.json")
    assert r.status_code == 422
