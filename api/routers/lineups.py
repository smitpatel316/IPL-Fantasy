"""Lineups: weekly XI. Slot + overseas-cap validation is real (D7/D8 locked);
the weekly-lock deadline enforcement is the P2-L2 seam (marked below)."""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from .. import schemas
from ..constants import TOTAL_WEEKS
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
    slots: dict[str, list[int]] = {}
    for r in con.execute(
        "SELECT slot, player_id FROM roster_slots WHERE team_id = ? AND week_no = ?",
        (team_id, week_no),
    ):
        slots.setdefault(r["slot"], []).append(r["player_id"])
    roles = player_roles_map(con)
    overseas = sum(
        1 for pids in slots.values() for pid in pids
        if roles.get(pid, {}).get("is_overseas")
    )
    return schemas.LineupOut(
        team_id=team_id, week_no=week_no, slots=slots,
        overseas_starters=overseas, valid=bool(slots),
    )
