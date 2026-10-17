"""P5-W35: key-dates .ics export — the calendar renders the exact
P5-W27 projection (build_key_dates), never a second computation.

Fixture reuses the W27 seed (default settings; week-1 fixture row
with source 'standin-2026'). Assertions:
  * the body is well-formed RFC 5545 structure (CRLF, balanced
    BEGIN/END, parseable UTC DTSTARTs) via a strict mini-parser;
  * every VEVENT instant equals the key-dates endpoint's `at` for
    the same league (converted to UTC basic format);
  * the undated draft entry is omitted (no instant to render);
  * the waiver-run event carries RRULE:FREQ=WEEKLY and, after a
    settings change to friday, its instant moves with the payload;
  * standin lock events carry the standin note in DESCRIPTION.
"""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.database import get_db
from api.routers import key_dates

SCHEMA = Path(__file__).resolve().parent / "schema.sql"


def _seed(con, settings="{}"):
    con.execute("INSERT INTO users (name) VALUES ('w35-owner')")
    league = con.execute(
        "INSERT INTO leagues (name, invite_code, commissioner_id,"
        " season, settings, status) VALUES ('w35', 'CODE-w35', 1,"
        " '2027', ?, 'setup')", (settings,)).lastrowid
    con.execute(
        "INSERT INTO team_weekly_games (season, week_no, week_start,"
        " week_end, ipl_team_code, games, source) VALUES ('2027', 1,"
        " '2027-03-08', '2027-03-14', 'MI', 2, 'standin-2026')")
    con.commit()
    return league


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / "ics.db"
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA.read_text())
    league = _seed(con)
    con.close()
    app = FastAPI()
    app.include_router(key_dates.router, prefix="/api/leagues")

    def override():
        c = sqlite3.connect(str(db_path))
        c.row_factory = sqlite3.Row
        try:
            yield c
        finally:
            c.close()

    app.dependency_overrides[get_db] = override
    return TestClient(app), league, db_path


def _parse_ics(text: str) -> list[dict]:
    """Strict structural parse: CRLF only, balanced VEVENT blocks,
    every DTSTART/DTEND a valid UTC basic-format instant."""
    assert "\r\n" in text and text.endswith("\r\n")
    bare = text.replace("\r\n", "")
    assert "\n" not in bare and "\r" not in bare
    lines = text.split("\r\n")[:-1]
    assert lines[0] == "BEGIN:VCALENDAR" and lines[-1] == "END:VCALENDAR"
    events, cur = [], None
    for line in lines:
        if line == "BEGIN:VEVENT":
            assert cur is None
            cur = {}
        elif line == "END:VEVENT":
            assert cur is not None and "DTSTART" in cur and "SUMMARY" in cur
            events.append(cur)
            cur = None
        elif cur is not None and ":" in line:
            k, v = line.split(":", 1)
            cur[k] = v
    assert cur is None
    for ev in events:
        for k in ("DTSTART", "DTEND", "DTSTAMP"):
            datetime.strptime(ev[k], "%Y%m%dT%H%M%SZ")  # raises if bad
    return events


def _basic(iso: str) -> str:
    return datetime.fromisoformat(iso).astimezone(timezone.utc).strftime(
        "%Y%m%dT%H%M%SZ")


def test_ics_matches_key_dates_payload(client):
    tc, league, _ = client
    payload = tc.get(f"/api/leagues/{league}/key-dates").json()
    r = tc.get(f"/api/leagues/{league}/key-dates.ics")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("text/calendar")
    assert "attachment" in r.headers["content-disposition"]
    events = _parse_ics(r.text)
    by_uid = {ev["UID"]: ev for ev in events}
    dated = [e for e in payload["entries"] if e["at"]]
    assert len(events) == len(dated)  # undated draft entry omitted
    assert not any("draft" in uid for uid in by_uid)
    for e in dated:
        ev = by_uid[f"{e['key']}@league-{league}.ipl-fantasy"]
        assert ev["DTSTART"] == _basic(e["at"]), e["key"]
        assert ev["SUMMARY"] == e["label"].replace(",", "\\,")
    # Weekly waiver run recurs from its projected instant.
    assert by_uid[f"waiver_run@league-{league}.ipl-fantasy"]["RRULE"] == "FREQ=WEEKLY"
    # Standin note on lock-derived events (week 1 source is
    # 'standin-2026'; weeks 2-8 have no fixture row at all).
    assert "Standin date" in by_uid[f"lineup_lock_1@league-{league}.ipl-fantasy"]["DESCRIPTION"]
    assert "Standin date" in by_uid[f"lineup_lock_8@league-{league}.ipl-fantasy"]["DESCRIPTION"]
    assert "Standin date" not in by_uid[f"waiver_run@league-{league}.ipl-fantasy"]["DESCRIPTION"]
    assert tc.get("/api/leagues/99999/key-dates.ics").status_code == 404


def test_ics_follows_settings_change(client):
    tc, league, db_path = client
    con = sqlite3.connect(str(db_path))
    con.execute("UPDATE leagues SET settings = ? WHERE id = ?",
                (json.dumps({"waiver_run_weekday": "friday",
                             "trade_deadline_week": 4}), league))
    con.commit()
    con.close()
    payload = tc.get(f"/api/leagues/{league}/key-dates").json()
    entries = {e["key"]: e for e in payload["entries"]}
    assert entries["trade_deadline"]["at"] == entries["lineup_lock_4"]["at"]
    events = _parse_ics(tc.get(f"/api/leagues/{league}/key-dates.ics").text)
    by_uid = {ev["UID"]: ev for ev in events}
    assert by_uid[f"waiver_run@league-{league}.ipl-fantasy"]["DTSTART"] == _basic(
        entries["waiver_run"]["at"])
    assert "Friday" in by_uid[f"waiver_run@league-{league}.ipl-fantasy"]["SUMMARY"]
    assert by_uid[f"trade_deadline@league-{league}.ipl-fantasy"]["DTSTART"] == _basic(
        entries["lineup_lock_4"]["at"])
