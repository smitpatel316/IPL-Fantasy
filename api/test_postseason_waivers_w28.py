"""P4-W28 regression: phantom post-season waiver claims.

Before the fix, services.current_week() was MAX(final week)+1 with no
cap, so after the week-8 final new claims were filed into week 9 —
invisible to the pending/history reads (week_no <= TOTAL_WEEKS) yet
executable via the unbounded POST /waivers/run?week_no=9.

These tests use a scratch sqlite DB (schema.sql) + a minimal FastAPI
app mounting only the waivers router, and assert:
  * current_week is capped at TOTAL_WEEKS,
  * with weeks 7-8 final, a new claim is rejected 422 and writes no row,
  * POST /waivers/run?week_no=9 is 422 (router Query bound, and the
    service layer rejects it too),
  * a normal in-season claim + run still works unchanged.
"""

import sqlite3
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import services
from api.constants import TOTAL_WEEKS
from api.database import get_db
from api.routers import waivers

SCHEMA = Path(__file__).resolve().parent / "schema.sql"


def _seed_league(con, name, final_weeks):
    """One league, 2 teams (1 rostered player each), 1 free agent.
    Returns (league_id, team_a, team_b, drop_a, free_player)."""
    con.execute("INSERT INTO users (name) VALUES (?)", (f"{name}-owner",))
    cur = con.execute(
        "INSERT INTO leagues (name, invite_code, commissioner_id, season,"
        " settings, status) VALUES (?, ?, 1, '2027', '{}', 'in_season')",
        (name, f"CODE-{name}"),
    )
    league_id = cur.lastrowid
    team_ids = []
    drop_ids = []
    for label in ("A", "B"):
        t = con.execute(
            "INSERT INTO teams (league_id, owner_id, name, faab_remaining)"
            " VALUES (?, 1, ?, 100)",
            (league_id, f"{name}-{label}"),
        ).lastrowid
        team_ids.append(t)
        p = con.execute(
            "INSERT INTO players (name, season) VALUES (?, '2027')",
            (f"{name}-drop-{label}",),
        ).lastrowid
        drop_ids.append(p)
        con.execute(
            "INSERT INTO roster_slots (team_id, player_id, slot, week_no)"
            " VALUES (?, ?, 'BN', NULL)",
            (t, p),
        )
    free = con.execute(
        "INSERT INTO players (name, season) VALUES (?, '2027')",
        (f"{name}-free",),
    ).lastrowid
    for wk in final_weeks:
        con.execute(
            "INSERT INTO matchups (league_id, week_no, team_a_id, team_b_id,"
            " score_a, score_b, status) VALUES (?, ?, ?, ?, 10, 5, 'final')",
            (league_id, wk, team_ids[0], team_ids[1]),
        )
    con.commit()
    return league_id, team_ids[0], team_ids[1], drop_ids[0], free


@pytest.fixture()
def env(tmp_path):
    services._registry.clear()
    con = sqlite3.connect(str(tmp_path / "scratch.db"),
                          check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA.read_text())
    post = _seed_league(con, "Post", final_weeks=[7, 8])
    live = _seed_league(con, "Live", final_weeks=[1])

    app = FastAPI()
    app.include_router(waivers.router, prefix="/api/waivers")

    def _override_get_db():
        yield con

    app.dependency_overrides[get_db] = _override_get_db
    yield con, TestClient(app), post, live
    con.close()
    services._registry.clear()


def test_current_week_capped_at_total_weeks(env):
    con, _client, post, live = env
    assert services.current_week(con, post[0]) == TOTAL_WEEKS  # not 9
    assert services.current_week(con, live[0]) == 2


def test_postseason_claim_rejected_and_run_week9_422(env):
    con, client, post, _live = env
    league_id, team_a, _team_b, drop_a, free = post

    r = client.post("/api/waivers/claim", json={
        "league_id": league_id, "team_id": team_a,
        "add_player_id": free, "drop_player_id": drop_a, "bid": 5,
    })
    assert r.status_code == 422, r.text
    assert "season is complete" in r.json()["detail"]
    # No phantom row was written (in any week).
    assert con.execute(
        "SELECT COUNT(*) FROM waiver_claims WHERE league_id = ?",
        (league_id,)).fetchone()[0] == 0

    r = client.post("/api/waivers/run",
                    params={"league_id": league_id, "week_no": 9})
    assert r.status_code == 422, r.text

    # Service-layer defence in depth (direct callers / scheduler).
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        services.submit_waiver_claim(con, league_id, team_a, 9, free,
                                     drop_a, 5)
    assert exc.value.status_code == 422
    with pytest.raises(HTTPException) as exc:
        services.run_waivers(con, league_id, 9)
    assert exc.value.status_code == 422


def test_inseason_claim_and_run_still_work(env):
    con, client, _post, live = env
    league_id, team_a, _team_b, drop_a, free = live

    r = client.post("/api/waivers/claim", json={
        "league_id": league_id, "team_id": team_a,
        "add_player_id": free, "drop_player_id": drop_a, "bid": 5,
    })
    assert r.status_code == 200, r.text
    assert r.json()["week_no"] == 2
    assert r.json()["status"] == "pending"

    r = client.get("/api/waivers/pending",
                   params={"league_id": league_id, "week_no": 2})
    assert r.status_code == 200 and len(r.json()) == 1

    r = client.post("/api/waivers/run",
                    params={"league_id": league_id, "week_no": 2})
    assert r.status_code == 200, r.text
    assert r.json()[0]["winner_team_id"] == team_a
    assert r.json()[0]["player_id"] == free
