"""Leagues: create, read (+standings), join, list teams."""

import json
import secrets
import sqlite3
import string

from fastapi import APIRouter, Depends, HTTPException, Query

from .. import schemas, services
from ..constants import FAAB_BUDGET, TOTAL_WEEKS
from ..database import get_db
from . import get_league, get_team, new_claim_code, row_dict

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


def _standings_sort_key(s: schemas.TeamStandingOut) -> tuple:
    """Standings order, best first (P4-W27).

    Mirrors the tiebreak chain in engine/matchup_scheduler.standings()
    (wins desc, losses asc, points-for desc) with ties desc in between
    (a tie outranks a loss): the scheduler's later steps — head-to-head
    win% among the tied group and its seeded coin-flip — are not
    derivable from this endpoint's per-team aggregates, and the
    playoffs projection's final fallback (team id desc) would make
    full ties look arbitrary on the dashboard, so full ties here fall
    back to team name asc (then team id, for determinism)."""
    return (-s.wins, s.losses, -s.ties, -s.points_for,
            s.team_name.casefold(), s.team_id)


@router.get("/{league_id}", response_model=schemas.LeagueDetailOut)
def get_league_detail(league_id: int, con: sqlite3.Connection = Depends(get_db)):
    league = get_league(con, league_id)
    standings = []
    for t in con.execute(
        """SELECT t.*, u.name AS owner_name FROM teams t
           LEFT JOIN users u ON u.id = t.owner_id WHERE t.league_id = ?""",
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
                claimed=bool(t["claim_code"]),
            )
        )
    # P4-W27: rank by record, not alphabet — the web dashboard renders
    # rows (rank numbers, playoff highlighting/cut line, and the
    # my-matchup strip's default team = standings[0]) in this order.
    standings.sort(key=_standings_sort_key)
    return schemas.LeagueDetailOut(
        id=league["id"], name=league["name"], invite_code=league["invite_code"],
        season=league["season"], status=league["status"], settings=league["settings"],
        standings=standings,
        current_week=min(services.current_week(con, league_id), TOTAL_WEEKS),
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
def _cant_cut_out(con: sqlite3.Connection, league_id: int) -> schemas.CantCutOut:
    ids, source = services.cant_cut_player_ids(con, league_id)
    league = get_league(con, league_id)
    return schemas.CantCutOut(
        player_ids=sorted(ids), source=source,
        top_n=league["settings"].get("cant_cut_top_n", services.DEFAULT_CANT_CUT_TOP_N),
    )


@router.get("/{league_id}/cant-cut", response_model=schemas.CantCutOut)
def get_cant_cut(league_id: int, con: sqlite3.Connection = Depends(get_db)):
    """The effective can't-cut list (P4-W22): commissioner custom list
    when set, else the top-N preseason ranks."""
    get_league(con, league_id)
    return _cant_cut_out(con, league_id)


@router.put("/{league_id}/cant-cut", response_model=schemas.CantCutOut)
def set_cant_cut(league_id: int, body: schemas.CantCutIn,
                 con: sqlite3.Connection = Depends(get_db)):
    """Commissioner control for the can't-cut list. Send player_ids to
    set a custom list ([] = feature off), player_ids=null to clear back
    to the top-N default, and/or top_n (0-50) to size the default."""
    league = get_league(con, league_id)
    settings = dict(league["settings"])
    sent = body.model_fields_set
    if "top_n" in sent and body.top_n is not None:
        if not 0 <= body.top_n <= 50:
            raise HTTPException(422, "top_n must be 0..50")
        settings["cant_cut_top_n"] = body.top_n
    if "player_ids" in sent:
        if body.player_ids is None:
            settings.pop("cant_cut_player_ids", None)
        else:
            for pid in body.player_ids:
                if not con.execute("SELECT 1 FROM players WHERE id = ?", (pid,)).fetchone():
                    raise HTTPException(404, f"player {pid} not found")
            settings["cant_cut_player_ids"] = list(dict.fromkeys(body.player_ids))
    con.execute("UPDATE leagues SET settings = ? WHERE id = ?",
                (json.dumps(settings), league_id))
    con.commit()
    return _cant_cut_out(con, league_id)
@router.post("/{league_id}/roster-moves", response_model=schemas.RosterMoveOut)
def create_roster_move(league_id: int, body: schemas.RosterMoveCreate,
                       con: sqlite3.Connection = Depends(get_db)):
    """Commissioner add/drop by fiat with a mandatory audit note (P4-W25)."""
    out = services.commissioner_roster_move(
        con, league_id, body.team_id, body.player_id, body.action, body.note)
    return schemas.RosterMoveOut(**out)


@router.get("/{league_id}/roster-moves", response_model=list[schemas.RosterMoveOut])
def list_roster_moves(league_id: int, con: sqlite3.Connection = Depends(get_db)):
    get_league(con, league_id)
    return [
        schemas.RosterMoveOut(
            id=r["id"], league_id=r["league_id"], team_id=r["team_id"],
            team_name=r["team_name"], kind=r["kind"], player_id=r["player_id"],
            player_name=r["player_name"], note=r["note"],
            created_at=r["created_at"])
        for r in con.execute(
            "SELECT a.*, t.name AS team_name FROM league_adjustments a"
            " JOIN teams t ON t.id = a.team_id"
            " WHERE a.league_id = ? AND a.kind IN ('roster_add', 'roster_drop')"
            " ORDER BY a.id DESC LIMIT 50",
            (league_id,))
    ]


@router.post("/{league_id}/join", response_model=schemas.TeamOut)
def join_league(league_id: int, body: schemas.JoinLeagueIn, con: sqlite3.Connection = Depends(get_db)):
    league = get_league(con, league_id)
    if body.invite_code != league["invite_code"]:
        raise HTTPException(403, "invalid invite code")
    if league["status"] != "setup":
        raise HTTPException(409, f"league is {league['status']}; joins closed")
    owner = con.execute("INSERT INTO users (name) VALUES (?)", (body.owner_name,)).lastrowid
    # Joining auto-claims the team for its creator (P4-W18): the claim
    # code is returned in this response only, and gates the team's
    # mutations from now on.
    code = new_claim_code()
    try:
        cur = con.execute(
            "INSERT INTO teams (league_id, owner_id, name, faab_remaining, claim_code)"
            " VALUES (?, ?, ?, ?, ?)",
            (league_id, owner, body.team_name, FAAB_BUDGET, code),
        )
    except sqlite3.IntegrityError:
        raise HTTPException(409, f"team name '{body.team_name}' taken in this league")
    con.commit()
    team = get_team(con, cur.lastrowid)
    return schemas.TeamOut(
        id=team["id"], league_id=team["league_id"], name=team["name"],
        owner_name=team["owner_name"], faab_remaining=team["faab_remaining"],
        claimed=True, claim_code=code,
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
            claimed=bool(t["claim_code"]),
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


@router.get("/{league_id}/schedule-matrix",
            response_model=schemas.ScheduleMatrixOut)
def schedule_matrix(league_id: int, con: sqlite3.Connection = Depends(get_db)):
    """P5-W15: IPL team x fantasy week game-count matrix — the
    schedule-nudges table for every week at once, cell-for-cell the
    same values GET /schedule-nudges serves per week. A team with no
    row in a week where the fixture exists counts 0 (bye). Empty rows
    until the fixture imports."""
    league = get_league(con, league_id)  # 404 if missing
    from .. import schedule_games
    from ..constants import TOTAL_WEEKS
    per_team: dict[str, list[int]] = {}
    source = ""
    weeks_available: list[int] = []
    for wk in range(1, TOTAL_WEEKS + 1):
        data = schedule_games.fetch_week(con, league["season"], wk)
        weeks_available = data["weeks_available"]
        if data["source"]:
            source = data["source"]
        for g in data["games"]:
            row = per_team.setdefault(
                g["ipl_team_code"], [0] * TOTAL_WEEKS)
            row[wk - 1] = g["games"]
    rows = [
        schemas.ScheduleMatrixRowOut(
            ipl_team_code=code, games_by_week=games, total=sum(games))
        for code, games in sorted(per_team.items())
    ]
    return schemas.ScheduleMatrixOut(
        league_id=league_id, season=league["season"], source=source,
        weeks_available=weeks_available, rows=rows)


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


_RECAP_BASIS = (
    "Grades compare each team's drafted players against consensus "
    "pre-draft ranks (best rank any team gave the player). A player's "
    "value is (ranked pool size - rank + 1); a team's grade compares "
    "the value it drafted with the value its pick positions were "
    "'expected' to return. Deterministic: same draft + ranks -> "
    "same grades."
)


def _grade(ratio: float) -> str:
    if ratio >= 1.10:
        return "A"
    if ratio >= 1.03:
        return "B"
    if ratio >= 0.97:
        return "C"
    if ratio >= 0.90:
        return "D"
    return "F"


@router.get("/{league_id}/draft-recap", response_model=schemas.DraftRecapOut)
def get_draft_recap(league_id: int, con: sqlite3.Connection = Depends(get_db)):
    """P5-W4: post-draft recap + grades. Read-only and deterministic;
    computed from draft_picks + pre_draft_ranks only (no engine state).
    Until the draft completes, returns the draft's status with no
    teams — the UI shows the honest 'grades land when the draft
    completes' empty state."""
    get_league(con, league_id)  # 404 if missing
    d = services.get_league_draft(con, league_id)
    if d is None:
        return schemas.DraftRecapOut(
            league_id=league_id, status="no_draft", basis=_RECAP_BASIS)
    if d["status"] != "complete":
        return schemas.DraftRecapOut(
            league_id=league_id, status=d["status"], draft_id=d["id"],
            basis=_RECAP_BASIS)

    team_names = {
        r["id"]: r["name"]
        for r in con.execute(
            "SELECT id, name FROM teams WHERE league_id = ?", (league_id,))
    }
    consensus = {
        r["player_id"]: r["c_rank"]
        for r in con.execute(
            """SELECT r.player_id, MIN(r.rank) AS c_rank
               FROM pre_draft_ranks r JOIN teams t ON t.id = r.team_id
               WHERE t.league_id = ? GROUP BY r.player_id""", (league_id,))
    }
    pool = len(consensus)

    def value(rank: int) -> int:
        return pool - rank + 1

    picks = con.execute(
        """SELECT dp.pick_no, dp.team_id, dp.player_id, p.name AS player_name
           FROM draft_picks dp JOIN players p ON p.id = dp.player_id
           WHERE dp.draft_id = ? AND dp.player_id IS NOT NULL
           ORDER BY dp.pick_no""", (d["id"],)).fetchall()

    per_team: dict[int, dict] = {
        tid: {"projected": 0, "expected": 0, "made": 0, "unranked": 0,
              "steal": None, "reach": None}
        for tid in team_names
    }
    all_ranked: list[schemas.RecapPickOut] = []
    for r in picks:
        agg = per_team.setdefault(
            r["team_id"],
            {"projected": 0, "expected": 0, "made": 0, "unranked": 0,
             "steal": None, "reach": None})
        agg["made"] += 1
        agg["expected"] += max(value(r["pick_no"]), 1)
        rank = consensus.get(r["player_id"])
        if rank is None:
            agg["unranked"] += 1
            continue
        agg["projected"] += value(rank)
        entry = schemas.RecapPickOut(
            player_id=r["player_id"], player_name=r["player_name"],
            team_id=r["team_id"], team_name=team_names.get(r["team_id"], ""),
            pick_no=r["pick_no"], consensus_rank=rank,
            delta=r["pick_no"] - rank)
        all_ranked.append(entry)
        if entry.delta > 0 and (
                agg["steal"] is None or entry.delta > agg["steal"].delta):
            agg["steal"] = entry
        if entry.delta < 0 and (
                agg["reach"] is None or entry.delta < agg["reach"].delta):
            agg["reach"] = entry

    teams_out = []
    for tid, name in team_names.items():
        agg = per_team[tid]
        expected = agg["expected"] or 1
        ratio = round(agg["projected"] / expected, 3)
        teams_out.append(schemas.RecapTeamOut(
            team_id=tid, team_name=name, grade=_grade(ratio),
            projected_value=agg["projected"], expected_value=agg["expected"],
            value_ratio=ratio, picks_made=agg["made"],
            unranked_picks=agg["unranked"],
            biggest_steal=agg["steal"], biggest_reach=agg["reach"]))
    # Best draft first; team name breaks ties deterministically.
    teams_out.sort(key=lambda t: (-t.value_ratio, t.team_name))

    headline_steal = max(
        all_ranked, key=lambda e: (e.delta, -e.pick_no), default=None)
    if headline_steal is not None and headline_steal.delta <= 0:
        headline_steal = None
    best_pick = min(
        all_ranked, key=lambda e: (e.consensus_rank, e.pick_no), default=None)
    return schemas.DraftRecapOut(
        league_id=league_id, status="complete", draft_id=d["id"],
        teams=teams_out, headline_biggest_steal=headline_steal,
        headline_best_pick=best_pick, basis=_RECAP_BASIS)
