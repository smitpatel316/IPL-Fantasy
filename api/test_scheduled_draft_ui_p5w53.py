"""P5-W53: UI-contract tests for the scheduled-draft control.

The ScheduledDraftSetter component (web/components/ScheduledDraftSetter.tsx)
sends exactly this request shape:
  PATCH /api/leagues/{id}/settings?team_id=<commissioner team>
      + X-Team-Claim header
      body {"draft_scheduled_at": <instant>}
where <instant> is what a datetime-local input produces converted with the
browser's own offset — no seconds, e.g. "2027-03-01T14:00-05:00" — and
{"draft_scheduled_at": ""} to clear. Assertions (all hand-derived):
  * the seconds-less offset form normalizes to the same UTC instant;
  * set-then-clear round-trips: the stored key disappears, the key-dates
    draft entry drops its instant, and the .ics feed omits the draft VEVENT;
  * naive/garbled instants 422 with the plain-English details the control
    renders inline.
"""
import sqlite3
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.database import get_db
from api.routers import key_dates, leagues

SCHEMA = Path(__file__).resolve().parent / "schema.sql"

# Hand-computed: the component's toOffsetIso turns a datetime-local
# "2027-03-01T14:00" into "2027-03-01T14:00-05:00"; 14:00 at UTC-5 is
# 19:00 UTC. Matches the W51 reference instant exactly.
UI_INSTANT = "2027-03-01T14:00-05:00"
INSTANT_UTC = "2027-03-01T19:00:00+00:00"
INSTANT_BASIC_START = "20270301T190000Z"


def _seed(con):
    con.execute("INSERT INTO users (name) VALUES ('w53-owner')")
    league = con.execute(
        "INSERT INTO leagues (name, invite_code, commissioner_id,"
        " season, settings, status) VALUES ('w53', 'CODE-w53', 1,"
        " '2027', '{}', 'setup')").lastrowid
    teams = []
    for name, code in (("A", "sekrit-a"), ("B", "sekrit-b")):
        teams.append(con.execute(
            "INSERT INTO teams (league_id, name, owner_id, claim_code)"
            " VALUES (?, ?, 1, ?)", (league, name, code)).lastrowid)
    con.commit()
    return league, teams  # A is the commissioner's team


def env_fixture(tmp_path):
    db_path = tmp_path / "ui-schedule.db"
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA.read_text())
    league, (comm_team, _) = _seed(con)
    con.close()
    app = FastAPI()
    app.include_router(leagues.router, prefix="/api/leagues")
    app.include_router(key_dates.router, prefix="/api/leagues")

    def override():
        c = sqlite3.connect(str(db_path))
        c.row_factory = sqlite3.Row
        try:
            yield c
        finally:
            c.close()

    app.dependency_overrides[get_db] = override
    return TestClient(app), league, comm_team


def _ui_patch(tc, league, team_id, instant, claim="sekrit-a"):
    """The component's exact request: commissioner_team_id in the body
    (P5-W52) + claim header + the key."""
    return tc.patch(
        f"/api/leagues/{league}/settings",
        json={"commissioner_team_id": team_id, "draft_scheduled_at": instant},
        headers={"X-Team-Claim": claim})


def _draft_entry(tc, league):
    payload = tc.get(f"/api/leagues/{league}/key-dates").json()
    return next(e for e in payload["entries"] if e["key"] == "draft")


def _ics_draft_starts(text):
    return [ln.split(":", 1)[1] for ln in text.split("\r\n")
            if ln.startswith("DTSTART:")]


def test_ui_seconds_less_offset_set(tmp_path):
    tc, league, comm = env_fixture(tmp_path)
    r = _ui_patch(tc, league, comm, UI_INSTANT)
    assert r.status_code == 200, r.text
    assert r.json()["settings"]["draft_scheduled_at"] == INSTANT_UTC


def test_ui_set_then_clear_roundtrip(tmp_path):
    tc, league, comm = env_fixture(tmp_path)
    # Set (UI shape) — countdown + .ics reflect it.
    r = _ui_patch(tc, league, comm, UI_INSTANT)
    assert r.status_code == 200, r.text
    entry = _draft_entry(tc, league)
    assert entry["at"] == INSTANT_UTC
    ics = tc.get(f"/api/leagues/{league}/key-dates.ics").text
    assert INSTANT_BASIC_START in _ics_draft_starts(ics)
    # Clear (UI sends "").
    r = _ui_patch(tc, league, comm, "")
    assert r.status_code == 200, r.text
    assert "draft_scheduled_at" not in r.json()["settings"]
    entry = _draft_entry(tc, league)
    assert entry["at"] is None
    ics = tc.get(f"/api/leagues/{league}/key-dates.ics").text
    assert INSTANT_BASIC_START not in _ics_draft_starts(ics)


def test_ui_invalid_instant_detail_surfaces_inline(tmp_path):
    tc, league, comm = env_fixture(tmp_path)
    r = _ui_patch(tc, league, comm, "2027-03-01T19:00")
    assert r.status_code == 422, r.text
    assert r.json()["detail"] == \
        "draft_scheduled_at must include a timezone offset"
    r = _ui_patch(tc, league, comm, "next tuesday")
    assert r.status_code == 422, r.text
    assert r.json()["detail"] == "draft_scheduled_at must be an ISO 8601 instant"
    # Failed saves leave nothing scheduled.
    assert _draft_entry(tc, league)["at"] is None
