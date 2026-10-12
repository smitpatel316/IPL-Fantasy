"""Lineups: weekly XI. Slot + overseas-cap validation is real (D7/D8 locked);
the weekly-lock deadline enforcement is the P2-L2 seam (marked below).
GET carries the most recent saved lineup forward into unsaved weeks so a
manager never starts from an empty XI (P4-W5)."""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from .. import schemas
from ..constants import STARTER_SLOTS, TOTAL_WEEKS
from ..database import get_db
from ..validation import LineupError, validate_lineup
from . import get_team, player_roles_map

router = APIRouter()

TRACK = "P2-L2"


@router.put("/teams/{team_id}/lineup", response_model=schemas.LineupOut)
def set_lineup(team_id: int, body: schemas.LineupSet, con: sqlite3.Connection = Depends(get_db)):
    team = get_team(con, team_id)
    if not 1 <= body.week_no <= TOTAL_WEEKS:
        raise HTTPException(422, f"week_no must be 1..{TOTAL_WEEKS}")

    # P2-L2 SEAM: enforce the weekly lock deadline here (D5 — lineup locks at the
    # first ball of the fantasy week; before that, edits are free). Scaffold
    # accepts edits unconditionally; the deadline check slots in here.
    # if _lineup_locked(team["league_id"], body.week_no): raise HTTPException(409, "lineup locked")

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
    )


@router.get("/teams/{team_id}/lineup", response_model=schemas.LineupOut)
def get_lineup(team_id: int, week_no: int, con: sqlite3.Connection = Depends(get_db)):
    get_team(con, team_id)
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
    return schemas.LineupOut(
        team_id=team_id, week_no=week_no, slots=slots,
        overseas_starters=overseas, valid=valid,
        carried_over_from_week=carried_from,
    )
