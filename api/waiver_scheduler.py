"""Waiver-run scheduler (P4-W16).

POST /api/waivers/run existed but nothing ever called it — in a live
season, FAAB claims would sit pending forever. This module is the
trigger: an hourly in-process sweeper (same pattern as the draft
clock sweeper) that runs each in-season league's weekly FAAB once
its run moment has passed.

A league-week is DUE when:
  * the league is in_season,
  * it has pending claims for that week, and
  * now >= the league's configured run weekday (settings
    ``waiver_run_weekday``, default Wednesday) at 03:00 PT in that
    fantasy week's Mon–Sun window — dates from the imported fixture
    table for the league's season when present, else the engine
    FANTASY_WEEKS calendar (the same seam as the D5 lineup lock).

Idempotent: a resolved week has no pending claims, so it is never
re-run. One league's failure is logged and skipped, never fatal to
the loop. Ops alternative to the in-process sweeper: cron a POST to
/api/waivers/run?league_id=<id>&week_no=<n> — same code path.
"""

import asyncio
import json
import logging
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from . import schedule_games, services
from .engine.matchup_scheduler import FANTASY_WEEKS

log = logging.getLogger("api.waiver_scheduler")

_PT = ZoneInfo("America/Los_Angeles")
_RUN_TIME = time(3, 0)  # ~3am PT, per the waivers page copy
_WEEKDAY_OFFSET = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}
_TICK_SECONDS = 3600


def _week_window(con, season: str, week_no: int) -> tuple[date, date] | None:
    wk = schedule_games.fetch_week(con, season, week_no)
    if wk.get("week_start") and wk.get("week_end"):
        return date.fromisoformat(wk["week_start"]), date.fromisoformat(wk["week_end"])
    rng = FANTASY_WEEKS.get(week_no)
    if not rng:
        return None
    return date.fromisoformat(rng[0]), date.fromisoformat(rng[1])


def due_runs(con, now: datetime | None = None) -> list[tuple[int, int]]:
    """[(league_id, week_no)] whose FAAB run is due (see module doc)."""
    now = now or datetime.now(timezone.utc)
    out: list[tuple[int, int]] = []
    for league in con.execute(
        "SELECT id, season, settings FROM leagues WHERE status = 'in_season'"
    ):
        try:
            settings = json.loads(league["settings"] or "{}")
        except (TypeError, ValueError):
            settings = {}
        offset = _WEEKDAY_OFFSET.get(
            str(settings.get("waiver_run_weekday", "wednesday")).lower(), 2)
        weeks = [r[0] for r in con.execute(
            "SELECT DISTINCT week_no FROM waiver_claims"
            " WHERE league_id = ? AND status = 'pending'", (league["id"],))]
        for week_no in weeks:
            window = _week_window(con, league["season"], week_no)
            if window is None:
                continue
            run_day = window[0] + timedelta(days=offset)  # week_start is Monday
            due = datetime.combine(run_day, _RUN_TIME, tzinfo=_PT)
            if now >= due.astimezone(timezone.utc):
                out.append((league["id"], week_no))
    return out


def run_due(con, now: datetime | None = None) -> list[dict]:
    """Run every due league-week; per-league failures are contained."""
    results = []
    for league_id, week_no in due_runs(con, now):
        try:
            processed = services.run_waivers(con, league_id, week_no)
            results.append({"league_id": league_id, "week_no": week_no,
                            "processed": len(processed)})
            log.info("waiver run league=%s week=%s processed=%s",
                     league_id, week_no, len(processed))
        except Exception as e:  # one bad league must not stop the rest
            log.exception("waiver run failed league=%s week=%s", league_id, week_no)
            results.append({"league_id": league_id, "week_no": week_no,
                            "error": str(e)})
    return results


async def waiver_run_sweeper() -> None:
    from .database import connect

    while True:
        try:
            with connect() as con:
                run_due(con)
        except Exception:
            log.exception("waiver scheduler tick failed")
        await asyncio.sleep(_TICK_SECONDS)


def start_sweeper() -> asyncio.Task:
    return asyncio.create_task(waiver_run_sweeper())
