"""P5-W18: trade finder — hand-derived surplus/deficit fixture.

Needs (D7): WK1 BAT3 AR2 BOWL3. Short = count <= need; deep = count
>= need + 2; surplus = players beyond the best `need` by rank.

  Team A (requester): BOWL ranks 10/20/30/40/50 (deep; surplus best =
    rank 40), BAT 15/25 (short), WK rank 5 (short), AR 12/22/32
    (neither).
  Team B: BAT 5/11/21/31/41 (deep; surplus best = rank 31, and that
    player is on B's trade block), BOWL 18/28 (short), WK x2, AR x3.
  Team C: WK 8/26/48 (deep; surplus best = rank 26), BOWL 16/36
    (short), BAT x4, AR x2 (short, but A is not deep at AR).

Matches for A:
  B — A deep BOWL x B short BOWL; B deep BAT x A short BAT.
      give A-BOWL-40, receive B-BAT-31, boosted (trade block).
      combined rank 71.
  C — A deep BOWL x C short BOWL; C deep WK x A short WK.
      give A-BOWL-40, receive C-WK-26, not boosted. combined 66.
Boost sorts before combined rank, so the order is [B, C] even though
C's combined rank is lower — the boost is doing the ordering.
Can't-cut variant: with A-BOWL-40 on the can't-cut list, A's give
piece in both suggestions becomes A-BOWL-50.
"""

import json
import sqlite3
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.database import get_db
from api.routers import trades

SCHEMA = Path(__file__).resolve().parent / "schema.sql"


def _player(con, name, role, rank, rank_team, team=None):
    pid = con.execute(
        "INSERT INTO players (name, season) VALUES (?, '2027')",
        (name,)).lastrowid
    con.execute(
        "INSERT INTO player_roles (player_id, season, role, is_overseas,"
        " ipl_team_code) VALUES (?, '2027', ?, 0, 'MI')", (pid, role))
    con.execute(
        "INSERT INTO pre_draft_ranks (team_id, player_id, rank)"
        " VALUES (?, ?, ?)", (rank_team, pid, rank))
    if team is not None:
        con.execute(
            "INSERT INTO roster_slots (team_id, player_id, slot)"
            " VALUES (?, ?, 'BN')", (team, pid))
    return pid


def _seed(con):
    con.execute("INSERT INTO users (name) VALUES ('w18-owner')")
    league = con.execute(
        "INSERT INTO leagues (name, invite_code, commissioner_id,"
        " season, settings, status) VALUES ('w18-league', 'CODE-w18',"
        " 1, '2027', '{}', 'in_season')").lastrowid

    def team(name):
        return con.execute(
            "INSERT INTO teams (league_id, owner_id, name,"
            " faab_remaining) VALUES (?, 1, ?, 100)",
            (league, name)).lastrowid

    a, b, c = team("w18-A"), team("w18-B"), team("w18-C")
    ids = {"league": league, "a": a, "b": b, "c": c}
    for rank in (10, 20, 30, 40, 50):
        pid = _player(con, f"A-BOWL-{rank}", "BOWL", rank, a, a)
        if rank == 40:
            ids["a_bowl40"] = pid
        if rank == 50:
            ids["a_bowl50"] = pid
    for rank in (15, 25):
        _player(con, f"A-BAT-{rank}", "BAT", rank, a, a)
    _player(con, "A-WK-5", "WK", 5, a, a)
    for rank in (12, 22, 32):
        _player(con, f"A-AR-{rank}", "AR", rank, a, a)
    for rank in (5, 11, 21, 31, 41):
        pid = _player(con, f"B-BAT-{rank}", "BAT", rank, a, b)
        if rank == 31:
            ids["b_bat31"] = pid
    for rank in (18, 28):
        _player(con, f"B-BOWL-{rank}", "BOWL", rank, a, b)
    for rank in (33, 43):
        _player(con, f"B-WK-{rank}", "WK", rank, a, b)
    for rank in (34, 44, 54):
        _player(con, f"B-AR-{rank}", "AR", rank, a, b)
    for rank in (8, 26, 48):
        pid = _player(con, f"C-WK-{rank}", "WK", rank, a, c)
        if rank == 26:
            ids["c_wk26"] = pid
    for rank in (16, 36):
        _player(con, f"C-BOWL-{rank}", "BOWL", rank, a, c)
    for rank in (17, 27, 37, 47):
        _player(con, f"C-BAT-{rank}", "BAT", rank, a, c)
    for rank in (19, 29):
        _player(con, f"C-AR-{rank}", "AR", rank, a, c)
    # B lists its surplus BAT on the trade block.
    con.execute(
        "INSERT INTO trade_block (league_id, team_id, player_id,"
        " seeking) VALUES (?, ?, ?, 'want a BOWL')",
        (league, b, ids["b_bat31"]))
    con.commit()
    return ids


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / "finder.db"
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
    return TestClient(app), ids, db_path


def test_finder_hand_derived_matches(client):
    tc, ids, _ = client
    r = tc.get("/api/trades/finder",
               params={"league_id": ids["league"], "team_id": ids["a"]})
    assert r.status_code == 200, r.text
    s = r.json()["suggestions"]
    assert [x["partner_team_id"] for x in s] == [ids["b"], ids["c"]]
    sb, sc = s
    assert sb["give"]["player_id"] == ids["a_bowl40"]
    assert sb["receive"]["player_id"] == ids["b_bat31"]
    assert sb["give_role"] == "BOWL" and sb["receive_role"] == "BAT"
    assert sb["on_trade_block"] is True
    assert "short a BOWL" in sb["reason"]
    assert "on their trade block" in sb["reason"]
    assert sc["give"]["player_id"] == ids["a_bowl40"]
    assert sc["receive"]["player_id"] == ids["c_wk26"]
    assert sc["receive_role"] == "WK" and sc["on_trade_block"] is False


def test_finder_never_names_cant_cut_as_give(client):
    tc, ids, db_path = client
    con = sqlite3.connect(str(db_path))
    con.execute(
        "UPDATE leagues SET settings = ? WHERE id = ?",
        (json.dumps({"cant_cut_player_ids": [ids["a_bowl40"]]}),
         ids["league"]))
    con.commit()
    con.close()
    r = tc.get("/api/trades/finder",
               params={"league_id": ids["league"], "team_id": ids["a"]})
    assert r.status_code == 200, r.text
    s = r.json()["suggestions"]
    assert len(s) == 2
    assert all(x["give"]["player_id"] == ids["a_bowl50"] for x in s)


def test_finder_empty_and_validation(client):
    tc, ids, _ = client
    # Team C has no complementary partner among A/B for its own needs
    # beyond what A offers at BOWL... C IS short BOWL and A is deep —
    # but a match also needs C deep at an A-short role: C is deep at
    # WK and A is short WK, so C sees A. Instead verify from B's seat:
    # B is short BOWL, A is deep BOWL; A is short BAT, B is deep BAT
    # -> B sees exactly A.
    r = tc.get("/api/trades/finder",
               params={"league_id": ids["league"], "team_id": ids["b"]})
    assert [x["partner_team_id"] for x in r.json()["suggestions"]] == [
        ids["a"]]
    assert tc.get("/api/trades/finder",
                  params={"league_id": 99999, "team_id": ids["a"]}
                  ).status_code == 404
    assert tc.get("/api/trades/finder",
                  params={"league_id": ids["league"], "team_id": 99999}
                  ).status_code == 404
