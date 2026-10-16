"""P5-W16: waiver-wire recommendations — hand-derived fixture.

Consensus ranks (seeded as team T's pre_draft_ranks; MIN is league-wide):
  Team T (15-man): WK 30/95, BAT 40/50/60/80/100, AR 45/55/85,
                   BOWL 35/65/70/90/110.
  The rank-110 BOWL is on the league's custom can't-cut list, so the
  weakest *droppable* BOWL is rank 90.
  Free agents: fa_bat (BAT, MI) rank 20 -> upgrade 100-20 = 80
               fa_bowl (BOWL, CSK) rank 25 -> upgrade 90-25 = 65
               fa_wk (WK, MI) rank 28 -> upgrade 95-28 = 67
               fa_bad (BAT) rank 105 -> upgrade < 0, excluded
               fa_owned (BAT) rank 10 -> rostered by team U, excluded
  Schedule weeks 1-3: MI plays 2+2+2 = 6, CSK has no rows (= 0).
  score = upgrade + games -> bat 86, wk 73, bowl 65. Final order is
  [fa_bat, fa_wk, fa_bowl]: raw upgrade alone would tie fa_bat's
  margin differently — the blend is what puts the two MI players
  (6 games each) ahead of fa_bowl (CSK plays 0).
  Team V (14-man, same shape minus one) has an open spot: its
  recommendation for fa_bat carries drop_player_id = None.
"""

import json
import sqlite3
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.database import get_db
from api.routers import waivers

SCHEMA = Path(__file__).resolve().parent / "schema.sql"


def _player(con, name, role, code, rank, rank_team):
    pid = con.execute(
        "INSERT INTO players (name, season) VALUES (?, '2027')",
        (name,)).lastrowid
    con.execute(
        "INSERT INTO player_roles (player_id, season, role, is_overseas,"
        " ipl_team_code) VALUES (?, '2027', ?, 0, ?)", (pid, role, code))
    con.execute(
        "INSERT INTO pre_draft_ranks (team_id, player_id, rank)"
        " VALUES (?, ?, ?)", (rank_team, pid, rank))
    return pid


def _roster(con, team, pid):
    con.execute(
        "INSERT INTO roster_slots (team_id, player_id, slot)"
        " VALUES (?, ?, 'BN')", (team, pid))


def _seed(con):
    con.execute("INSERT INTO users (name) VALUES ('w16-owner')")
    league = con.execute(
        "INSERT INTO leagues (name, invite_code, commissioner_id,"
        " season, settings, status) VALUES ('w16-league', 'CODE-w16',"
        " 1, '2027', '{}', 'in_season')").lastrowid

    def team(name):
        return con.execute(
            "INSERT INTO teams (league_id, owner_id, name,"
            " faab_remaining) VALUES (?, 1, ?, 100)",
            (league, name)).lastrowid

    t, u, v = team("w16-T"), team("w16-U"), team("w16-V")
    ids = {"league": league, "t": t, "u": u, "v": v}
    shape = [("WK", 30), ("BAT", 40), ("AR", 45), ("BAT", 50),
             ("AR", 55), ("BAT", 60), ("BOWL", 35), ("BOWL", 65),
             ("BOWL", 70), ("BAT", 80), ("AR", 85), ("BOWL", 90),
             ("WK", 95), ("BAT", 100), ("BOWL", 110)]
    ids["t_roster"] = {}
    for i, (role, rank) in enumerate(shape):
        pid = _player(con, f"T{i}-{role}{rank}", role, "MI", rank, t)
        _roster(con, t, pid)
        ids["t_roster"][rank] = pid
        if i < 14:  # team V = same shape minus the last player
            _roster(con, v, pid)
    ids["fa_bat"] = _player(con, "FaBat", "BAT", "MI", 20, t)
    ids["fa_bowl"] = _player(con, "FaBowl", "BOWL", "CSK", 25, t)
    ids["fa_wk"] = _player(con, "FaWk", "WK", "MI", 28, t)
    ids["fa_bad"] = _player(con, "FaBad", "BAT", "MI", 105, t)
    ids["fa_owned"] = _player(con, "FaOwned", "BAT", "MI", 10, t)
    _roster(con, u, ids["fa_owned"])
    # Can't-cut: the rank-110 BOWL can never be the suggested drop.
    con.execute(
        "UPDATE leagues SET settings = ? WHERE id = ?",
        (json.dumps({"cant_cut_player_ids": [ids["t_roster"][110]]}),
         league))
    for wk in (1, 2, 3):
        con.execute(
            "INSERT INTO team_weekly_games (season, week_no, week_start,"
            " week_end, ipl_team_code, games, source) VALUES ('2027', ?,"
            " '2027-03-08', '2027-03-14', 'MI', 2, 'test')", (wk,))
    # A rival's pending blind bid on fa_bat — must never leak (D6).
    con.execute(
        "INSERT INTO waiver_claims (league_id, week_no, team_id,"
        " add_player_id, drop_player_id, bid, status) VALUES (?, 1, ?,"
        " ?, NULL, 99, 'pending')", (league, u, ids["fa_bat"]))
    con.commit()
    return ids


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / "recs.db"
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA.read_text())
    ids = _seed(con)
    con.close()

    app = FastAPI()
    app.include_router(waivers.router, prefix="/api/waivers")

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


def test_recommendations_hand_derived(client):
    tc, ids = client
    r = tc.get("/api/waivers/recommendations",
               params={"league_id": ids["league"], "team_id": ids["t"]})
    assert r.status_code == 200, r.text
    assert "99" not in r.text and "bid" not in r.text  # D6: no leak
    body = r.json()
    assert body["weeks"] == [1, 2, 3]
    recs = body["recommendations"]
    assert [x["player_id"] for x in recs] == [
        ids["fa_bat"], ids["fa_wk"], ids["fa_bowl"]]
    bat, wk, bowl = recs
    assert bat["upgrade"] == 80 and bat["score"] == 86
    assert bat["games_next_3_weeks"] == 6
    assert bat["drop_player_id"] == ids["t_roster"][100]
    assert "+80 rank value over your weakest BAT" in bat["reason"]
    assert "MI plays 6 games in the next 3 weeks" in bat["reason"]
    assert wk["upgrade"] == 67 and wk["score"] == 73
    assert wk["drop_player_id"] == ids["t_roster"][95]
    # Can't-cut: the rank-110 BOWL is never the drop; rank-90 is.
    assert bowl["upgrade"] == 65 and bowl["score"] == 65
    assert bowl["drop_player_id"] == ids["t_roster"][90]
    assert all(x["drop_player_id"] != ids["t_roster"][110] for x in recs)
    assert all(x["player_id"] not in (ids["fa_bad"], ids["fa_owned"])
               for x in recs)


def test_open_spot_needs_no_drop(client):
    tc, ids = client
    r = tc.get("/api/waivers/recommendations",
               params={"league_id": ids["league"], "team_id": ids["v"]})
    assert r.status_code == 200, r.text
    recs = {x["player_id"]: x for x in r.json()["recommendations"]}
    bat = recs[ids["fa_bat"]]
    assert bat["drop_player_id"] is None
    assert "open roster spot" in bat["reason"]


def test_recommendation_validation(client):
    tc, ids = client
    assert tc.get("/api/waivers/recommendations",
                  params={"league_id": 99999, "team_id": ids["t"]}
                  ).status_code == 404
    assert tc.get("/api/waivers/recommendations",
                  params={"league_id": ids["league"], "team_id": 99999}
                  ).status_code == 404
