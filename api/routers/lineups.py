"""Lineups: weekly XI. Slot + overseas-cap validation is real (D7/D8
locked), and the weekly lock (D5) is enforced on PUT: lineups lock at
the week's first ball (P4-W8, closing the P2-L2 seam).
GET carries the most recent saved lineup forward into unsaved weeks so a
manager never starts from an empty XI (P4-W5)."""

import sqlite3
from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Request

from .. import schedule_games, schemas
from ..constants import STARTER_SLOTS, TOTAL_WEEKS
from ..database import get_db
from ..engine.matchup_scheduler import FANTASY_WEEKS
from ..engine.sandbox_season import solve_best_d8_lineup
from ..validation import LineupError, validate_lineup
from . import get_league, get_team, player_roles_map, require_team_actor

router = APIRouter()

TRACK = "P2-L2"

# D5: lineups lock at the week's first ball. The fixture data carries
# dates only (team_weekly_games), so the lock instant is the week's
# Monday at 19:30 IST — the standard IPL evening start — as a stand-in
# until the real 2027 fixture (with start times) imports ~Feb 2027.
_FIRST_BALL = time(19, 30)
_IST = ZoneInfo("Asia/Kolkata")


def lineup_lock_at(con: sqlite3.Connection, league_id: int, week_no: int) -> datetime | None:
    """The week's lock instant (aware, UTC), or None if the week has no
    known start date. The date comes from the imported fixture table
    for the league's season when present, else the engine calendar."""
    season = get_league(con, league_id)["season"]
    week = schedule_games.fetch_week(con, season, week_no)
    start = week.get("week_start") or (FANTASY_WEEKS.get(week_no) or (None, None))[0]
    if not start:
        return None
    day = datetime.fromisoformat(str(start)).date()
    return datetime.combine(day, _FIRST_BALL, tzinfo=_IST).astimezone(timezone.utc)


@router.put("/teams/{team_id}/lineup", response_model=schemas.LineupOut)
def set_lineup(team_id: int, body: schemas.LineupSet, request: Request,
               con: sqlite3.Connection = Depends(get_db)):
    # P4-W18: a claimed team requires its claim code to be set by anyone else.
    team = require_team_actor(con, team_id, request)
    if not 1 <= body.week_no <= TOTAL_WEEKS:
        raise HTTPException(422, f"week_no must be 1..{TOTAL_WEEKS}")

    # D5 weekly lock: no edits once the week's first ball is due.
    lock = lineup_lock_at(con, team["league_id"], body.week_no)
    if lock is not None and datetime.now(timezone.utc) >= lock:
        raise HTTPException(
            422,
            f"lineup for week {body.week_no} is locked — lineups lock at the"
            f" week's first ball ({lock.isoformat()}, D5)",
        )

    roles = player_roles_map(con)
    try:
        summary = validate_lineup(body.slots, roles)
    except LineupError as e:
        raise HTTPException(422, str(e))

    # Ownership check: every player must be on this team's roster (construction state).
    owned_ids = {
        r["player_id"] for r in con.execute(
            "SELECT player_id FROM roster_slots WHERE team_id = ? AND week_no IS NULL", (team_id,)
        )
    }
    for slot, pids in body.slots.items():
        for pid in pids:
            if pid not in owned_ids:
                raise HTTPException(422, f"player {pid} is not on team {team_id}'s roster")

    # Replace this week's snapshot.
    con.execute("DELETE FROM roster_slots WHERE team_id = ? AND week_no = ?", (team_id, body.week_no))
    for slot, pids in body.slots.items():
        for pid in pids:
            con.execute(
                "INSERT INTO roster_slots (team_id, player_id, slot, week_no) VALUES (?, ?, ?, ?)",
                (team_id, pid, slot, body.week_no),
            )
    con.commit()
    return schemas.LineupOut(
        team_id=team_id, week_no=body.week_no, slots=body.slots,
        overseas_starters=summary["overseas_starters"], valid=True,
        # The save just succeeded, so the week is by definition unlocked;
        # still report the lock instant so clients can show it.
        locked=False, lock_at=lock.isoformat() if lock else None,
        player_availability={
            pid: roles.get(pid, {}).get("availability", "active")
            for pids in body.slots.values() for pid in pids
        },
    )


@router.get("/teams/{team_id}/lineup/suggestion",
            response_model=schemas.LineupSuggestionOut)
def get_lineup_suggestion(team_id: int, week_no: int,
                          con: sqlite3.Connection = Depends(get_db)):
    """P5-W13 Suggested XI: project the P2-L7 exact best-ADP D8-legal
    solver (the same one that auto-sets week 1 at draft completion) over
    the team's current construction roster for week_no. Read-only —
    zero writes; the manager still saves through PUT, so the D5 lock,
    D7 IL-eligibility and D8 cap checks stay exactly as enforced there.
    Players currently holding the IL slot in the requested week's saved
    lineup are excluded from the suggestion (they are out)."""
    team = get_team(con, team_id)
    if not 1 <= week_no <= TOTAL_WEEKS:
        raise HTTPException(422, f"week_no must be 1..{TOTAL_WEEKS}")
    league = get_league(con, team["league_id"])
    roster = [
        r["player_id"] for r in con.execute(
            "SELECT player_id FROM roster_slots"
            " WHERE team_id = ? AND week_no IS NULL", (team_id,))
    ]
    if len(roster) < 11:
        raise HTTPException(
            422, f"team {team_id} has {len(roster)} rostered players;"
                 " a suggestion needs at least 11")
    il_out = {
        r["player_id"] for r in con.execute(
            "SELECT player_id FROM roster_slots"
            " WHERE team_id = ? AND week_no = ? AND slot = 'IL'",
            (team_id, week_no))
    }
    pool = [pid for pid in roster if pid not in il_out]
    if len(pool) < 11:
        raise HTTPException(
            422, f"only {len(pool)} players are available (IL excluded);"
                 " a suggestion needs at least 11")
    roles = player_roles_map(con, league["season"])
    missing = [pid for pid in pool if pid not in roles]
    if missing:
        raise HTTPException(
            422, f"no role metadata for players {missing};"
                 " cannot compute a legal suggestion")
    adp = {
        r["player_id"]: r["r"]
        for r in con.execute(
            "SELECT player_id, MIN(rank) AS r FROM pre_draft_ranks"
            " GROUP BY player_id")
    }
    adp_index = {pid: adp.get(pid, 10 ** 9) for pid in pool}
    try:
        assignment = solve_best_d8_lineup(pool, roles, adp_index)
    except AssertionError as e:
        raise HTTPException(422, str(e))
    slots: dict[str, list[int]] = {}
    for pid, slot in assignment.items():
        slots.setdefault(slot, []).append(pid)
    # A full 15-man roster with nobody on IL leaves 4 non-starters but BN
    # holds 3 (D7): the suggestion keeps the best-ranked 3 on the bench
    # and omits the last player rather than emit an unsavable lineup.
    if len(slots.get("BN", [])) > 3:
        slots["BN"] = sorted(slots["BN"], key=lambda p: adp_index[p])[:3]
    for pid in sorted(il_out):
        slots.setdefault("IL", []).append(pid)
    try:
        summary = validate_lineup(slots, roles)
    except LineupError as e:
        raise HTTPException(422, str(e))
    lock = lineup_lock_at(con, team["league_id"], week_no)
    return schemas.LineupSuggestionOut(
        team_id=team_id, week_no=week_no, slots=slots,
        overseas_starters=summary["overseas_starters"], valid=True,
        locked=lock is not None and datetime.now(timezone.utc) >= lock,
        lock_at=lock.isoformat() if lock else None,
        player_availability={
            pid: roles.get(pid, {}).get("availability", "active")
            for pids in slots.values() for pid in pids
        },
    )


@router.get("/teams/{team_id}/lineup", response_model=schemas.LineupOut)
def get_lineup(team_id: int, week_no: int, con: sqlite3.Connection = Depends(get_db)):
    team = get_team(con, team_id)
    if not 1 <= week_no <= TOTAL_WEEKS:
        raise HTTPException(422, f"week_no must be 1..{TOTAL_WEEKS}")

    def _slots_for(wk: int) -> dict[str, list[int]]:
        out: dict[str, list[int]] = {}
        for r in con.execute(
            "SELECT slot, player_id FROM roster_slots WHERE team_id = ? AND week_no = ?",
            (team_id, wk),
        ):
            out.setdefault(r["slot"], []).append(r["player_id"])
        return out

    slots = _slots_for(week_no)
    carried_from: int | None = None
    valid = bool(slots)
    if not slots:
        # Carry-over (P4-W5): prefill from the most recent earlier saved
        # week (week 1 is auto-set at draft completion). Players no longer
        # on the roster are dropped from the prefill; nothing is persisted
        # until the manager saves. valid reflects whether the carried XI
        # is still a complete legal lineup.
        row = con.execute(
            "SELECT MAX(week_no) AS wk FROM roster_slots"
            " WHERE team_id = ? AND week_no IS NOT NULL AND week_no < ?",
            (team_id, week_no),
        ).fetchone()
        if row and row["wk"] is not None:
            carried_from = row["wk"]
            owned = {
                r["player_id"] for r in con.execute(
                    "SELECT player_id FROM roster_slots"
                    " WHERE team_id = ? AND week_no IS NULL", (team_id,))
            }
            slots = {
                slot: [pid for pid in pids if pid in owned]
                for slot, pids in _slots_for(carried_from).items()
            }
            slots = {s: p for s, p in slots.items() if p}
            try:
                summary = validate_lineup(slots, player_roles_map(con))
                valid = summary["starters"] == summary["expected_starters"]
            except LineupError:
                valid = False
    roles = player_roles_map(con)
    # D8 caps overseas STARTERS at 4; bench/IL don't count.
    overseas = sum(
        1 for slot, pids in slots.items() if slot in STARTER_SLOTS for pid in pids
        if roles.get(pid, {}).get("is_overseas")
    )
    lock = lineup_lock_at(con, team["league_id"], week_no)
    return schemas.LineupOut(
        team_id=team_id, week_no=week_no, slots=slots,
        overseas_starters=overseas, valid=valid,
        carried_over_from_week=carried_from,
        locked=lock is not None and datetime.now(timezone.utc) >= lock,
        lock_at=lock.isoformat() if lock else None,
        player_availability={
            pid: roles.get(pid, {}).get("availability", "active")
            for pids in slots.values() for pid in pids
        },
    )
