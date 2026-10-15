"""P4-W33 regression: re-running a genuinely-run waiver week.

Before the fix, services.run_waivers short-circuited on pending==0
BEFORE checking whether the week had genuinely run, so a re-run of a
week that already processed claims returned 200 [] instead of the
documented 422 WeekAlreadyRun — contradicting the W31 result line,
the code comment, and the engine contract (WaiverEngine.run_week
raises WeekAlreadyRun for weeks in _runs).

The service layer must now distinguish the two empty-pending cases:
  * genuinely-run week (engine _runs, persisted in engine_state)
    -> 422 "week N waivers already ran", no duplicate effects;
  * never-run week with zero pending claims (P4-W31)
    -> 200 [] and the week stays open for later claims.

Scratch sqlite DB (schema.sql) + minimal FastAPI app mounting only
the waivers router. Rosters carry role metadata (player_roles) so the
P4-W30 D8 guard lets the genuine claim through.
"""

import sqlite3
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.testclient import TestClient

from api import services
from api.database import get_db
from api.routers import waivers

SCHEMA = Path(__file__).resolve().parent / "schema.sql"

# (role, count) per team: WK1/BAT3/AR2/BOWL3 starters + BN3 (BATx2/BOWLx1).
ROSTER_MIX = [("WK", 1), ("BAT", 5), ("AR", 2), ("BOWL", 4)]


def _seed_league(con):
    """1 league, 2 teams x 14 D8-fieldable players, 1 free-agent BAT."""
    con.execute("INSERT INTO users (name) VALUES ('w33-owner')")
    cur = con.execute(
        "INSERT INTO leagues (name, invite_code, commissioner_id, season,"
        " settings, status) VALUES ('w33', 'CODE-w33', 1, '2027', '{}',"
        " 'in_season')"
    )
    league_id = cur.lastrowid
    team_ids, drop_by_team = [], {}
    for label in ("A", "B"):
        t = con.execute(
            "INSERT INTO teams (league_id, owner_id, name, faab_remaining)"
            " VALUES (?, 1, ?, 100)",
            (league_id, f"w33-{label}"),
        ).lastrowid
        team_ids.append(t)
        for role, n in ROSTER_MIX:
            for i in range(n):
                p = con.execute(
                    "INSERT INTO players (name, season) VALUES (?, '2027')",
                    (f"w33-{label}-{role}-{i}",),
                ).lastrowid
                con.execute(
                    "INSERT INTO player_roles (player_id, season, role,"
                    " is_overseas, ipl_team_code, source, status)"
                    " VALUES (?, '2027', ?, 0, 'MI', 'w33', NULL)",
                    (p, role),
                )
                con.execute(
                    "INSERT INTO roster_slots (team_id, player_id, slot,"
                    " week_no) VALUES (?, ?, 'BN', NULL)",
                    (t, p),
                )
                if label == "A" and role == "BAT" and i == 4:
                    drop_by_team[t] = p  # a bench BAT to drop
    free = con.execute(
        "INSERT INTO players (name, season) VALUES ('w33-free', '2027')"
    ).lastrowid
    con.execute(
        "INSERT INTO player_roles (player_id, season, role, is_overseas,"
        " ipl_team_code, source, status)"
        " VALUES (?, '2027', 'BAT', 0, 'MI', 'w33', NULL)",
        (free,),
    )
    con.commit()
    return league_id, team_ids[0], team_ids[1], drop_by_team[team_ids[0]], free


@pytest.fixture()
def env(tmp_path):
    services._registry.clear()
    con = sqlite3.connect(str(tmp_path / "scratch.db"),
                          check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA.read_text())
    seeded = _seed_league(con)

    app = FastAPI()
    app.include_router(waivers.router, prefix="/api/waivers")

    def _override_get_db():
        yield con

    app.dependency_overrides[get_db] = _override_get_db
    yield con, TestClient(app), seeded
    con.close()
    services._registry.clear()


def _faab(con, team_id):
    return con.execute(
        "SELECT faab_remaining FROM teams WHERE id = ?", (team_id,)
    ).fetchone()[0]


def test_rerun_of_genuinely_run_week_422(env):
    con, client, seeded = env
    league_id, team_a, _team_b, drop_a, free = seeded

    r = client.post("/api/waivers/claim", json={
        "league_id": league_id, "team_id": team_a,
        "add_player_id": free, "drop_player_id": drop_a, "bid": 5,
    })
    assert r.status_code == 200, r.text

    r = client.post("/api/waivers/run",
                    params={"league_id": league_id, "week_no": 1})
    assert r.status_code == 200, r.text
    assert r.json()[0]["winner_team_id"] == team_a
    assert _faab(con, team_a) == 95

    # Re-running the genuinely-run week must be 422, not a silent [].
    r = client.post("/api/waivers/run",
                    params={"league_id": league_id, "week_no": 1})
    assert r.status_code == 422, r.text
    assert "already ran" in r.json()["detail"]
    # No duplicate effects: FAAB charged exactly once.
    assert _faab(con, team_a) == 95

    # Service-layer defence in depth (direct callers / scheduler).
    with pytest.raises(HTTPException) as exc:
        services.run_waivers(con, league_id, 1)
    assert exc.value.status_code == 422
    assert "already ran" in exc.value.detail


def test_empty_never_run_week_stays_open(env):
    con, client, seeded = env
    league_id, team_a, _team_b, drop_a, free = seeded

    # No claims filed for week 1 at all: run is a silent no-op (P4-W31).
    r = client.post("/api/waivers/run",
                    params={"league_id": league_id, "week_no": 1})
    assert r.status_code == 200, r.text
    assert r.json() == []

    # And the week stays OPEN: a later claim for week 1 is accepted.
    r = client.post("/api/waivers/claim", json={
        "league_id": league_id, "team_id": team_a,
        "add_player_id": free, "drop_player_id": drop_a, "bid": 8,
    })
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "pending"
