"""Key dates & deadlines calendar (P5-W27).

GET /api/leagues/{id}/key-dates projects every "when does what
happen" answer from the exact source that enforces it — never a
second copy: weekly lineup locks come from lineup_lock_at (the P4-W8
D5 enforcement seam), the waiver run from the league's
waiver_run_weekday setting + the scheduler's 03:00 PT rule, the trade
deadline from the trade_deadline_week setting (its instant = that
week's lock), the draft from league/draft status + pick_clock_secs
(+ the commissioner's scheduled instant, P5-W51), and the playoffs
from D9 weeks 7-8. Dates render in PT and IST; each entry is past /
next-up / upcoming relative to now. Read-only.
"""

import sqlite3
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse

from .. import schemas, schedule_games
from ..constants import PLAYOFF_WEEKS, TOTAL_WEEKS
from ..database import get_db
from . import get_league
from .lineups import lineup_lock_at

router = APIRouter()

_PT = ZoneInfo("America/Los_Angeles")
_IST = ZoneInfo("Asia/Kolkata")
_WEEKDAYS = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
             "friday": 4, "saturday": 5, "sunday": 6}


def _fmt(dt: datetime | None, tz: ZoneInfo) -> str | None:
    return dt.astimezone(tz).strftime("%a %b %d, %Y %H:%M %Z") if dt else None


def _draft_scheduled_at(settings: dict) -> datetime | None:
    """P5-W51: the commissioner's draft instant (UTC) from league
    settings, or None when unscheduled / unparseable. Stored values
    are normalized by the PATCH endpoint; this stays defensive."""
    raw = settings.get("draft_scheduled_at")
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw)
    except (ValueError, TypeError):
        return None
    if dt.tzinfo is None:
        return None
    return dt.astimezone(timezone.utc)


def build_key_dates(league_id: int,
                    con: sqlite3.Connection) -> schemas.KeyDatesOut:
    """The one key-dates projection (P5-W27). The JSON endpoint and
    the P5-W35 .ics export both render THIS — never a second date
    computation."""
    league = get_league(con, league_id)  # 404 if missing
    settings = league["settings"] or {}  # get_league parses the JSON
    weekday_name = str(settings.get("waiver_run_weekday", "wednesday")).lower()
    deadline_week = int(settings.get("trade_deadline_week", 6))
    pick_clock = int(settings.get("pick_clock_secs", 90))
    now = datetime.now(timezone.utc)

    dated: list[tuple[datetime | None, schemas.KeyDateEntryOut]] = []

    def add(key, label, detail, at):
        dated.append((at, schemas.KeyDateEntryOut(
            key=key, label=label, detail=detail,
            at=at.isoformat() if at else None,
            at_pt=_fmt(at, _PT), at_ist=_fmt(at, _IST), state="upcoming")))

    locks = {wk: lineup_lock_at(con, league_id, wk)
             for wk in range(1, TOTAL_WEEKS + 1)}
    for wk in range(1, TOTAL_WEEKS + 1):
        detail = "Lineups lock at the week's first ball (D5)."
        if wk in PLAYOFF_WEEKS:
            detail += " Playoff week (D9)."
        add(f"lineup_lock_{wk}", f"Week {wk} lineup lock", detail, locks[wk])
    # Waiver run: next occurrence of the configured weekday at 03:00 PT
    # (the waiver_scheduler rule), a recurring weekly entry.
    target = _WEEKDAYS.get(weekday_name, 2)
    today_pt = now.astimezone(_PT).date()
    delta = (target - today_pt.weekday()) % 7
    run_day = today_pt + timedelta(days=delta)
    run_at = datetime.combine(run_day, time(3, 0), tzinfo=_PT)
    if run_at <= now:
        run_at += timedelta(days=7)
    add("waiver_run",
        f"Waiver run ({weekday_name.capitalize()}s, weekly)",
        "Blind FAAB bids resolve at ~03:00 PT on the configured weekday (D6).",
        run_at.astimezone(timezone.utc))
    add("trade_deadline", f"Trade deadline (end of week {deadline_week})",
        "Proposals close at that week's lineup lock; the review window "
        "still applies to trades accepted before it.",
        locks.get(deadline_week))
    add("playoffs", "Playoffs begin (week 7)",
        "Top 4 seeds play off over weeks 7-8 (D9).", locks.get(PLAYOFF_WEEKS[0]))

    # State pass over dated entries: past < now; the earliest future
    # dated entry is next-up; the rest are upcoming. A scheduled draft
    # (P5-W51) joins the dated set while the league is still in setup.
    status = league["status"]
    draft_at = (_draft_scheduled_at(settings)
                if status == "setup" else None)
    future = [at for at, _ in dated if at is not None and at >= now]
    if draft_at is not None and draft_at >= now:
        future.append(draft_at)
    next_up_at = min(future) if future else None
    entries: list[schemas.KeyDateEntryOut] = []
    if status == "drafting":
        draft_state, draft_detail = "next-up", "Draft is live now."
    elif status != "setup":
        draft_state, draft_detail = "past", "Draft complete."
    elif draft_at is None:
        draft_state, draft_detail = (
            "upcoming",
            "Not started yet — the commissioner starts it from the "
            "league page.")
    elif draft_at < now:
        # The instant passed but the draft never started: overdue, not
        # "past" — it is the thing needing action.
        draft_state, draft_detail = (
            "next-up",
            "Scheduled time has passed — start the draft from the "
            "league page.")
    elif draft_at == next_up_at:
        draft_state, draft_detail = (
            "next-up", "Commissioner-scheduled — not started yet.")
    else:
        draft_state, draft_detail = (
            "upcoming", "Commissioner-scheduled — not started yet.")
    entries.append(schemas.KeyDateEntryOut(
        key="draft", label="Snake draft",
        detail=f"Pick clock {pick_clock}s per pick. {draft_detail}",
        at=draft_at.isoformat() if draft_at else None,
        at_pt=_fmt(draft_at, _PT), at_ist=_fmt(draft_at, _IST),
        state=draft_state))
    for at, entry in sorted(dated, key=lambda x: (x[0] is None, x[0])):
        if at is not None:
            entry.state = ("past" if at < now else
                           "next-up" if at == next_up_at else "upcoming")
        entries.append(entry)
    return schemas.KeyDatesOut(league_id=league_id, entries=entries)


@router.get("/{league_id}/key-dates", response_model=schemas.KeyDatesOut)
def key_dates(league_id: int, con: sqlite3.Connection = Depends(get_db)):
    return build_key_dates(league_id, con)


# ---------- P5-W35: iCalendar export of the same projection ----------

def _ics_escape(text: str) -> str:
    return (text.replace("\\", "\\\\").replace(";", "\\;")
            .replace(",", "\\,").replace("\n", "\\n"))


def _ics_dt(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _is_standin(con: sqlite3.Connection, league_id: int,
                entry: schemas.KeyDateEntryOut) -> bool:
    """True when a lock-derived entry's instant came from the stand-in
    calendar rather than an imported fixture row: the seam's fixture
    lookup for that week has no week_start, or its source says so.
    Only called for lineup_lock_N / trade_deadline / playoffs keys."""
    week_no = None
    if entry.key.startswith("lineup_lock_"):
        week_no = int(entry.key.rsplit("_", 1)[1])
    elif entry.key == "trade_deadline":
        # The deadline entry's instant IS a lock instant; match it.
        week_no = next(
            (wk for wk in range(1, TOTAL_WEEKS + 1)
             if lineup_lock_at(con, league_id, wk) is not None
             and entry.at == lineup_lock_at(con, league_id, wk).isoformat()),
            None)
    elif entry.key == "playoffs":
        week_no = PLAYOFF_WEEKS[0]
    if week_no is None:
        return False
    season = get_league(con, league_id)["season"]
    week = schedule_games.fetch_week(con, season, week_no)
    return not week.get("week_start") or "standin" in (week.get("source") or "")


@router.get("/{league_id}/key-dates.ics")
def key_dates_ics(league_id: int,
                  con: sqlite3.Connection = Depends(get_db)):
    """RFC 5545 rendering of build_key_dates — every VEVENT instant
    is the payload's `at` for the same league, in UTC. A draft with no
    scheduled instant (P5-W51) is omitted (a VEVENT requires a
    DTSTART); a scheduled draft renders as a VEVENT at its stored
    instant. The single weekly waiver-run entry becomes a weekly
    RRULE event from its projected next run. Lock-derived events
    carry the standin note when their date is a stand-in."""
    payload = build_key_dates(league_id, con)  # 404 if missing
    stamp = _ics_dt(datetime.now(timezone.utc))
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//IPL Fantasy//Key Dates//EN",
        "CALSCALE:GREGORIAN",
    ]
    for entry in payload.entries:
        if entry.at is None:
            continue  # no instant (e.g. unscheduled draft) — cannot be a VEVENT
        start = datetime.fromisoformat(entry.at)
        description = entry.detail
        if entry.key != "waiver_run" and _is_standin(con, league_id, entry):
            description += (" Standin date — based on the stand-in "
                            "calendar until the real fixture imports.")
        lines += [
            "BEGIN:VEVENT",
            f"UID:{entry.key}@league-{league_id}.ipl-fantasy",
            f"DTSTAMP:{stamp}",
            f"DTSTART:{_ics_dt(start)}",
            f"DTEND:{_ics_dt(start + timedelta(minutes=30))}",
        ]
        if entry.key == "waiver_run":
            lines.append("RRULE:FREQ=WEEKLY")
        lines += [
            f"SUMMARY:{_ics_escape(entry.label)}",
            f"DESCRIPTION:{_ics_escape(description)}",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return PlainTextResponse(
        "\r\n".join(lines) + "\r\n", media_type="text/calendar",
        headers={"Content-Disposition":
                 f'attachment; filename="key-dates-league-{league_id}.ics"'})
