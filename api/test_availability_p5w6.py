"""P5-W6: lineup availability dots.

Availability is derived server-side from the curated
player_roles.status (the P4-W4 designation) until the live poller
lands: NULL/'active' -> 'active', 'retired' -> 'retired', any other
designation ('injured', 'out') -> 'out'. It rides PlayerOut (list +
detail + watchlist entries, which extend PlayerOut) and the lineup
response's player_availability map so every slot can be dotted.

Hand-derived expectations from the seed below:
  * 'Fit'    status NULL      -> active
  * 'Active' status 'active'  -> active
  * 'Hurt'   status 'injured' -> out
  * 'Gone'   status 'out'     -> out
  * 'Old'    status 'retired' -> retired
"""

import sqlite3
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.database import get_db
from api.routers import lineups, players
from api.routers import availability_from_status

SCHEMA = Path(__file__).resolve().parent / "schema.sql"

CASES = [
    ("Fit", None, "active"),
    ("Active", "active", "active"),
    ("Hurt", "injured", "out"),
    ("Gone", "out", "out"),
    ("Old", "retired", "retired"),
]


def test_availability_from_status_mapping():
    for _, status, expected in CASES:
        assert availability_from_status(status) == expected
    assert availability_from_status("  Injured ") == "out"  # case/space-safe
    assert availability_from_status("") == "active"


def _seed(con):
    con.execute("INSERT INTO users (name) VALUES ('w6-owner')")
    league_id = con.execute(
        "INSERT INTO leagues (name, invite_code, commissioner_id,"
        " season, settings, status) VALUES ('w6-league', 'CODE-w6', 1,"
        " '2027', '{}', 'in_season')",
    ).lastrowid
    team_id = con.execute(
        "INSERT INTO teams (league_id, owner_id, name, faab_remaining)"
        " VALUES (?, 1, 'w6-team', 100)",
        (league_id,),
    ).lastrowid
    ids = {}
    for name, status, _ in CASES:
        pid = con.execute(
            "INSERT INTO players (name, season) VALUES (?, '2027')", (name,)
        ).lastrowid
        con.execute(
            "INSERT INTO player_roles (player_id, season, role,"
            " is_overseas, ipl_team_code, status)"
            " VALUES (?, '2027', 'BAT', 0, 'MI', ?)",
            (pid, status),
        )
        ids[name] = pid
    # Fit starts at BAT and Hurt sits on the bench in the week-1 lineup.
    con.execute(
        "INSERT INTO roster_slots (team_id, player_id, slot, week_no)"
        " VALUES (?, ?, 'BAT', 1)",
        (team_id, ids["Fit"]),
    )
    con.execute(
        "INSERT INTO roster_slots (team_id, player_id, slot, week_no)"
        " VALUES (?, ?, 'BN', 1)",
        (team_id, ids["Hurt"]),
    )
    con.commit()
    return {"league": league_id, "team": team_id, "players": ids}


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / "availability.db"
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA.read_text())
    ids = _seed(con)
    con.close()

    app = FastAPI()
    app.include_router(players.router, prefix="/api/players")
    app.include_router(lineups.router, prefix="/api")

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


def test_players_list_and_detail_carry_availability(client):
    tc, ids = client
    r = tc.get("/api/players", params={"league_id": ids["league"]})
    assert r.status_code == 200, r.text
    got = {p["name"]: p["availability"] for p in r.json()}
    assert got == {name: expected for name, _, expected in CASES}
    for name, _, expected in CASES:
        d = tc.get(f"/api/players/{ids['players'][name]}",
                   params={"league_id": ids["league"]})
        assert d.status_code == 200, d.text
        assert d.json()["availability"] == expected


def test_lineup_response_maps_slot_availability(client):
    tc, ids = client
    r = tc.get(f"/api/teams/{ids['team']}/lineup", params={"week_no": 1})
    assert r.status_code == 200, r.text
    avail = r.json()["player_availability"]
    assert avail[str(ids["players"]["Fit"])] == "active"
    assert avail[str(ids["players"]["Hurt"])] == "out"
