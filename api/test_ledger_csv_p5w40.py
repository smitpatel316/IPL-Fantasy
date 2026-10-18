"""P5-W40: ledger CSV export — hand-derived.

Same scratch-league shape as the P5-W28 ledger test, plus a
commissioner roster fiat and an executed trade so the CSV's player
column is exercised across every entry kind:

  Team A: starting_balance, won P1 ($17), lost claim on P2,
  commissioner FAAB +10, commissioner roster_add P4,
  pending claim on P3 (sealed $99), executed trade with B
  (gave P5, received P6).

Checks: 200 + text/csv content-type + attachment disposition with the
team in the filename, valid CSV with the expected header, row count
matching the JSON endpoint, and per-row parity (timestamp, team, type,
player, faab_delta, note). The claim gate behaves like the JSON
endpoint: claimed teams 403 without their code.
"""

import csv
import io
import json
import sqlite3
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.database import get_db
from api.routers import ledger

SCHEMA = Path(__file__).resolve().parent / "schema.sql"
HEADER = ["timestamp", "team", "type", "player", "faab_delta", "note"]


def _seed(con):
    con.execute("INSERT INTO users (name) VALUES ('w40-owner')")
    league = con.execute(
        "INSERT INTO leagues (name, invite_code, commissioner_id,"
        " season, settings, status) VALUES ('w40', 'CODE-w40', 1,"
        " '2027', '{}', 'in_season')").lastrowid
    teams = {}
    for name in ("A", "B"):
        teams[name] = con.execute(
            "INSERT INTO teams (league_id, name, owner_id, faab_remaining)"
            " VALUES (?, ?, 1, 93)", (league, name)).lastrowid
    players = {}
    for name in ("P1", "P2", "P3", "P4", "P5", "P6"):
        players[name] = con.execute(
            "INSERT INTO players (name, season) VALUES (?, '2027')",
            (name,)).lastrowid
    a = teams["A"]
    for status, pid, bid, ts in [
            ("won", players["P1"], 17, "2027-03-10T00:00:00"),
            ("lost", players["P2"], 30, "2027-03-11T00:00:00"),
            ("pending", players["P3"], 99, "2027-03-12T00:00:00")]:
        con.execute(
            "INSERT INTO waiver_claims (league_id, team_id, week_no,"
            " add_player_id, bid, status, created_at) VALUES (?, ?, 1,"
            " ?, ?, ?, ?)", (league, a, pid, bid, status, ts))
    con.execute(
        "INSERT INTO league_adjustments (league_id, team_id, kind,"
        " faab_delta, faab_after, note, created_at) VALUES (?, ?, 'faab',"
        " 10, 93, 'goodwill', '2027-03-11T12:00:00')", (league, a))
    con.execute(
        "INSERT INTO league_adjustments (league_id, team_id, kind,"
        " faab_delta, faab_after, player_name, note, created_at)"
        " VALUES (?, ?, 'roster_add', 0, 93, 'P4', 'fiat add',"
        " '2027-03-12T08:00:00')", (league, a))
    con.execute(
        "INSERT INTO trades (league_id, from_team_id, to_team_id, gives,"
        " receives, status, created_at, executed_at) VALUES (?, ?, ?,"
        " ?, ?, 'executed', '2027-03-13T00:00:00', '2027-03-13T01:00:00')",
        (league, a, teams["B"],
         json.dumps([players["P5"]]), json.dumps([players["P6"]])))
    con.commit()
    return {"league": league, "teams": teams}


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / "ledger_csv.db"
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA.read_text())
    ids = _seed(con)
    con.close()
    app = FastAPI()
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


def _rows(r):
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("text/csv")
    disp = r.headers["content-disposition"]
    assert "attachment" in disp and "ledger-team-" in disp
    rows = list(csv.reader(io.StringIO(r.text)))
    assert rows[0] == HEADER
    return rows[1:]


def test_csv_parity_with_json_endpoint(client):
    tc, ids, _ = client
    lid, a = ids["league"], ids["teams"]["A"]
    body = tc.get(f"/api/leagues/{lid}/teams/{a}/ledger").json()
    rows = _rows(tc.get(f"/api/leagues/{lid}/teams/{a}/ledger.csv"))
    assert len(rows) == len(body["entries"]), (
        len(rows), len(body["entries"]))
    entries = {e["id"]: e for e in body["entries"]}
    by_id = {}
    for ts, team, typ, player, delta, note in rows:
        assert team == "A"
        assert ts and typ and note
        int(delta)
    for e in body["entries"]:
        by_id.setdefault(e["kind"], []).append(e)
    kinds = [r[2] for r in rows]
    assert sorted(kinds) == sorted(e["kind"] for e in body["entries"])
    # timestamp / type / faab_delta / note mirror the JSON rows
    want = {(e["occurred_at"], e["kind"], e["faab_delta"], e["text"])
            for e in body["entries"]}
    got = {(r[0], r[2], int(r[4]), r[5]) for r in rows}
    assert got == want
    # player column names the player each entry is about
    players_by_kind = {r[2]: r[3] for r in rows}
    assert players_by_kind["waiver_won"] == "P1"
    assert players_by_kind["waiver_lost"] == "P2"
    assert players_by_kind["waiver_pending"] == "P3"
    assert players_by_kind["commissioner_roster_add"] == "P4"
    assert players_by_kind["commissioner_faab"] == ""
    assert players_by_kind["starting_balance"] == ""
    assert players_by_kind["trade_executed"] == "P5, P6"


def test_csv_claim_gate(client):
    tc, ids, db_path = client
    lid, a = ids["league"], ids["teams"]["A"]
    url = f"/api/leagues/{lid}/teams/{a}/ledger.csv"
    assert tc.get(url).status_code == 200
    con = sqlite3.connect(str(db_path))
    con.execute("UPDATE teams SET claim_code = 'sekret' WHERE id = ?", (a,))
    con.commit()
    con.close()
    assert tc.get(url).status_code == 403
    assert tc.get(url, headers={"X-Team-Claim": "wrong"}).status_code == 403
    r = tc.get(url, headers={"X-Team-Claim": "sekret"})
    assert r.status_code == 200
    assert len(list(csv.reader(io.StringIO(r.text)))) > 1
    assert tc.get("/api/leagues/99999/teams/1/ledger.csv").status_code == 404
