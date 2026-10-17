"""P5-W31: custom pre-draft ranks CSV import/export.

Hand-derived expectations:
- Seed ranks for team A = [P3, P1, P2] (by id order of insertion:
  Alpha/BAT/MI, Bravo/WK/CSK, Charlie/BOWL/MI). Export must render
  exactly those rows in that order with role/IPL-team joined.
- Export -> import round-trip reproduces [P3, P1, P2] identically.
- Import by exact name (header rank,player) orders as listed.
- Unknown name / unknown id / duplicate / out-of-pool player (a
  2026-season player) each 422 and leave the saved ranks untouched.
- A claimed team 403s an import without its claim code and accepts
  it with the code.
- Auto-pick follows imported ranks: in a built draft, the on-clock
  team's auto-pick is its imported #1 (a domestic BAT).
"""

import sqlite3
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import services
from api.database import get_db
from api.routers import ranks

SCHEMA = Path(__file__).resolve().parent / "schema.sql"
PLAYERS = [
    # name, role, team, overseas
    ("Alpha", "BAT", "MI", 0),
    ("Bravo", "WK", "CSK", 0),
    ("Charlie", "BOWL", "MI", 1),
    ("Delta", "AR", "CSK", 0),
]


def _seed(con):
    con.execute("INSERT INTO users (name) VALUES ('w31-owner')")
    league = con.execute(
        "INSERT INTO leagues (name, invite_code, commissioner_id,"
        " season, settings, status) VALUES ('w31-league', 'CODE-w31',"
        " 1, '2027', '{}', 'setup')").lastrowid
    team_a = con.execute(
        "INSERT INTO teams (league_id, name, owner_id) VALUES (?, 'A', 1)",
        (league,)).lastrowid
    team_b = con.execute(
        "INSERT INTO teams (league_id, name, owner_id) VALUES (?, 'B', 1)",
        (league,)).lastrowid
    ids = {}
    for name, role, code, os_ in PLAYERS:
        pid = con.execute(
            "INSERT INTO players (name, season) VALUES (?, '2027')",
            (name,)).lastrowid
        con.execute(
            "INSERT INTO player_roles (player_id, season, role,"
            " is_overseas, ipl_team_code) VALUES (?, '2027', ?, ?, ?)",
            (pid, role, os_, code))
        ids[name] = pid
    # Out-of-pool: same name pattern, wrong season for this league.
    old = con.execute(
        "INSERT INTO players (name, season) VALUES ('Oldtimer', '2026')"
    ).lastrowid
    con.execute(
        "INSERT INTO player_roles (player_id, season, role,"
        " is_overseas, ipl_team_code) VALUES (?, '2026', 'BAT', 0, 'MI')",
        (old,))
    # Saved ranks for A: Charlie, Alpha, Bravo.
    for i, name in enumerate(["Charlie", "Alpha", "Bravo"]):
        con.execute(
            "INSERT INTO pre_draft_ranks (team_id, player_id, rank)"
            " VALUES (?, ?, ?)", (team_a, ids[name], i + 1))
    con.commit()
    return {"league": league, "a": team_a, "b": team_b, "ids": ids,
            "old": old}


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / "ranks.db"
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA.read_text())
    ids = _seed(con)
    con.close()
    app = FastAPI()
    app.include_router(ranks.router, prefix="/api")

    def override():
        # check_same_thread=False mirrors api/database.py: the async
        # import endpoint runs on the event-loop thread.
        c = sqlite3.connect(str(db_path), check_same_thread=False)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys = ON")
        try:
            yield c
        finally:
            c.close()

    app.dependency_overrides[get_db] = override
    return TestClient(app), ids, db_path


def _saved(tc, team):
    r = tc.get(f"/api/teams/{team}/ranks")
    assert r.status_code == 200, r.text
    return r.json()["player_ids"]


def test_export_projection(client):
    tc, ids, _ = client
    p = ids["ids"]
    assert _saved(tc, ids["a"]) == [p["Charlie"], p["Alpha"], p["Bravo"]]
    r = tc.get(f"/api/teams/{ids['a']}/ranks.csv")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("text/csv")
    lines = r.text.strip().splitlines()
    assert lines[0] == "rank,player_id,player,role,ipl_team"
    assert lines[1:] == [
        f"1,{p['Charlie']},Charlie,BOWL,MI",
        f"2,{p['Alpha']},Alpha,BAT,MI",
        f"3,{p['Bravo']},Bravo,WK,CSK",
    ]
    # Empty ranks export is header-only; unknown team 404s.
    r = tc.get(f"/api/teams/{ids['b']}/ranks.csv")
    assert r.text.strip().splitlines() == ["rank,player_id,player,role,ipl_team"]
    assert tc.get("/api/teams/99999/ranks.csv").status_code == 404


def test_export_import_round_trip(client):
    tc, ids, _ = client
    exported = tc.get(f"/api/teams/{ids['a']}/ranks.csv").text
    r = tc.post(f"/api/teams/{ids['b']}/ranks/import",
                content=exported, headers={"Content-Type": "text/csv"})
    assert r.status_code == 200, r.text
    assert r.json()["player_ids"] == _saved(tc, ids["a"])
    assert _saved(tc, ids["b"]) == _saved(tc, ids["a"])


def test_import_by_name_and_bare_ids(client):
    tc, ids, _ = client
    p = ids["ids"]
    r = tc.post(f"/api/teams/{ids['b']}/ranks/import",
                content="rank,player\n1,Delta\n2,Alpha\n",
                headers={"Content-Type": "text/csv"})
    assert r.status_code == 200, r.text
    assert _saved(tc, ids["b"]) == [p["Delta"], p["Alpha"]]
    r = tc.post(f"/api/teams/{ids['b']}/ranks/import",
                content=f"{p['Bravo']}\n{p['Charlie']}\n",
                headers={"Content-Type": "text/csv"})
    assert r.status_code == 200, r.text
    assert _saved(tc, ids["b"]) == [p["Bravo"], p["Charlie"]]


def test_import_validation_leaves_ranks_untouched(client):
    tc, ids, _ = client
    p = ids["ids"]
    before = _saved(tc, ids["a"])
    bad_bodies = [
        "rank,player\n1,Nobody\n",                       # unknown name
        f"rank,player_id\n1,{p['Alpha']}\n2,{p['Alpha']}\n",  # duplicate
        f"player_id\n99999\n",                           # unknown id
        f"player_id\n{ids['old']}\n",                    # out of pool
        "player\nOldtimer\n",                            # out of pool by name
        "",                                              # empty
        "rank,player\n",                                 # header only
    ]
    for body in bad_bodies:
        r = tc.post(f"/api/teams/{ids['a']}/ranks/import",
                    content=body, headers={"Content-Type": "text/csv"})
        assert r.status_code == 422, (body, r.text)
        assert _saved(tc, ids["a"]) == before


def test_import_claim_gate(client):
    tc, ids, db_path = client
    con = sqlite3.connect(str(db_path))
    con.execute("UPDATE teams SET claim_code = 'CODE123456' WHERE id = ?",
                (ids["a"],))
    con.commit()
    con.close()
    body = "player\nAlpha\n"
    r = tc.post(f"/api/teams/{ids['a']}/ranks/import",
                content=body, headers={"Content-Type": "text/csv"})
    assert r.status_code == 403, r.text
    r = tc.post(f"/api/teams/{ids['a']}/ranks/import",
                content=body,
                headers={"Content-Type": "text/csv",
                         "X-Team-Claim": "CODE123456"})
    assert r.status_code == 200, r.text
    assert _saved(tc, ids["a"]) == [ids["ids"]["Alpha"]]
    assert tc.post("/api/teams/99999/ranks/import", content=body,
                   headers={"Content-Type": "text/csv"}).status_code == 404


def test_auto_pick_follows_imported_ranks(tmp_path):
    db_path = tmp_path / "draft.db"
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA.read_text())
    con.execute("INSERT INTO users (name) VALUES ('w31-owner')")
    league = con.execute(
        "INSERT INTO leagues (name, invite_code, commissioner_id,"
        " season, settings, status) VALUES ('w31-draft', 'CODE-w31d',"
        " 1, '2027', '{}', 'setup')").lastrowid
    teams = []
    for name in ("A", "B"):
        teams.append(con.execute(
            "INSERT INTO teams (league_id, name, owner_id)"
            " VALUES (?, ?, 1)", (league, name)).lastrowid)
    roles = ["WK", "BAT", "BAT", "AR", "BOWL", "BOWL"]
    pids = []
    for i in range(32):
        pid = con.execute(
            "INSERT INTO players (name, season) VALUES (?, '2027')",
            (f"Player {i:02d}",)).lastrowid
        con.execute(
            "INSERT INTO player_roles (player_id, season, role,"
            " is_overseas, ipl_team_code) VALUES (?, '2027', ?, 0, 'MI')",
            (pid, roles[i % len(roles)]))
        pids.append(pid)
    # Consensus order (what auto-pick would follow without customs):
    # player 0 first for every team.
    for t in teams:
        for i, pid in enumerate(pids):
            con.execute(
                "INSERT INTO pre_draft_ranks (team_id, player_id, rank)"
                " VALUES (?, ?, ?)", (t, pid, i + 1))
    con.commit()

    # Import a custom order for BOTH teams via the service-level CSV
    # parser path the endpoint uses: team order starts with a BAT
    # buried at consensus #20 (index 19 -> a BAT by the role cycle).
    from api.routers.ranks import _parse_ranks_csv
    star = pids[19]
    assert roles[19 % len(roles)] == "BAT"
    for t in teams:
        order = _parse_ranks_csv(
            f"player_id\n{star}\n" + "\n".join(
                str(p) for p in pids if p != star),
            {pid: "" for pid in pids}, {})
        services.set_team_ranks(con, t, order)
    draft = services._build_draft(con, league)
    pick = draft.auto_pick()
    assert pick["player_id"] == star
    con.close()
