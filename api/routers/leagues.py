"""Leagues: create, read (+standings), join, list teams."""

import json
import secrets
import sqlite3
import string

from fastapi import APIRouter, Depends, HTTPException, Query

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
        "pick_clock_secs": 90,
    }


@router.get("", response_model=list[schemas.LeagueSummaryOut])
def list_leagues(con: sqlite3.Connection = Depends(get_db)):
    """All leagues (id/name/season/status/team count) — powers the web
    league switcher (P4-W7)."""
    return [
        schemas.LeagueSummaryOut(
            id=r["id"], name=r["name"], season=r["season"], status=r["status"],
            team_count=r["team_count"],
        )
        for r in con.execute(
            "SELECT l.*, (SELECT COUNT(*) FROM teams t WHERE t.league_id = l.id)"
            " AS team_count FROM leagues l ORDER BY l.id"
        )
    ]


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


@router.patch("/{league_id}/settings", response_model=schemas.LeagueOut)
def patch_league_settings(league_id: int, body: schemas.LeagueSettingsPatch,
                          con: sqlite3.Connection = Depends(get_db)):
    """Commissioner settings edit (P4-W15). Ungated until team identity
    lands (P4-W18); only the patchable keys are applied."""
    league = get_league(con, league_id)
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(422, "no settings supplied")
    settings = dict(league["settings"] or {})
    settings.update(updates)
    con.execute("UPDATE leagues SET settings = ? WHERE id = ?",
                (json.dumps(settings), league_id))
    con.commit()
    league = get_league(con, league_id)
    return schemas.LeagueOut(**{k: league[k] for k in ("id", "name", "invite_code", "season", "status", "settings")})


@router.post("/{league_id}/adjustments", response_model=schemas.AdjustmentOut)
def create_adjustment(league_id: int, body: schemas.AdjustmentCreate,
                      con: sqlite3.Connection = Depends(get_db)):
    """Manual FAAB adjustment with a mandatory audit note (P4-W15)."""
    get_league(con, league_id)  # 404 if missing
    team = get_team(con, body.team_id)
    if team["league_id"] != league_id:
        raise HTTPException(422, "team is not in this league")
    faab_after = max(0, team["faab_remaining"] + body.faab_delta)
    con.execute("UPDATE teams SET faab_remaining = ? WHERE id = ?",
                (faab_after, team["id"]))
    cur = con.execute(
        "INSERT INTO league_adjustments (league_id, team_id, kind, faab_delta, faab_after, note)"
        " VALUES (?, ?, 'faab', ?, ?, ?)",
        (league_id, team["id"], body.faab_delta, faab_after, body.note),
    )
    con.commit()
    row = con.execute("SELECT * FROM league_adjustments WHERE id = ?", (cur.lastrowid,)).fetchone()
    return schemas.AdjustmentOut(
        id=row["id"], league_id=row["league_id"], team_id=row["team_id"],
        team_name=team["name"], kind=row["kind"], faab_delta=row["faab_delta"],
        faab_after=row["faab_after"], note=row["note"], created_at=row["created_at"],
    )


@router.get("/{league_id}/adjustments", response_model=list[schemas.AdjustmentOut])
def list_adjustments(league_id: int, con: sqlite3.Connection = Depends(get_db)):
    get_league(con, league_id)  # 404 if missing
    return [
        schemas.AdjustmentOut(
            id=r["id"], league_id=r["league_id"], team_id=r["team_id"],
            team_name=r["team_name"], kind=r["kind"], faab_delta=r["faab_delta"],
            faab_after=r["faab_after"], note=r["note"], created_at=r["created_at"],
        )
        for r in con.execute(
            "SELECT a.*, t.name AS team_name FROM league_adjustments a"
            " JOIN teams t ON t.id = a.team_id WHERE a.league_id = ?"
            " ORDER BY a.id DESC LIMIT 50",
            (league_id,),
        )
    ]


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


@router.get("/{league_id}/schedule-nudges", response_model=schemas.ScheduleNudgesOut)
def schedule_nudges(league_id: int, week_no: int = Query(1, ge=1),
                    con: sqlite3.Connection = Depends(get_db)):
    """P3-A6 (D10 option 4): per-IPL-team game counts for a fantasy week.

    Powers the draft-room and waiver-wire schedule badges. Empty `games`
    (plus `weeks_available`) when the fixture hasn't been imported yet —
    the importer is api/schedule_games.py.
    """
    league = get_league(con, league_id)  # 404 if missing
    from .. import schedule_games
    data = schedule_games.fetch_week(con, league["season"], week_no)
    return schemas.ScheduleNudgesOut(league_id=league_id, **data)


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


@router.get("/{league_id}/draft", response_model=schemas.DraftOut)
def get_league_draft(league_id: int, con: sqlite3.Connection = Depends(get_db)):
    """The league's most recent draft (for the draft room); 404 if none."""
    get_league(con, league_id)  # 404 if missing
    d = services.get_league_draft(con, league_id)
    if d is None:
        raise HTTPException(404, f"league {league_id} has no draft yet")
    return schemas.DraftOut(
        id=d["id"], league_id=d["league_id"], rounds=d["rounds"],
        status=d["status"], current_pick_no=d["current_pick_no"],
        draft_order=d["draft_order"],
        on_clock_team_id=d.get("on_clock_team_id"),
    )
