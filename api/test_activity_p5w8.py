"""P5-W8: league activity feed — read-only projection over recorded
events (draft picks, waiver-run outcomes, executed/vetoed trades,
commissioner adjustments), newest first, paginated.

D6 HARD INVARIANT under test: a pending claim never appears, and a
losing bid's amount appears NOWHERE in the payload — only the winning
bid ($7 here) is public once the run executes. The losing bid is $42
and the pending bid is $99; neither string may show up as an amount.

Hand-derived order (occurred_at desc):
  adj (10:05) > trade executed (10:04) > waiver lost (10:03)
  > waiver won (10:02) > draft pick (10:01).
"""

import sqlite3
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.database import get_db
from api.routers import activity

SCHEMA = Path(__file__).resolve().parent / "schema.sql"
DAY = "2027-03-10"


def _seed(con):
    con.execute("INSERT INTO users (name) VALUES ('w8-owner')")
    ids = {}
    league = con.execute(
        "INSERT INTO leagues (name, invite_code, commissioner_id,"
        " season, settings, status) VALUES ('w8-league', 'CODE-w8', 1,"
        " '2027', '{}', 'in_season')").lastrowid
    ids["league"] = league
    for label in ("A", "B"):
        ids[f"team{label}"] = con.execute(
            "INSERT INTO teams (league_id, owner_id, name,"
            " faab_remaining) VALUES (?, 1, ?, 100)",
            (league, f"w8-{label}")).lastrowid
    for name in ("Alpha", "Beta", "Gamma"):
        ids[name.lower()] = con.execute(
            "INSERT INTO players (name, season) VALUES (?, '2027')",
            (name,)).lastrowid
    draft = con.execute(
        "INSERT INTO drafts (league_id, status) VALUES (?, 'complete')",
        (league,)).lastrowid
    con.execute(
        "INSERT INTO draft_picks (draft_id, pick_no, round_no, team_id,"
        " player_id, is_auto, picked_at) VALUES (?, 1, 1, ?, ?, 0, ?)",
        (draft, ids["teamA"], ids["alpha"], f"{DAY} 10:01:00"))
    # Waiver outcomes: A won Alpha for $7; B's $42 claim for Alpha lost;
    # a $99 PENDING claim for Beta must never appear.
    con.execute(
        "INSERT INTO waiver_claims (league_id, week_no, team_id,"
        " add_player_id, bid, status, created_at) VALUES"
        " (?, 1, ?, ?, 7, 'won', ?)",
        (league, ids["teamA"], ids["alpha"], f"{DAY} 10:02:00"))
    con.execute(
        "INSERT INTO waiver_claims (league_id, week_no, team_id,"
        " add_player_id, bid, status, created_at) VALUES"
        " (?, 1, ?, ?, 42, 'lost', ?)",
        (league, ids["teamB"], ids["alpha"], f"{DAY} 10:03:00"))
    con.execute(
        "INSERT INTO waiver_claims (league_id, week_no, team_id,"
        " add_player_id, bid, status, created_at) VALUES"
        " (?, 1, ?, ?, 99, 'pending', ?)",
        (league, ids["teamB"], ids["beta"], f"{DAY} 10:06:00"))
    con.execute(
        "INSERT INTO trades (league_id, from_team_id, to_team_id,"
        " gives, receives, status, executed_at) VALUES"
        " (?, ?, ?, '[%d]', '[%d]', 'executed', ?)"
        % (ids["beta"], ids["gamma"]),
        (league, ids["teamA"], ids["teamB"], f"{DAY} 10:04:00"))
    con.execute(
        "INSERT INTO league_adjustments (league_id, team_id, kind,"
        " faab_delta, faab_after, note, created_at) VALUES"
        " (?, ?, 'faab', 5, 105, 'goodwill', ?)",
        (league, ids["teamB"], f"{DAY} 10:05:00"))
    con.commit()
    return ids


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / "activity.db"
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA.read_text())
    ids = _seed(con)
    con.close()

    app = FastAPI()
    app.include_router(activity.router, prefix="/api/leagues")

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


def test_feed_order_and_content(client):
    tc, ids = client
    r = tc.get(f"/api/leagues/{ids['league']}/activity")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 5
    kinds = [e["kind"] for e in body["entries"]]
    assert kinds == ["commissioner_faab", "trade_executed",
                     "waiver_lost", "waiver_won", "draft_pick"]
    won = body["entries"][3]
    assert won["amount"] == 7 and "$7" in won["text"]
    assert "Alpha" in won["text"] and "w8-A" in won["text"]
    pick = body["entries"][4]
    assert "drafted Alpha" in pick["text"] and "pick 1" in pick["text"]
    trade = body["entries"][1]
    assert "Beta" in trade["text"] and "Gamma" in trade["text"]


def test_no_sealed_bid_leak(client):
    tc, ids = client
    raw = tc.get(f"/api/leagues/{ids['league']}/activity").text
    body = tc.get(f"/api/leagues/{ids['league']}/activity").json()
    # Pending claim: absent entirely, its $99 nowhere.
    assert all(e["player_name"] != "Beta" or e["kind"] == "trade_executed"
               for e in body["entries"])
    assert "99" not in raw
    # Losing bid: entry exists but carries no amount anywhere.
    lost = [e for e in body["entries"] if e["kind"] == "waiver_lost"]
    assert len(lost) == 1 and lost[0]["amount"] is None
    assert "$42" not in raw and '"amount":42' not in raw.replace(" ", "")


def test_pagination(client):
    tc, ids = client
    p1 = tc.get(f"/api/leagues/{ids['league']}/activity",
                params={"limit": 2, "offset": 0}).json()
    p2 = tc.get(f"/api/leagues/{ids['league']}/activity",
                params={"limit": 2, "offset": 2}).json()
    p3 = tc.get(f"/api/leagues/{ids['league']}/activity",
                params={"limit": 2, "offset": 4}).json()
    assert [len(p["entries"]) for p in (p1, p2, p3)] == [2, 2, 1]
    seen = [e["id"] for p in (p1, p2, p3) for e in p["entries"]]
    assert len(set(seen)) == 5  # no overlap across pages


def test_unknown_league_404(client):
    tc, _ = client
    assert tc.get("/api/leagues/99999/activity").status_code == 404
