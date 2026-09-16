"""Leagues: create, read (+standings), join, list teams."""

import json
import secrets
import sqlite3
import string

from fastapi import APIRouter, Depends, HTTPException

from .. import schemas, services
from ..constants import FAAB_BUDGET
from ..database import get_db
from . import get_league, get_team, row_dict

router = APIRouter()


def _invite_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(6))


def _default_settings() -> dict:
    from ..constants import (
        DRAFT_ROUNDS,
        OVERSEAS_STARTER_CAP,
        PLAYOFF_TEAMS,
        ROSTER_SLOTS,
        SCORING_TABLE_VERSION,
    )

    return {
        "draft_type": "snake",
        "rounds": DRAFT_ROUNDS,
        "roster_slots": dict(ROSTER_SLOTS),
        "faab_budget": FAAB_BUDGET,
        "scoring_table_version": SCORING_TABLE_VERSION,
        "overseas_cap": OVERSEAS_STARTER_CAP,
        "playoff_teams": PLAYOFF_TEAMS,
        "trade_deadline_week": 6,
        "waiver_run_weekday": "wednesday",
    }


@router.post("", response_model=schemas.LeagueOut)
def create_league(body: schemas.LeagueCreate, con: sqlite3.Connection = Depends(get_db)):
    owner = con.execute("INSERT INTO users (name) VALUES (?)", (body.commissioner_name,)).lastrowid
    code = _invite_code()
    cur = con.execute(
        "INSERT INTO leagues (name, invite_code, commissioner_id, season, settings, status)"
        " VALUES (?, ?, ?, ?, ?, 'setup')",
        (body.name, code, owner, body.season, json.dumps(_default_settings())),
    )
    con.commit()
    league = get_league(con, cur.lastrowid)
    return schemas.LeagueOut(**{k: league[k] for k in ("id", "name", "invite_code", "season", "status", "settings")})


@router.get("/{league_id}", response_model=schemas.LeagueDetailOut)
def get_league_detail(league_id: int, con: sqlite3.Connection = Depends(get_db)):
    league = get_league(con, league_id)
    standings = []
    for t in con.execute(
        """SELECT t.*, u.name AS owner_name FROM teams t
           LEFT JOIN users u ON u.id = t.owner_id WHERE t.league_id = ? ORDER BY t.name""",
        (league_id,),
    ):
        # W-L-T derives from finalized matchups; scaffold has none final yet.
        w = con.execute(
            """SELECT
                 SUM(CASE WHEN (team_a_id = ? AND score_a > score_b) OR (team_b_id = ? AND score_b > score_a) THEN 1 ELSE 0 END),
                 SUM(CASE WHEN (team_a_id = ? AND score_a < score_b) OR (team_b_id = ? AND score_b < score_a) THEN 1 ELSE 0 END),
                 SUM(CASE WHEN status = 'final' AND score_a = score_b AND (team_a_id = ? OR team_b_id = ?) THEN 1 ELSE 0 END),
                 SUM(CASE WHEN team_a_id = ? THEN score_a WHEN team_b_id = ? THEN score_b ELSE 0 END)
               FROM matchups WHERE league_id = ? AND status = 'final'""",
            (t["id"], t["id"], t["id"], t["id"], t["id"], t["id"], t["id"], t["id"], league_id),
        ).fetchone()
        standings.append(
            schemas.TeamStandingOut(
                team_id=t["id"], team_name=t["name"], owner_name=t["owner_name"],
                wins=w[0] or 0, losses=w[1] or 0, ties=w[2] or 0,
                points_for=w[3] or 0.0, faab_remaining=t["faab_remaining"],
            )
        )
    return schemas.LeagueDetailOut(
        id=league["id"], name=league["name"], invite_code=league["invite_code"],
        season=league["season"], status=league["status"], settings=league["settings"],
        standings=standings,
    )


@router.post("/{league_id}/join", response_model=schemas.TeamOut)
def join_league(league_id: int, body: schemas.JoinLeagueIn, con: sqlite3.Connection = Depends(get_db)):
    league = get_league(con, league_id)
    if body.invite_code != league["invite_code"]:
        raise HTTPException(403, "invalid invite code")
    if league["status"] != "setup":
        raise HTTPException(409, f"league is {league['status']}; joins closed")
    owner = con.execute("INSERT INTO users (name) VALUES (?)", (body.owner_name,)).lastrowid
    try:
        cur = con.execute(
            "INSERT INTO teams (league_id, owner_id, name, faab_remaining) VALUES (?, ?, ?, ?)",
            (league_id, owner, body.team_name, FAAB_BUDGET),
        )
    except sqlite3.IntegrityError:
        raise HTTPException(409, f"team name '{body.team_name}' taken in this league")
    con.commit()
    team = get_team(con, cur.lastrowid)
    return schemas.TeamOut(
        id=team["id"], league_id=team["league_id"], name=team["name"],
        owner_name=team["owner_name"], faab_remaining=team["faab_remaining"],
    )


@router.get("/{league_id}/teams", response_model=list[schemas.TeamOut])
def list_teams(league_id: int, con: sqlite3.Connection = Depends(get_db)):
    get_league(con, league_id)  # 404 if missing
    out = []
    for t in con.execute(
        """SELECT t.*, u.name AS owner_name FROM teams t
           LEFT JOIN users u ON u.id = t.owner_id WHERE t.league_id = ? ORDER BY t.name""",
        (league_id,),
    ):
        out.append(schemas.TeamOut(
            id=t["id"], league_id=t["league_id"], name=t["name"],
            owner_name=t["owner_name"], faab_remaining=t["faab_remaining"],
        ))
    return out


@router.post("/{league_id}/draft/start", response_model=schemas.DraftOut)
def start_draft(league_id: int, con: sqlite3.Connection = Depends(get_db)):
    """Start the snake draft (P3-A2: engine-backed). Moved here from the
    drafts router so the path matches the README contract
    POST /api/leagues/{id}/draft/start (was /api/drafts/leagues/...)."""
    get_league(con, league_id)  # 404 if missing
    d = services.start_draft(con, league_id)
    return schemas.DraftOut(
        id=d["id"], league_id=d["league_id"], rounds=d["rounds"],
        status=d["status"], current_pick_no=d["current_pick_no"],
        draft_order=d["draft_order"],
        on_clock_team_id=d.get("on_clock_team_id"),
    )
