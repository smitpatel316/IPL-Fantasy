"""P5-W51: commissioner-set scheduled draft instant — hand-derived.

The commissioner (team A, claim-gated per P4-W18) sets the draft
instant via PATCH /api/leagues/{id}/settings; it is stored on the
league settings normalized to UTC ISO 8601. Assertions:
  * round-trip: stored value + GET league detail show the UTC instant;
  * a +05:00-offset input is normalized to the same UTC instant;
  * key-dates draft entry carries at/at_pt/at_ist at the stored
    instant (hand-computed PT/IST renderings), state upcoming;
  * .ics renders a draft VEVENT whose DTSTART equals the stored
    instant (UTC basic format) with a +30min DTEND; an unscheduled
    league still omits the draft VEVENT (P5-W35 behavior);
  * a past instant flips the draft entry to next-up ("scheduled time
    has passed"), never "past";
  * a near-future instant (earliest dated entry) reads next-up;
  * gating: 422 with no team_id, 403 for a non-commissioner team and
    for a wrong claim code; other settings stay ungated;
  * naive/garbled instants 422; scheduling locks once the draft has
    started (422); "" clears the schedule.
"""
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.database import get_db
from api.routers import key_dates, leagues

SCHEMA = Path(__file__).resolve().parent / "schema.sql"

# Hand-computed: 2027-03-01T19:00:00+00:00 is a Monday; US DST 2027
# starts Mar 14, so PT is PST (UTC-8): 11:00. IST (UTC+5:30): 00:30
# the next day.
INSTANT_UTC = "2027-03-01T19:00:00+00:00"
INSTANT_PT = "Mon Mar 01, 2027 11:00 PST"
INSTANT_IST = "Tue Mar 02, 2027 00:30 IST"
INSTANT_BASIC = "20270301T190000Z"
INSTANT_BASIC_END = "20270301T193000Z"
PAST_INSTANT = "2020-01-01T00:00:00+00:00"


def _seed(con):
    con.execute("INSERT INTO users (name) VALUES ('w51-owner')")
    league = con.execute(
        "INSERT INTO leagues (name, invite_code, commissioner_id,"
        " season, settings, status) VALUES ('w51', 'CODE-w51', 1,"
        " '2027', '{}', 'setup')").lastrowid
    teams = []
    for name, code in (("A", "sekrit-a"), ("B", "sekrit-b")):
        teams.append(con.execute(
            "INSERT INTO teams (league_id, name, owner_id, claim_code)"
            " VALUES (?, ?, 1, ?)", (league, name, code)).lastrowid)
    con.commit()
    return league, teams  # A is the commissioner's team (owner_id match)


@pytest.fixture()
def env(tmp_path):
    db_path = tmp_path / "scheduled.db"
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA.read_text())
    league, (comm_team, other_team) = _seed(con)
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
    return (TestClient(app), db_path, league, comm_team, other_team)


def _schedule(tc, league, team_id, instant, claim="sekrit-a"):
    return tc.patch(
        f"/api/leagues/{league}/settings?team_id={team_id}",
        json={"draft_scheduled_at": instant},
        headers={"X-Team-Claim": claim})


def _draft_entry(tc, league):
    payload = tc.get(f"/api/leagues/{league}/key-dates").json()
    return next(e for e in payload["entries"] if e["key"] == "draft")


def _ics_events(text):
    events, cur = [], None
    for line in text.split("\r\n"):
        if line == "BEGIN:VEVENT":
            cur = {}
        elif line == "END:VEVENT":
            events.append(cur)
            cur = None
        elif cur is not None and ":" in line:
            k, v = line.split(":", 1)
            cur[k] = v
    return events


def test_set_and_roundtrip(env):
    tc, _, league, comm, _ = env
    r = _schedule(tc, league, comm, INSTANT_UTC)
    assert r.status_code == 200, r.text
    assert r.json()["settings"]["draft_scheduled_at"] == INSTANT_UTC
    # Round-trips through the league read too.
    detail = tc.get(f"/api/leagues/{league}").json()
    assert detail["settings"]["draft_scheduled_at"] == INSTANT_UTC


def test_offset_input_normalized_to_utc(env):
    tc, _, league, comm, _ = env
    r = _schedule(tc, league, comm, "2027-03-01T14:00:00-05:00")
    assert r.status_code == 200, r.text
    assert r.json()["settings"]["draft_scheduled_at"] == INSTANT_UTC


def test_key_dates_draft_entry(env):
    tc, _, league, comm, _ = env
    _schedule(tc, league, comm, INSTANT_UTC)
    entry = _draft_entry(tc, league)
    assert entry["at"] == INSTANT_UTC
    assert entry["at_pt"] == INSTANT_PT
    assert entry["at_ist"] == INSTANT_IST
    assert entry["state"] == "upcoming"  # the waiver run is nearer


def test_ics_draft_event_matches_stored_instant(env):
    tc, _, league, comm, _ = env
    _schedule(tc, league, comm, INSTANT_UTC)
    r = tc.get(f"/api/leagues/{league}/key-dates.ics")
    assert r.status_code == 200, r.text
    by_uid = {ev["UID"]: ev for ev in _ics_events(r.text)}
    ev = by_uid[f"draft@league-{league}.ipl-fantasy"]
    assert ev["DTSTART"] == INSTANT_BASIC
    assert ev["DTEND"] == INSTANT_BASIC_END
    assert "RRULE" not in ev


def test_ics_omits_unscheduled_draft(env):
    tc, _, league, _, _ = env
    r = tc.get(f"/api/leagues/{league}/key-dates.ics")
    assert r.status_code == 200, r.text
    uids = [ev["UID"] for ev in _ics_events(r.text)]
    assert not any(uid.startswith("draft@") for uid in uids)


def test_past_instant_flips_to_overdue_not_past(env):
    tc, _, league, comm, _ = env
    r = _schedule(tc, league, comm, PAST_INSTANT)
    assert r.status_code == 200, r.text
    entry = _draft_entry(tc, league)
    assert entry["at"] == PAST_INSTANT
    assert entry["state"] == "next-up"  # overdue: needs action, not "past"
    assert "has passed" in entry["detail"]


def test_earliest_future_instant_is_next_up(env):
    tc, _, league, comm, _ = env
    soon = (datetime.now(timezone.utc)
            + timedelta(hours=1)).isoformat()
    r = _schedule(tc, league, comm, soon)
    assert r.status_code == 200, r.text
    entry = _draft_entry(tc, league)
    assert entry["at"] == soon
    assert entry["state"] == "next-up"


def test_gating(env):
    tc, _, league, comm, other = env
    # No acting team: 422.
    r = tc.patch(f"/api/leagues/{league}/settings",
                 json={"draft_scheduled_at": INSTANT_UTC})
    assert r.status_code == 422
    # Non-commissioner team with its own claim: 403.
    r = _schedule(tc, league, other, INSTANT_UTC, claim="sekrit-b")
    assert r.status_code == 403, r.text
    # Commissioner's team with a wrong claim: 403.
    r = _schedule(tc, league, comm, INSTANT_UTC, claim="nope")
    assert r.status_code == 403, r.text
    # Nothing stuck: still unscheduled.
    assert _draft_entry(tc, league)["at"] is None
    # Right team + right claim: 200.
    r = _schedule(tc, league, comm, INSTANT_UTC)
    assert r.status_code == 200, r.text


def test_other_settings_stay_ungated(env):
    tc, _, league, _, _ = env
    r = tc.patch(f"/api/leagues/{league}/settings",
                 json={"pick_clock_secs": 60})
    assert r.status_code == 200, r.text
    assert r.json()["settings"]["pick_clock_secs"] == 60


def test_invalid_instants_rejected(env):
    tc, _, league, comm, _ = env
    for bad in ("2027-03-01T19:00:00", "not-a-date", "2027-13-99"):
        r = _schedule(tc, league, comm, bad)
        assert r.status_code == 422, (bad, r.text)


def test_schedule_locks_once_draft_starts(env):
    tc, db_path, league, comm, _ = env
    con = sqlite3.connect(str(db_path))
    con.execute("UPDATE leagues SET status = 'drafting' WHERE id = ?",
                (league,))
    con.commit()
    con.close()
    r = _schedule(tc, league, comm, INSTANT_UTC)
    assert r.status_code == 422, r.text
    # And the draft entry no longer carries a schedule.
    assert _draft_entry(tc, league)["at"] is None


def test_clear_schedule(env):
    tc, _, league, comm, _ = env
    assert _schedule(tc, league, comm, INSTANT_UTC).status_code == 200
    assert _draft_entry(tc, league)["at"] == INSTANT_UTC
    r = _schedule(tc, league, comm, "")
    assert r.status_code == 200, r.text
    assert "draft_scheduled_at" not in r.json()["settings"]
    entry = _draft_entry(tc, league)
    assert entry["at"] is None
    assert entry["state"] == "upcoming"
    r = tc.get(f"/api/leagues/{league}/key-dates.ics")
    uids = [ev["UID"] for ev in _ics_events(r.text)]
    assert not any(uid.startswith("draft@") for uid in uids)
