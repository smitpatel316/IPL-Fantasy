"""Leagues: create, read (+standings), join, list teams."""

import json
import secrets
import sqlite3
import string

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from .. import schemas, services
from ..constants import FAAB_BUDGET, TOTAL_WEEKS
from ..database import get_db
from . import (
    availability_from_status,
    avg_points_map,
    get_league,
    get_team,
    new_claim_code,
    row_dict,
)

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


def _team_record(con: sqlite3.Connection, league_id: int,
                team_id: int) -> tuple[int, int, int, float]:
    """P5-W45: (wins, losses, ties, points_for) for one team from finalized
    matchups — the same query get_league_detail uses for the standings."""
    w = con.execute(
        """SELECT
             SUM(CASE WHEN (team_a_id = ? AND score_a > score_b) OR (team_b_id = ? AND score_b > score_a) THEN 1 ELSE 0 END),
             SUM(CASE WHEN (team_a_id = ? AND score_a < score_b) OR (team_b_id = ? AND score_b < score_a) THEN 1 ELSE 0 END),
             SUM(CASE WHEN status = 'final' AND score_a = score_b AND (team_a_id = ? OR team_b_id = ?) THEN 1 ELSE 0 END),
             SUM(CASE WHEN team_a_id = ? THEN score_a WHEN team_b_id = ? THEN score_b ELSE 0 END)
           FROM matchups WHERE league_id = ? AND status = 'final'""",
        (team_id, team_id, team_id, team_id, team_id, team_id, team_id, team_id, league_id),
    ).fetchone()
    return (w[0] or 0, w[1] or 0, w[2] or 0, w[3] or 0.0)


@router.get("/my-leagues", response_model=list[schemas.MyLeagueTeamOut])
def my_leagues(team_ids: str = Query("",
              description="comma-separated team ids this browser holds claim codes for (P4-W18)"),
              con: sqlite3.Connection = Depends(get_db)):
    """P5-W45: for each team id this browser has claimed, the league it
    lives in (name, season, status) plus the team's W-L record from
    finalized matchups. Read-only; claim codes are never projected.
    Placed before /{league_id} so the literal path wins."""
    ids: list[int] = []
    for raw in team_ids.split(","):
        raw = raw.strip()
        if not raw:
            continue
        if not raw.isdigit():
            raise HTTPException(422, f"bad team id '{raw}'")
        if int(raw) not in ids:
            ids.append(int(raw))
    if not ids:
        raise HTTPException(422, "supply at least one team id (team_ids)")
    if len(ids) > 100:
        raise HTTPException(422, "too many team ids (max 100)")
    out = []
    for tid in ids:
        try:
            team = get_team(con, tid)  # unknown teams are skipped below
        except HTTPException:
            continue
        league = get_league(con, team["league_id"])
        wins, losses, ties, pf = _team_record(con, team["league_id"], tid)
        out.append(schemas.MyLeagueTeamOut(
            team_id=tid, team_name=team["name"],
            league_id=league["id"], league_name=league["name"],
            season=league["season"], league_status=league["status"],
            wins=wins, losses=losses, ties=ties, points_for=pf))
    return out


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
        wins, losses, ties, pf = _team_record(con, league_id, t["id"])
        standings.append(
            schemas.TeamStandingOut(
                team_id=t["id"], team_name=t["name"], owner_name=t["owner_name"],
                wins=wins, losses=losses, ties=ties,
                points_for=pf, faab_remaining=t["faab_remaining"],
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


_RECORD_LABELS = {
    "highest_weekly_score": "Highest weekly score",
    "largest_margin": "Largest margin of victory",
    "longest_win_streak": "Longest win streak",
    "narrowest_win": "Narrowest win",
    "most_points_in_loss": "Most points in a loss",
}


def _fmt_score(v: float) -> str:
    return ("%g" % v)


@router.get("/{league_id}/records", response_model=schemas.LeagueRecordsOut)
def league_records(league_id: int, con: sqlite3.Connection = Depends(get_db)):
    """P5-W46: the league records book. Every record derives from
    persisted FINAL matchups (read-only); ties resolve deterministically
    to the earliest week, then the alphabetically-first team name. An
    unscored league returns scored=0 and no records — the UI renders
    the honest pre-season empty state."""
    league = get_league(con, league_id)  # 404 if missing
    names = {
        r["id"]: r["name"] for r in con.execute(
            "SELECT id, name FROM teams WHERE league_id = ?", (league_id,))
    }
    finals = con.execute(
        """SELECT week_no, team_a_id, team_b_id, score_a, score_b
           FROM matchups WHERE league_id = ? AND status = 'final'
           ORDER BY week_no""",
        (league_id,)).fetchall()
    records: list[schemas.LeagueRecordOut] = []
    if finals:
        def name(tid: int) -> str:
            return names.get(tid, f"team {tid}")

        def winner_loser(m):
            if m["score_a"] > m["score_b"]:
                return (m["team_a_id"], m["team_b_id"])
            if m["score_b"] > m["score_a"]:
                return (m["team_b_id"], m["team_a_id"])
            return None

        # Highest weekly score.
        hs, hs_tid, hs_wk = max(
            ((max(m["score_a"], m["score_b"]),
              m["team_a_id"] if m["score_a"] >= m["score_b"] else m["team_b_id"],
              m["week_no"]) for m in finals),
            key=lambda e: (e[0], -e[2], name(e[1])))
        records.append(schemas.LeagueRecordOut(
            key="highest_weekly_score",
            label=_RECORD_LABELS["highest_weekly_score"],
            value=_fmt_score(hs),
            detail=f"{name(hs_tid)} · week {hs_wk}"))

        # Largest margin and narrowest win (ties excluded from both).
        decided = [(m, winner_loser(m)) for m in finals]
        decided = [(m, wl) for m, wl in decided if wl is not None]
        if decided:
            def margin(m):
                return abs(m["score_a"] - m["score_b"])

            lm, lm_wl = max(decided,
                            key=lambda e: (margin(e[0]), -e[0]["week_no"],
                                           name(e[1][0])))
            w_id, l_id = lm_wl
            w_sc = lm["score_a"] if w_id == lm["team_a_id"] else lm["score_b"]
            l_sc = lm["score_b"] if w_id == lm["team_a_id"] else lm["score_a"]
            records.append(schemas.LeagueRecordOut(
                key="largest_margin",
                label=_RECORD_LABELS["largest_margin"],
                value=_fmt_score(margin(lm)),
                detail=(f"{name(w_id)} {_fmt_score(w_sc)} – "
                        f"{_fmt_score(l_sc)} {name(l_id)} · week {lm['week_no']}")))

            nw, nw_wl = min(decided,
                            key=lambda e: (margin(e[0]), e[0]["week_no"],
                                           name(e[1][0])))
            w_id, l_id = nw_wl
            w_sc = nw["score_a"] if w_id == nw["team_a_id"] else nw["score_b"]
            l_sc = nw["score_b"] if w_id == nw["team_a_id"] else nw["score_a"]
            records.append(schemas.LeagueRecordOut(
                key="narrowest_win",
                label=_RECORD_LABELS["narrowest_win"],
                value=_fmt_score(margin(nw)),
                detail=(f"{name(w_id)} {_fmt_score(w_sc)} – "
                        f"{_fmt_score(l_sc)} {name(l_id)} · week {nw['week_no']}")))

            # Most points scored in a loss.
            mpl_m, mpl_lid, mpl_lsc = max(
                ((m, wl[1], (m["score_a"] if wl[1] == m["team_a_id"]
                             else m["score_b"])) for m, wl in decided),
                key=lambda e: (e[2], -e[0]["week_no"], name(e[1])))
            records.append(schemas.LeagueRecordOut(
                key="most_points_in_loss",
                label=_RECORD_LABELS["most_points_in_loss"],
                value=_fmt_score(mpl_lsc),
                detail=(f"{name(mpl_lid)} · week {mpl_m['week_no']}")))

        # Longest win streak (a tie or loss resets the run).
        per_team: dict[int, list[tuple[int, str]]] = {}
        for m in finals:
            wl = winner_loser(m)
            for tid in (m["team_a_id"], m["team_b_id"]):
                oc = "w" if wl and wl[0] == tid else ("t" if wl is None else "l")
                per_team.setdefault(tid, []).append((m["week_no"], oc))
        best = (0, "", 0, 0)  # (length, team_name, from_week, to_week)
        for tid in sorted(per_team, key=name):
            run, start = 0, 0
            for wk, oc in per_team[tid]:
                if oc == "w":
                    if run == 0:
                        start = wk
                    run += 1
                    if run > best[0]:
                        best = (run, name(tid), start, wk)
                else:
                    run = 0
        if best[0] > 0:
            records.append(schemas.LeagueRecordOut(
                key="longest_win_streak",
                label=_RECORD_LABELS["longest_win_streak"],
                value=f"{best[0]} week{'s' if best[0] != 1 else ''}",
                detail=(f"{best[1]} · week {best[2]}"
                        if best[2] == best[3]
                        else f"{best[1]} · weeks {best[2]}–{best[3]}")))
    return schemas.LeagueRecordsOut(
        league_id=league_id, scored=len(finals), records=records)


@router.get("/{league_id}/waivers/order", response_model=schemas.WaiverOrderOut)
def waiver_order(league_id: int, con: sqlite3.Connection = Depends(get_db)):
    """P5-W47: the current waiver-wire tiebreak order — the engine's
    reverse-standings order (services.standings_best_first, reversed:
    the worst team wins tied bids), with each team's W-L. Read
    projection only; no engine changes."""
    get_league(con, league_id)  # 404 if missing
    names = {
        r["id"]: r["name"] for r in con.execute(
            "SELECT id, name FROM teams WHERE league_id = ?", (league_id,))
    }
    order = []
    for pos, tid in enumerate(
            reversed(services.standings_best_first(con, league_id)), start=1):
        w = con.execute(
            """SELECT
                 SUM(CASE WHEN (team_a_id = ? AND score_a > score_b) OR (team_b_id = ? AND score_b > score_a) THEN 1 ELSE 0 END),
                 SUM(CASE WHEN (team_a_id = ? AND score_a < score_b) OR (team_b_id = ? AND score_b < score_a) THEN 1 ELSE 0 END)
               FROM matchups WHERE league_id = ? AND status = 'final'""",
            (tid, tid, tid, tid, league_id)).fetchone()
        order.append(schemas.WaiverOrderTeamOut(
            position=pos, team_id=tid,
            team_name=names.get(tid, f"team {tid}"),
            wins=w[0] or 0, losses=w[1] or 0))
    return schemas.WaiverOrderOut(
        league_id=league_id, order=order,
        basis=("Reverse standings — the team with the worst record "
               "wins tied bids."))
@router.patch("/{league_id}/settings", response_model=schemas.LeagueOut)
def patch_league_settings(league_id: int, body: schemas.LeagueSettingsPatch,
                          con: sqlite3.Connection = Depends(get_db)):
    """Commissioner settings edit (P4-W15). Ungated until team identity
    lands (P4-W18); only the patchable keys are applied."""
    league = get_league(con, league_id)
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(422, "no settings supplied")
    if "draft_order" in updates:
        # P5-W30: the order locks once the draft starts, and a set order
        # must be an exact permutation of the joined team ids.
        if league["status"] != "setup":
            raise HTTPException(
                422, "draft order locks once the draft starts")
        order = updates["draft_order"]
        if order:
            team_ids = [r["id"] for r in con.execute(
                "SELECT id FROM teams WHERE league_id = ?", (league_id,))]
            if sorted(order) != sorted(team_ids):
                raise HTTPException(
                    422, "draft_order must be an exact permutation of the"
                         " league's team ids (no duplicates, none missing,"
                         " none unknown)")
        else:
            updates.pop("draft_order")  # [] clears back to the shuffle
    settings = dict(league["settings"] or {})
    settings.update(updates)
    if "draft_order" in body.model_dump() and body.draft_order == []:
        settings.pop("draft_order", None)
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
                       request: Request,
                       con: sqlite3.Connection = Depends(get_db)):
    """Commissioner add/drop by fiat with a mandatory audit note (P4-W25).
    Gated on the commissioner's team (P5-W54): body.commissioner_team_id
    must name the league's commissioner team, and a claimed
    commissioner's team must present its X-Team-Claim code (the P4-W18
    claim gate). The identity field is not persisted — only the fiat
    move lands in the audit log."""
    from .message_board import _require_commissioner_actor
    league = get_league(con, league_id)
    _require_commissioner_actor(con, league, body.commissioner_team_id,
                                request, "record commissioner roster moves")
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


TIER_GAP = 5  # P5-W25 pinned tier-break threshold (consensus-rank gap)


def _cheat_sheet(con, league) -> schemas.CheatSheetOut:
    """P5-W25 draft cheat sheet: every player with a D7 role for the
    league's season, grouped by role and ordered by consensus
    pre_draft_ranks (MIN rank across the league's teams — the exact
    players-list projection), tiered by rank gaps. total_games sums the
    schedule-nudges table over all weeks for the player's IPL team
    (null until a fixture imports). Read-only."""
    from .. import schedule_games
    from ..constants import TOTAL_WEEKS
    league_id = league["id"]
    totals: dict[str, int] = {}
    source = ""
    fixture_seen = False
    for wk in range(1, TOTAL_WEEKS + 1):
        data = schedule_games.fetch_week(con, league["season"], wk)
        if data["source"]:
            source = data["source"]
        for g in data["games"]:
            fixture_seen = True
            totals[g["ipl_team_code"]] = (
                totals.get(g["ipl_team_code"], 0) + g["games"])
    avgs = avg_points_map(con)
    rows = con.execute(
        """SELECT p.id, p.name, pr.role, pr.is_overseas, pr.ipl_team_code,
                  pr.status,
                  (SELECT MIN(rank) FROM pre_draft_ranks r
                   JOIN teams t ON t.id = r.team_id
                   WHERE r.player_id = p.id AND t.league_id = ?) AS rk
           FROM players p JOIN player_roles pr
             ON pr.player_id = p.id AND pr.season = p.season
           WHERE p.season = ?
           ORDER BY pr.role, rk NULLS LAST, p.name""",
        (league_id, league["season"])).fetchall()
    groups: dict[str, list[schemas.CheatSheetPlayerOut]] = {
        role: [] for role in ("WK", "BAT", "AR", "BOWL")}
    tiers: dict[str, int] = {}
    prev_rank: dict[str, int | None] = {}
    for r in rows:
        role = r["role"]
        tier = tiers.get(role, 1)
        rk = r["rk"]
        if rk is not None and prev_rank.get(role) is not None \
                and rk - prev_rank[role] > TIER_GAP:
            tier += 1
        tiers[role] = tier
        if rk is not None:
            prev_rank[role] = rk
        code = r["ipl_team_code"]
        groups[role].append(schemas.CheatSheetPlayerOut(
            id=r["id"], name=r["name"], role=role, ipl_team_code=code,
            is_overseas=bool(r["is_overseas"] or 0), preseason_rank=rk,
            tier=tier, avg_points=avgs.get(r["id"]),
            availability=availability_from_status(r["status"]),
            total_games=(totals.get(code, 0)
                         if fixture_seen and code else None)))
    return schemas.CheatSheetOut(
        league_id=league_id, season=league["season"], source=source,
        tier_gap_threshold=TIER_GAP,
        groups=[schemas.CheatSheetGroupOut(role=role, players=groups[role])
                for role in ("WK", "BAT", "AR", "BOWL")])


@router.get("/{league_id}/cheat-sheet",
            response_model=schemas.CheatSheetOut)
def cheat_sheet(league_id: int, con: sqlite3.Connection = Depends(get_db)):
    league = get_league(con, league_id)  # 404 if missing
    return _cheat_sheet(con, league)


@router.get("/{league_id}/cheat-sheet.csv")
def cheat_sheet_csv(league_id: int,
                    con: sqlite3.Connection = Depends(get_db)):
    """P5-W25: the cheat-sheet payload as CSV — same rows, same order,
    for offline/print use on draft day."""
    import csv
    import io

    from fastapi.responses import PlainTextResponse
    league = get_league(con, league_id)  # 404 if missing
    sheet = _cheat_sheet(con, league)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["role", "tier", "player", "ipl_team", "overseas",
                "preseason_rank", "avg_points", "availability",
                "total_games"])
    for g in sheet.groups:
        for pl in g.players:
            w.writerow([g.role, pl.tier, pl.name, pl.ipl_team_code or "",
                        "yes" if pl.is_overseas else "no",
                        pl.preseason_rank if pl.preseason_rank is not None
                        else "",
                        pl.avg_points if pl.avg_points is not None else "",
                        pl.availability,
                        pl.total_games if pl.total_games is not None
                        else ""])
    return PlainTextResponse(
        buf.getvalue(), media_type="text/csv",
        headers={"Content-Disposition":
                 f'attachment; filename="cheat-sheet-league-{league_id}.csv"'})


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


_RECAP_LABELS = {
    "biggest_upset": "Biggest upset",
    "highest_scorer": "Highest scorer",
    "closest_matchup": "Closest matchup",
    "biggest_blowout": "Biggest blowout",
}


def _fmt_score(v: float) -> str:
    return ("%g" % v)


@router.get("/{league_id}/recap/{week_no}",
            response_model=schemas.WeeklyRecapOut)
def weekly_recap(league_id: int, week_no: int,
                 con: sqlite3.Connection = Depends(get_db)):
    """P5-W48: the 'week in review' for one scored week. Biggest upset
    (the winner's pre-week average points-for vs the loser's — a winner
    who was outscored on average before this week), highest scorer,
    closest matchup, and biggest blowout. Computed from persisted
    matchup scores only; a week with no final matchups returns
    scored=false and no facts (the UI shows the honest 'week not scored
    yet' state). Read-only."""
    if not 1 <= week_no <= TOTAL_WEEKS:
        raise HTTPException(422, f"week_no must be 1..{TOTAL_WEEKS}")
    get_league(con, league_id)  # 404 if missing
    names = {
        r["id"]: r["name"] for r in con.execute(
            "SELECT id, name FROM teams WHERE league_id = ?", (league_id,))
    }
    games = con.execute(
        """SELECT team_a_id, team_b_id, score_a, score_b FROM matchups
           WHERE league_id = ? AND week_no = ? AND status = 'final'""",
        (league_id, week_no)).fetchall()

    def name(tid: int) -> str:
        return names.get(tid, f"team {tid}")

    def side(m, tid: int) -> float:
        return m["score_a"] if tid == m["team_a_id"] else m["score_b"]

    def winner_loser(m):
        if m["score_a"] > m["score_b"]:
            return (m["team_a_id"], m["team_b_id"])
        if m["score_b"] > m["score_a"]:
            return (m["team_b_id"], m["team_a_id"])
        return None

    facts: list[schemas.RecapFactOut] = []
    if games:
        decided = [(m, w, l) for m in games
                   for wl in [winner_loser(m)] if wl for (w, l) in [wl]]

        # Biggest upset: winner entered the week with a lower average
        # points-for than the loser (computed from prior final weeks).
        if week_no > 1:
            prior: dict[int, list[float]] = {}
            for m in con.execute(
                    """SELECT team_a_id, team_b_id, score_a, score_b
                       FROM matchups WHERE league_id = ? AND week_no < ?
                       AND status = 'final'""",
                    (league_id, week_no)):
                prior.setdefault(m["team_a_id"], []).append(m["score_a"])
                prior.setdefault(m["team_b_id"], []).append(m["score_b"])
            avg = {tid: sum(v) / len(v) for tid, v in prior.items()}
            upsets = [(avg[l] - avg[w], w, l) for _, w, l in decided
                      if w in avg and l in avg and avg[w] < avg[l]]
            if upsets:
                delta, w, l = max(upsets, key=lambda e: (e[0], name(e[1])))
                facts.append(schemas.RecapFactOut(
                    key="biggest_upset",
                    label=_RECAP_LABELS["biggest_upset"],
                    value=f"+{_fmt_score(delta)} underdog",
                    detail=(f"{name(w)} beat {name(l)} (pre-week avg "
                            f"{_fmt_score(avg[w])} vs {_fmt_score(avg[l])})")))

        # Highest scorer.
        hs_tid, hs_m, hs_sc = max(
            ((tid, m, side(m, tid)) for m in games
             for tid in (m["team_a_id"], m["team_b_id"])),
            key=lambda e: (e[2], name(e[0])))
        hs_opp = (hs_m["team_b_id"] if hs_tid == hs_m["team_a_id"]
                  else hs_m["team_a_id"])
        facts.append(schemas.RecapFactOut(
            key="highest_scorer", label=_RECAP_LABELS["highest_scorer"],
            value=_fmt_score(hs_sc),
            detail=f"{name(hs_tid)} vs {name(hs_opp)}"))

        if decided:
            def margin(m) -> float:
                return abs(m["score_a"] - m["score_b"])

            # Closest matchup.
            nm, nw, nl = min(decided,
                             key=lambda e: (margin(e[0]), name(e[1])))
            nw_sc, nl_sc = side(nm, nw), side(nm, nl)
            facts.append(schemas.RecapFactOut(
                key="closest_matchup", label=_RECAP_LABELS["closest_matchup"],
                value=_fmt_score(margin(nm)),
                detail=(f"{name(nw)} {_fmt_score(nw_sc)} – "
                        f"{_fmt_score(nl_sc)} {name(nl)}")))

            # Biggest blowout (a shutout gets the callout).
            bm, bw, bl = max(decided,
                             key=lambda e: (margin(e[0]), name(e[1])))
            bw_sc, bl_sc = side(bm, bw), side(bm, bl)
            detail = (f"{name(bw)} {_fmt_score(bw_sc)} – "
                      f"{_fmt_score(bl_sc)} {name(bl)}")
            if bl_sc == 0:
                detail += " — shutout"
            facts.append(schemas.RecapFactOut(
                key="biggest_blowout", label=_RECAP_LABELS["biggest_blowout"],
                value=_fmt_score(margin(bm)), detail=detail))
    return schemas.WeeklyRecapOut(
        league_id=league_id, week_no=week_no,
        scored=bool(games), matchup_count=len(games), facts=facts)
