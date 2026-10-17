"""Key dates & deadlines calendar (P5-W27).

GET /api/leagues/{id}/key-dates projects every "when does what
happen" answer from the exact source that enforces it — never a
second copy: weekly lineup locks come from lineup_lock_at (the P4-W8
D5 enforcement seam), the waiver run from the league's
waiver_run_weekday setting + the scheduler's 03:00 PT rule, the trade
deadline from the trade_deadline_week setting (its instant = that
week's lock), the draft from league/draft status + pick_clock_secs,
and the playoffs from D9 weeks 7-8. Dates render in PT and IST; each
entry is past / next-up / upcoming relative to now. Read-only.
"""

import sqlite3
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends

from .. import schemas
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


@router.get("/{league_id}/key-dates", response_model=schemas.KeyDatesOut)
def key_dates(league_id: int, con: sqlite3.Connection = Depends(get_db)):
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
    # dated entry is next-up; the rest are upcoming.
    future = [at for at, _ in dated if at is not None and at >= now]
    next_up_at = min(future) if future else None
    entries: list[schemas.KeyDateEntryOut] = []
    status = league["status"]
    draft_state = ("past" if status not in ("setup", "drafting")
                   else "next-up" if status == "drafting" else "upcoming")
    entries.append(schemas.KeyDateEntryOut(
        key="draft", label="Snake draft",
        detail=(f"Pick clock {pick_clock}s per pick. "
                + {"setup": "Not started yet — the commissioner starts it "
                            "from the league page.",
                   "drafting": "Draft is live now."}.get(
                       status, "Draft complete.")),
        state=draft_state))
    for at, entry in sorted(dated, key=lambda x: (x[0] is None, x[0])):
        if at is not None:
            entry.state = ("past" if at < now else
                           "next-up" if at == next_up_at else "upcoming")
        entries.append(entry)
    return schemas.KeyDatesOut(league_id=league_id, entries=entries)
