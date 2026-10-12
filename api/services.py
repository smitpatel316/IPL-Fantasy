"""Engine glue: api.engine state machines behind the HTTP routers.

The league-core engines (draft / waiver / trade) are pure in-memory state
machines. This module owns:
  - building an engine from the sqlite rows (teams, rosters, ranks, roles),
  - persisting engine snapshots as JSON in the `engine_state` table
    (in-memory registry per process + DB persistence across restarts),
  - translating engine results back into DB projections (draft_picks,
    roster_slots, waiver_claims, trades rows) and raising the engine's
    domain errors as HTTP-friendly exceptions.

NOTE: the engine to_dict/from_dict contracts serialize dict int-keys as
JSON strings; `_revive_*` normalizes keys back to ints after a DB load
(the engines themselves are league-core's territory — do not patch them
here for persistence quirks).
"""

import json
import logging
import sqlite3
import threading
import time

from fastapi import HTTPException

from api.engine.draft_engine import (
    ClockNotExpired,
    DoNotDraft,
    Draft,
    DraftConfig,
    DraftError,
    DraftNotLive,
    NotYourTurn,
    PlayerUnavailable,
    PoolExhausted,
    RosterFull,
    UnfieldableRoster,
    d8_reachable,
)
# P2-L7 exact best-ADP D8-legal-11 solver (lives in sandbox_season; pure function).
from api.engine.sandbox_season import solve_best_d8_lineup
from api.engine.matchup_scheduler import (
    ScheduleConfig, ScheduleError, generate_schedule,
)
from api.engine.trade_engine import ACTIVE_ROSTER_SIZE, TradeEngine, TradeError
from api.engine.waiver_engine import WaiverEngine, WaiverError

from . import constants
from .routers import get_league, get_team, owned_map, player_roles_map

log = logging.getLogger("api.services")

# ---------------------------------------------------------------------------
# persistence: engine_state table (+ trades.engine_id column)
# ---------------------------------------------------------------------------

_SCHEMA_PATCH = """
CREATE TABLE IF NOT EXISTS engine_state (
    scope      TEXT NOT NULL,   -- 'draft' | 'waiver' | 'trade'
    scope_id   INTEGER NOT NULL,
    state      TEXT NOT NULL,   -- engine to_dict() JSON
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (scope, scope_id)
);
"""


def ensure_engine_tables(con: sqlite3.Connection) -> None:
    con.executescript(_SCHEMA_PATCH)
    cols = {r["name"] for r in con.execute("PRAGMA table_info(trades)")}
    if "engine_id" not in cols:
        con.execute("ALTER TABLE trades ADD COLUMN engine_id INTEGER")
    # P4-W1 history detail: veto count + lifecycle timestamps on the
    # trades read projection (backfilled from engine state on next sync).
    for col, ddl in (
        ("veto_count", "INTEGER NOT NULL DEFAULT 0"),
        ("proposed_at", "TEXT"),
        ("accepted_at", "TEXT"),
        ("vetoed_at", "TEXT"),
        ("executed_at", "TEXT"),
    ):
        if col not in cols:
            con.execute(f"ALTER TABLE trades ADD COLUMN {col} {ddl}")
    con.commit()


_registry: dict[tuple[str, int], object] = {}

# Per-draft mutexes: the draft-room WebSocket clock sweeper and the HTTP pick
# endpoints share the engine cache across threads; pick recording (clock
# expiry + manual picks) must be serialized per draft.
_draft_locks: dict[int, threading.Lock] = {}
_draft_locks_guard = threading.Lock()


def _draft_lock(draft_id: int) -> threading.Lock:
    with _draft_locks_guard:
        return _draft_locks.setdefault(draft_id, threading.Lock())


def _save(con: sqlite3.Connection, scope: str, scope_id: int, state: dict) -> None:
    ensure_engine_tables(con)
    con.execute(
        "INSERT INTO engine_state (scope, scope_id, state, updated_at)"
        " VALUES (?, ?, ?, datetime('now'))"
        " ON CONFLICT (scope, scope_id) DO UPDATE SET state = excluded.state,"
        " updated_at = datetime('now')",
        (scope, scope_id, json.dumps(state)),
    )
    con.commit()


def _load_state(con: sqlite3.Connection, scope: str, scope_id: int) -> dict | None:
    ensure_engine_tables(con)
    row = con.execute(
        "SELECT state FROM engine_state WHERE scope = ? AND scope_id = ?",
        (scope, scope_id),
    ).fetchone()
    return json.loads(row["state"]) if row else None


def _get_cached(scope: str, scope_id: int):
    return _registry.get((scope, scope_id))


def _put_cached(scope: str, scope_id: int, engine, con) -> None:
    _registry[(scope, scope_id)] = engine
    _save(con, scope, scope_id, engine.to_dict())


# ---------------------------------------------------------------------------
# shared helpers
# ---------------------------------------------------------------------------

def _teams(con: sqlite3.Connection, league_id: int) -> list[dict]:
    return [
        dict(r)
        for r in con.execute(
            "SELECT id, name, faab_remaining FROM teams WHERE league_id = ? ORDER BY id",
            (league_id,),
        )
    ]


def _roster_pids(con: sqlite3.Connection, team_id: int) -> list[int]:
    return [
        r["player_id"]
        for r in con.execute(
            "SELECT player_id FROM roster_slots WHERE team_id = ? AND week_no IS NULL"
            " ORDER BY id",
            (team_id,),
        )
    ]


def _pool_ranked(con: sqlite3.Connection, league_id: int, season: str) -> list[int]:
    """Free-agent player ids ordered by league preseason rank (ADP proxy)."""
    owned = set(owned_map(con, league_id))
    rows = con.execute(
        """SELECT p.id, COALESCE(MIN(r.rank), 1e9) AS r
           FROM players p
           LEFT JOIN pre_draft_ranks r ON r.player_id = p.id
           WHERE p.season = ?
           GROUP BY p.id ORDER BY r, p.id""",
        (season,),
    ).fetchall()
    return [r["id"] for r in rows if r["id"] not in owned]


def _team_ranks(con: sqlite3.Connection, team_id: int) -> list[int]:
    return [
        r["player_id"]
        for r in con.execute(
            "SELECT player_id FROM pre_draft_ranks WHERE team_id = ? ORDER BY rank",
            (team_id,),
        )
    ]


def current_week(con: sqlite3.Connection, league_id: int) -> int:
    row = con.execute(
        "SELECT MAX(week_no) FROM matchups WHERE league_id = ? AND status = 'final'",
        (league_id,),
    ).fetchone()
    # P4-W28: cap at TOTAL_WEEKS — after the week-8 final there is no
    # week 9. Without the cap, current_week returned 9 and waiver
    # claims were filed into an invisible week (reads bound week_no
    # <= TOTAL_WEEKS) that the unbounded run endpoint could execute.
    return min((row[0] or 0) + 1, constants.TOTAL_WEEKS)


def standings_best_first(con: sqlite3.Connection, league_id: int) -> list[int]:
    """Team ids best -> worst (wins, then points-for, then id desc as the
    deterministic stand-in for reverse-standings order on ties)."""
    rows = con.execute(
        """SELECT t.id,
             SUM(CASE WHEN (team_a_id = t.id AND score_a > score_b)
                       OR (team_b_id = t.id AND score_b > score_a) THEN 1 ELSE 0 END) AS w,
             SUM(CASE WHEN team_a_id = t.id THEN score_a
                      WHEN team_b_id = t.id THEN score_b ELSE 0 END) AS pf
           FROM teams t LEFT JOIN matchups m
             ON m.league_id = t.league_id AND m.status = 'final'
                AND (m.team_a_id = t.id OR m.team_b_id = t.id)
           WHERE t.league_id = ?
           GROUP BY t.id ORDER BY w DESC, pf DESC, t.id DESC""",
        (league_id,),
    ).fetchall()
    return [r["id"] for r in rows]


# ---------------------------------------------------------------------------
# draft
# ---------------------------------------------------------------------------

def _build_draft(con: sqlite3.Connection, league_id: int) -> Draft:
    league = get_league(con, league_id)
    season = league["season"]
    teams = _teams(con, league_id)
    if len(teams) < 2:
        raise HTTPException(409, "need at least 2 teams to start a draft")
    roles = {
        pid: {"role": meta["role"], "is_overseas": meta["is_overseas"]}
        for pid, meta in player_roles_map(con, season).items()
    }
    pool = _pool_ranked(con, league_id, season)
    picks_needed = len(teams) * constants.DRAFT_ROUNDS
    if len(pool) < picks_needed:
        raise HTTPException(
            409,
            f"player pool too small to complete the draft: {len(pool)} "
            f"players available, {picks_needed} picks required "
            f"({len(teams)} teams x {constants.DRAFT_ROUNDS} rounds)")
    ranks = {t["id"]: _team_ranks(con, t["id"]) for t in teams}
    settings = league.get("settings") or {}
    cfg = DraftConfig(
        teams=tuple((t["id"], t["name"]) for t in teams),
        rounds=constants.DRAFT_ROUNDS,
        pick_clock_secs=int(settings.get("pick_clock_secs", 90)),
        seed=42,
    )
    draft = Draft(cfg, pool, roles=roles, ranks=ranks)
    draft.start()
    return draft


def _revive_draft(con: sqlite3.Connection, draft_id: int) -> Draft:
    cached = _get_cached("draft", draft_id)
    if cached is not None:
        return cached
    league_id = con.execute(
        "SELECT league_id FROM drafts WHERE id = ?", (draft_id,)
    ).fetchone()
    if not league_id:
        raise HTTPException(404, f"draft {draft_id} not found")
    state = _load_state(con, "draft", draft_id)
    if state is None:
        raise HTTPException(404, f"draft {draft_id} has no engine state")
    league = get_league(con, league_id["league_id"])
    season = league["season"]
    roles = {
        pid: {"role": meta["role"], "is_overseas": meta["is_overseas"]}
        for pid, meta in player_roles_map(con, season).items()
    }
    pool = _pool_ranked(con, league_id["league_id"], season)
    # Re-add already-drafted players to the pool so from_dict's invariants
    # hold; drafted set is authoritative from state.picks.
    drafted = {p["player_id"] for p in state.get("picks", []) if p.get("player_id")}
    for pid in drafted:
        if pid not in pool:
            pool.append(pid)
    draft = Draft.from_dict(state, pool, roles=roles)
    draft.rosters = {int(k): v for k, v in draft.rosters.items()}
    draft.dnd = {int(k): set(v) for k, v in draft.dnd.items()}
    # from_dict() drops custom ranks (advisory only per its contract); re-supply
    # them so clock-expiry auto-picks respect each team's pre-draft board.
    league_id_int = league_id["league_id"]
    teams = _teams(con, league_id_int)
    draft.ranks = {t["id"]: _team_ranks(con, t["id"]) for t in teams}
    _registry[("draft", draft_id)] = draft
    return draft


def _draft_error_to_http(e: DraftError) -> HTTPException:
    if isinstance(e, NotYourTurn):
        return HTTPException(409, str(e))
    if isinstance(e, (DraftNotLive, ClockNotExpired)):
        return HTTPException(409, str(e))
    return HTTPException(422, str(e))


def _persist_pick(con: sqlite3.Connection, draft_id: int, pick: dict) -> None:
    con.execute(
        "INSERT INTO draft_picks (draft_id, pick_no, round_no, team_id, player_id, is_auto)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (draft_id, pick["pick_no"], pick["round_no"], pick["team_id"],
         pick["player_id"], 1 if pick["is_auto"] else 0),
    )
    # week_no NULL = draft/construction state (see schema.sql).
    con.execute(
        "INSERT INTO roster_slots (team_id, player_id, slot, week_no)"
        " VALUES (?, ?, ?, NULL)",
        (pick["team_id"], pick["player_id"], pick["slot"]),
    )


def start_draft(con: sqlite3.Connection, league_id: int) -> dict:
    league = get_league(con, league_id)
    if league["status"] not in ("setup",):
        raise HTTPException(409, f"league is {league['status']}; draft already started")
    draft = _build_draft(con, league_id)
    cur = con.execute(
        "INSERT INTO drafts (league_id, draft_order, rounds, status, current_pick_no, pick_deadline)"
        " VALUES (?, ?, ?, ?, ?, datetime(?, 'unixepoch'))",
        (league_id, json.dumps(list(draft.draft_order)), constants.DRAFT_ROUNDS,
         draft.status, draft.current_pick_no, draft.pick_deadline),
    )
    draft_id = cur.lastrowid
    _put_cached("draft", draft_id, draft, con)
    con.execute("UPDATE leagues SET status = 'drafting' WHERE id = ?", (league_id,))
    con.commit()
    return _draft_row(con, draft_id)


def _draft_row(con: sqlite3.Connection, draft_id: int) -> dict:
    row = con.execute("SELECT * FROM drafts WHERE id = ?", (draft_id,)).fetchone()
    if not row:
        raise HTTPException(404, f"draft {draft_id} not found")
    d = dict(row)
    order = json.loads(d["draft_order"] or "[]")
    # On-clock team comes from the live engine (snake math lives there);
    # never derive it from the round-1 order with index arithmetic.
    try:
        eng = _revive_draft(con, draft_id)
        on_clock = eng.on_clock_team_id if (
            eng.status == Draft.STATUS_LIVE and d["status"] == "live") else None
    except HTTPException:
        on_clock = None
    return {
        "id": d["id"], "league_id": d["league_id"], "rounds": d["rounds"],
        "status": d["status"], "current_pick_no": d["current_pick_no"],
        "draft_order": order,
        "on_clock_team_id": on_clock,
    }


def _pick_out(pick: dict) -> dict:
    return {
        "pick_no": pick["pick_no"], "round_no": pick["round_no"],
        "team_id": pick["team_id"], "player_id": pick["player_id"],
        "is_auto": pick["is_auto"],
    }


def _commit_pick(con: sqlite3.Connection, draft_id: int, draft: Draft,
                 pick: dict, fired: dict | None = None) -> None:
    """Persist one recorded pick (plus an optional clock-fired auto-pick that
    preceded it) and run draft-completion side effects. Shared by make_pick
    (HTTP/WS manual picks) and expire_pick (clock sweeper)."""
    with con:
        if fired:
            _persist_pick(con, draft_id, fired)
        _persist_pick(con, draft_id, pick)
        if draft.status == Draft.STATUS_COMPLETE:
            con.execute(
                "UPDATE drafts SET status = 'complete', current_pick_no = ?,"
                " pick_deadline = NULL WHERE id = ?",
                (draft.current_pick_no, draft_id),
            )
            league_id = con.execute(
                "SELECT league_id FROM drafts WHERE id = ?", (draft_id,)
            ).fetchone()["league_id"]
            con.execute(
                "UPDATE leagues SET status = 'in_season' WHERE id = ?", (league_id,)
            )
            # Yahoo-style default: every team opens week 1 with its best-ADP
            # D8-legal 11 (BNx3, IL empty); managers adjust before the D5 lock.
            _auto_set_week1_lineups(
                con, league_id, get_league(con, league_id)["season"])
            # Weeks 1-6 H2H schedule (D4); byes for odd team counts.
            _generate_schedule(con, league_id)
        else:
            con.execute(
                "UPDATE drafts SET current_pick_no = ?, status = ?,"
                " pick_deadline = datetime(?, 'unixepoch') WHERE id = ?",
                (draft.current_pick_no, draft.status, draft.pick_deadline, draft_id),
            )
    _put_cached("draft", draft_id, draft, con)


def make_pick(con: sqlite3.Connection, draft_id: int, team_id: int,
              player_id: int) -> dict:
    with _draft_lock(draft_id):
        draft = _revive_draft(con, draft_id)
        fired: dict | None = None
        try:
            # Auto-fire the clock before validating the manual pick.
            if draft.status == Draft.STATUS_LIVE and draft.pick_deadline is not None \
                    and time.time() >= draft.pick_deadline:
                fired = draft.expire_pick()
            pick = draft.manual_pick(team_id, player_id)
        except DraftError as e:
            raise _draft_error_to_http(e)
        _commit_pick(con, draft_id, draft, pick, fired)
        return _pick_out(pick)


def expire_pick(con: sqlite3.Connection, draft_id: int) -> dict | None:
    """Fire the pick clock for a live draft whose deadline has passed (called
    by the draft-room WebSocket clock sweeper). Returns the auto-pick, or None
    when the draft isn't live or the clock hasn't expired yet."""
    with _draft_lock(draft_id):
        row = con.execute(
            "SELECT status FROM drafts WHERE id = ?", (draft_id,)).fetchone()
        if row and row["status"] == "stalled":
            return None  # terminal: pool exhausted, see below
        draft = _revive_draft(con, draft_id)
        if draft.status != Draft.STATUS_LIVE or draft.pick_deadline is None:
            return None
        try:
            pick = draft.expire_pick()
        except ClockNotExpired:
            return None
        except PoolExhausted as e:
            # The draft can never advance — no eligible players remain for
            # the on-clock team. Park it in a terminal 'stalled' state with
            # the reason logged, instead of leaving a 'live' draft whose
            # clock the sweeper retries (and warns about) every second.
            with con:
                con.execute(
                    "UPDATE drafts SET status = 'stalled', pick_deadline = NULL"
                    " WHERE id = ?", (draft_id,))
            log.error("draft %s stalled: %s", draft_id, e)
            return None
        except DraftError as e:
            raise _draft_error_to_http(e)
        _commit_pick(con, draft_id, draft, pick)
        return _pick_out(pick)


def get_league_draft(con: sqlite3.Connection, league_id: int) -> dict | None:
    """The league's most recent draft row (for the draft room), or None."""
    row = con.execute(
        "SELECT id FROM drafts WHERE league_id = ? ORDER BY id DESC LIMIT 1",
        (league_id,),
    ).fetchone()
    if not row:
        return None
    return _draft_row(con, row["id"])


def draft_snapshot(con: sqlite3.Connection, draft_id: int) -> dict:
    """Full draft-room state: draft row + live engine snapshot (picks,
    rosters, DND, on-clock team, deadline). Drives the WebSocket room."""
    row = _draft_row(con, draft_id)
    eng = _revive_draft(con, draft_id)
    snap = eng.to_dict()
    snap["draft"]["id"] = row["id"]
    snap["draft"]["league_id"] = row["league_id"]
    return snap


def set_dnd(con: sqlite3.Connection, draft_id: int, team_id: int,
            player_id: int, blocked: bool = True) -> dict:
    """Add/remove a player on a team's do-not-draft list during a live draft.
    Auto-pick skips DND players; manual picks of them are rejected."""
    with _draft_lock(draft_id):
        draft = _revive_draft(con, draft_id)
        if draft.status != Draft.STATUS_LIVE:
            raise HTTPException(
                409, f"draft is {draft.status}; DND changes need a live draft")
        league_id = con.execute(
            "SELECT league_id FROM drafts WHERE id = ?", (draft_id,)
        ).fetchone()["league_id"]
        team_ids = {t["id"] for t in _teams(con, league_id)}
        if team_id not in team_ids:
            raise HTTPException(404, f"team {team_id} not in this draft")
        if not con.execute(
                "SELECT 1 FROM players WHERE id = ?", (player_id,)).fetchone():
            raise HTTPException(404, f"player {player_id} not found")
        dnd = draft.dnd.setdefault(team_id, set())
        if blocked:
            dnd.add(player_id)
        else:
            dnd.discard(player_id)
        _put_cached("draft", draft_id, draft, con)
        return {"draft_id": draft_id, "team_id": team_id, "dnd": sorted(dnd)}


def get_team_ranks(con: sqlite3.Connection, team_id: int) -> list[int]:
    """A team's custom pre-draft ranks (ordered player ids); [] = none set."""
    get_team(con, team_id)  # 404 if missing
    return _team_ranks(con, team_id)


def set_team_ranks(con: sqlite3.Connection, team_id: int,
                   player_ids: list[int]) -> dict:
    """Replace a team's custom pre-draft ranks (P4-W17).

    The draft engine reads pre_draft_ranks for auto-pick order; until
    now nothing could write them, so auto-pick always fell back to
    league preseason ranks. An empty list clears the custom ranks.
    When the team's league has a live draft, its in-memory ranks are
    refreshed too (mirroring set_dnd), so the change bites on the
    very next auto-pick.
    """
    team = get_team(con, team_id)  # 404 if missing
    if len(player_ids) != len(set(player_ids)):
        raise HTTPException(422, "player_ids contains duplicates")
    if len(player_ids) > 500:
        raise HTTPException(422, "rank list too long (max 500)")
    for pid in player_ids:
        if not con.execute(
                "SELECT 1 FROM players WHERE id = ?", (pid,)).fetchone():
            raise HTTPException(404, f"player {pid} not found")
    with con:
        con.execute("DELETE FROM pre_draft_ranks WHERE team_id = ?", (team_id,))
        con.executemany(
            "INSERT INTO pre_draft_ranks (team_id, player_id, rank) VALUES (?, ?, ?)",
            [(team_id, pid, i + 1) for i, pid in enumerate(player_ids)],
        )
    # Refresh a live draft's in-memory ranks for this team, if any.
    row = con.execute(
        "SELECT id FROM drafts WHERE league_id = ? ORDER BY id DESC LIMIT 1",
        (team["league_id"],),
    ).fetchone()
    if row:
        draft_row = _draft_row(con, row["id"])
        if draft_row["status"] == Draft.STATUS_LIVE:
            with _draft_lock(row["id"]):
                draft = _revive_draft(con, row["id"])
                draft.ranks[team_id] = list(player_ids)
                _put_cached("draft", row["id"], draft, con)
    return {"team_id": team_id, "player_ids": list(player_ids)}


def _week1_slot(con: sqlite3.Connection, team_id: int, player_id: int) -> str | None:
    """The player's week-1 lineup slot, or None if not in it."""
    row = con.execute(
        "SELECT slot FROM roster_slots WHERE team_id = ? AND player_id = ?"
        " AND week_no = 1",
        (team_id, player_id),
    ).fetchone()
    return row["slot"] if row else None


def _move_into_week1_slot(con: sqlite3.Connection, team_id: int,
                          drop_pid: int, add_pid: int) -> None:
    """Move add_pid into drop_pid's vacated week-1 lineup slot (same team).

    Used by waiver wins. P4-W30: the slot write is SKIPPED when the
    added player is not role-eligible for the vacated slot (per
    constants.SLOT_ELIGIBILITY; IL additionally requires IL
    eligibility, mirroring api.validation.validate_lineup) — a
    slot-ineligible player is never written into a saved lineup. The
    drop's row is still removed (the slot is vacated) and the manager
    places the add via PUT /teams/{id}/lineup.
    """
    if drop_pid is None:
        return
    slot = _week1_slot(con, team_id, drop_pid)
    if slot is None:
        return
    con.execute(
        "DELETE FROM roster_slots WHERE team_id = ? AND player_id = ?"
        " AND week_no = 1",
        (team_id, drop_pid),
    )
    meta = player_roles_map(con).get(add_pid) or {}
    role = meta.get("role")
    eligible = role in constants.SLOT_ELIGIBILITY.get(slot, ())
    if slot == "IL" and not meta.get("il_eligible"):
        eligible = False
    if not eligible:
        log.warning(
            "team %s: waiver add %s (role %s) is not eligible for the "
            "vacated week-1 %s slot — slot write skipped",
            team_id, add_pid, role, slot)
        return
    con.execute(
        "INSERT INTO roster_slots (team_id, player_id, slot, week_no)"
        " VALUES (?, ?, ?, 1)",
        (team_id, add_pid, slot),
    )


def _swap_week1_slots(con: sqlite3.Connection, team_a: int, team_b: int,
                      pids_a: list[int], pids_b: list[int]) -> None:
    """Paired week-1 slot swap for an executed N-for-N trade.

    pids_a[i] (moving A->B) takes pids_b[i]'s vacated week-1 slot on team B
    and vice versa — the Yahoo convention that keeps both lineups' slot
    counts intact. The trade engine guarantees balanced counts.
    """
    slots_a = {pid: _week1_slot(con, team_a, pid) for pid in pids_a}
    slots_b = {pid: _week1_slot(con, team_b, pid) for pid in pids_b}
    for pa, pb in zip(pids_a, pids_b):
        sa, sb = slots_a[pa], slots_b[pb]
        for pid, slot in ((pa, sa), (pb, sb)):
            if slot is not None:
                con.execute(
                    "DELETE FROM roster_slots WHERE team_id = ? AND player_id = ?"
                    " AND week_no = 1",
                    (team_a if pid == pa else team_b, pid),
                )
        # pa -> team B in pb's old slot; pb -> team A in pa's old slot.
        if sb is not None:
            con.execute(
                "INSERT INTO roster_slots (team_id, player_id, slot, week_no)"
                " VALUES (?, ?, ?, 1)",
                (team_b, pa, sb),
            )
        if sa is not None:
            con.execute(
                "INSERT INTO roster_slots (team_id, player_id, slot, week_no)"
                " VALUES (?, ?, ?, 1)",
                (team_a, pb, sa),
            )


def _generate_schedule(con: sqlite3.Connection, league_id: int) -> None:
    """Write the weeks 1–6 H2H schedule at draft completion (P2-L5 engine).

    Odd team counts get a bye: a BYE sentinel rounds the circle-method
    input up to even, and pairings against it are skipped (no matchup row).
    Idempotent: any existing rows for the league are replaced, so a
    re-fired completion side effect can't double the schedule.
    """
    con.execute("DELETE FROM matchups WHERE league_id = ?", (league_id,))
    teams = [(t["id"], t["name"]) for t in _teams(con, league_id)]
    BYE = -1
    if len(teams) % 2 == 1:
        teams.append((BYE, "BYE"))
    try:
        sched = generate_schedule(
            ScheduleConfig(teams=tuple(teams), seed=league_id))
    except ScheduleError as e:
        raise HTTPException(500, f"schedule generation failed: {e}")
    for week_no, pairs in sched.items():
        for a, b in pairs:
            if a == BYE or b == BYE:
                continue  # bye week — no matchup row
            con.execute(
                "INSERT INTO matchups (league_id, week_no, team_a_id,"
                " team_b_id, status) VALUES (?, ?, ?, ?, 'scheduled')",
                (league_id, week_no, a, b),
            )


def _auto_set_week1_lineups(con: sqlite3.Connection, league_id: int, season: str) -> None:
    """Set each team's week-1 lineup to its best-ADP D8-legal 11 (BN×3, IL empty).

    Yahoo-style default: managers get a legal starting lineup the moment the
    draft completes and can adjust before the weekly lock (D5).
    """
    rows = con.execute(
        """SELECT dp.team_id, dp.player_id FROM draft_picks dp
           JOIN drafts d ON d.id = dp.draft_id
           WHERE d.league_id = ?""",
        (league_id,),
    ).fetchall()
    by_team: dict[int, list[int]] = {}
    for r in rows:
        by_team.setdefault(r["team_id"], []).append(r["player_id"])
    roles = player_roles_map(con, season)
    adp = {
        r["player_id"]: r["r"]
        for r in con.execute(
            "SELECT player_id, MIN(rank) AS r FROM pre_draft_ranks GROUP BY player_id"
        ).fetchall()
    }
    for team_id, pids in by_team.items():
        if len(pids) != constants.DRAFT_ROUNDS:
            raise HTTPException(
                500, f"team {team_id} drafted {len(pids)} players, "
                     f"expected {constants.DRAFT_ROUNDS}")
        adp_index = {pid: adp.get(pid, 10 ** 9) for pid in pids}
        assignment = solve_best_d8_lineup(pids, roles, adp_index)
        con.executemany(
            "INSERT INTO roster_slots (team_id, player_id, slot, week_no)"
            " VALUES (?, ?, ?, 1)",
            [(team_id, pid, slot) for pid, slot in assignment.items()],
        )


# ---------------------------------------------------------------------------
# waivers
# ---------------------------------------------------------------------------

def _build_waiver(con: sqlite3.Connection, league_id: int) -> WaiverEngine:
    teams = _teams(con, league_id)
    rosters = {t["id"]: _roster_pids(con, t["id"]) for t in teams}
    league = get_league(con, league_id)
    pool = _pool_ranked(con, league_id, league["season"])
    eng = WaiverEngine(rosters, pool, budget=constants.FAAB_BUDGET)
    eng.remaining = {t["id"]: t["faab_remaining"] for t in teams}
    return eng


def _revive_waiver(con: sqlite3.Connection, league_id: int) -> WaiverEngine:
    cached = _get_cached("waiver", league_id)
    if cached is not None:
        return cached
    state = _load_state(con, "waiver", league_id)
    if state is None:
        eng = _build_waiver(con, league_id)
    else:
        eng = WaiverEngine.from_dict(state)
        # JSON round-trip leaves dict keys as strings; normalize to ints.
        # Bid keys are NOT touched here — from_dict already restored
        # them to (int, int) tuples (P4-W24: normalize exactly once;
        # re-normalizing them here crashed on the tuple keys).
        eng._rosters = {int(k): list(v) for k, v in eng._rosters.items()}
        eng.remaining = {int(k): v for k, v in eng.remaining.items()}
        eng._frozen = {int(k): v for k, v in eng._frozen.items()}
    _registry[("waiver", league_id)] = eng
    return eng


DEFAULT_CANT_CUT_TOP_N = 12


def cant_cut_player_ids(con: sqlite3.Connection, league_id: int) -> tuple[set[int], str]:
    """The league's effective can't-cut set (P4-W22, blueprint §5):
    the commissioner's custom list (settings.cant_cut_player_ids) when
    set — an empty list turns the feature off — otherwise the top-N
    players by preseason rank (settings.cant_cut_top_n, default 12;
    rank = MIN over the league's teams' pre-draft ranks, as the
    players list projects it). Returns (player_ids, source)."""
    league = get_league(con, league_id)
    settings = league["settings"]
    custom = settings.get("cant_cut_player_ids")
    if custom is not None:
        return {int(p) for p in custom}, "custom"
    top_n = settings.get("cant_cut_top_n", DEFAULT_CANT_CUT_TOP_N)
    if not top_n:
        return set(), "off"
    rows = con.execute(
        """SELECT r.player_id, MIN(r.rank) AS rk FROM pre_draft_ranks r
           JOIN teams t ON t.id = r.team_id WHERE t.league_id = ?
           GROUP BY r.player_id ORDER BY rk, r.player_id LIMIT ?""",
        (league_id, int(top_n)),
    ).fetchall()
    return {r["player_id"] for r in rows}, "preseason_top_n"


def submit_waiver_claim(con: sqlite3.Connection, league_id: int, team_id: int,
                        week_no: int, add_player_id: int,
                        drop_player_id: int | None, bid: int) -> dict:
    get_league(con, league_id)
    # P4-W28: no new claims past the season. A target week beyond
    # TOTAL_WEEKS is out of range, and once the final week
    # (TOTAL_WEEKS) itself is final the season is over — even though
    # current_week is capped at TOTAL_WEEKS, a claim must not be
    # re-filed into that already-final week.
    if not 1 <= week_no <= constants.TOTAL_WEEKS:
        raise HTTPException(
            422,
            f"week_no must be 1..{constants.TOTAL_WEEKS}: the season is "
            f"complete after week {constants.TOTAL_WEEKS}, so no new "
            "waiver claims are accepted",
        )
    final_week = con.execute(
        "SELECT MAX(week_no) FROM matchups WHERE league_id = ?"
        " AND status = 'final'",
        (league_id,),
    ).fetchone()[0] or 0
    if final_week >= constants.TOTAL_WEEKS:
        raise HTTPException(
            422,
            f"season is complete: week {constants.TOTAL_WEEKS} is "
            "final, so no new waiver claims are accepted",
        )
    team_ids = {t["id"] for t in _teams(con, league_id)}
    if team_id not in team_ids:
        raise HTTPException(404, f"team {team_id} not found")
    if drop_player_id is None and \
            len(_roster_pids(con, team_id)) >= constants.ROSTER_SIZE:
        # P4-W26: a drop is required only when the roster is full at
        # 15; a team under 15 (the draft fills only 14) may claim with
        # no drop and fill its open spot. The engine enforces the same
        # rule against its roster state — this is the API-layer guard.
        raise HTTPException(
            422, "a drop_player_id is required — this team's roster is "
                 f"full at {constants.ROSTER_SIZE}")
    if drop_player_id is not None:
        protected, _src = cant_cut_player_ids(con, league_id)
        if drop_player_id in protected:
            row = con.execute("SELECT name FROM players WHERE id = ?",
                              (drop_player_id,)).fetchone()
            raise HTTPException(
                422,
                f"{row['name'] if row else 'that player'} is on the can't-cut "
                "list and cannot be dropped",
            )
    eng = _revive_waiver(con, league_id)
    # D8-reachability guard (P4-W30, mirroring the P4-W24 trade guard):
    # the waiver engine holds no player metadata, so check here that
    # the post-swap roster can still field a D8-legal XI (exact check
    # via _unfieldable_after_swap / d8_reachable at picks_remaining=0).
    # Only checked when the swap is well-formed enough for the
    # engine's own validation to pass it — the add is claimable and
    # the drop (when named) is actually rostered; otherwise the
    # engine raises the more specific 422. A no-drop claim is checked
    # as a pure addition (roster + add).
    roster = _roster_pids(con, team_id)
    if add_player_id in eng.pool and add_player_id not in roster \
            and (drop_player_id is None or drop_player_id in roster):
        after = [p for p in roster if p != drop_player_id] + [add_player_id]
        bad = _unfieldable_after_swap(con, {team_id: after})
        if bad is not None:
            name = next((t["name"] for t in _teams(con, league_id)
                         if t["id"] == bad), f"team {bad}")
            raise HTTPException(
                422,
                f"waiver claim would leave {name} unable to field a "
                "legal XI (role minimums / overseas cap) — rejected "
                "by the D8 guard")
    try:
        eng.submit_bid(team_id, week_no, add_player_id, bid,
                       drop_player_id=drop_player_id)
    except WaiverError as e:
        raise HTTPException(422, str(e))
    cur = con.execute(
        "INSERT INTO waiver_claims (league_id, week_no, team_id, add_player_id,"
        " drop_player_id, bid, status) VALUES (?, ?, ?, ?, ?, ?, 'pending')",
        (league_id, week_no, team_id, add_player_id, drop_player_id, bid),
    )
    _put_cached("waiver", league_id, eng, con)
    return {
        "id": cur.lastrowid, "week_no": week_no, "team_id": team_id,
        "add_player_id": add_player_id, "drop_player_id": drop_player_id,
        "bid": bid, "status": "pending",
    }


def run_waivers(con: sqlite3.Connection, league_id: int, week_no: int) -> list[dict]:
    get_league(con, league_id)
    # P4-W28: bound the run like the reads — a week-9 run must never
    # execute phantom post-season claims (defence in depth behind the
    # router's Query(ge=1, le=TOTAL_WEEKS) validation).
    if not 1 <= week_no <= constants.TOTAL_WEEKS:
        raise HTTPException(
            422, f"week_no must be 1..{constants.TOTAL_WEEKS}")
    eng = _revive_waiver(con, league_id)
    # D8 re-check at run time (P4-W30, mirroring the trade settle
    # re-check in _settle_trades): rosters can change between bid and
    # run, so a claim that was fieldable at submission may brick the
    # team by run time. The engine evaluates the callback against the
    # actual post-swap roster at settlement; a rejected swap is
    # forfeited to the next bidder (the claim resolves 'lost' below,
    # the team appears in the result's forfeited_by, no FAAB is
    # deducted and no swap executes) while other claims still process.
    roles = player_roles_map(con)

    def _swap_stays_fieldable(tid: int, pid: int, post: list) -> bool:
        d, o = _role_counts(post, roles)
        if d8_reachable(d, o, 0):
            return True
        log.warning(
            "league %s: waiver claim by team %s for player %s would "
            "leave the team unable to field a legal XI (D8) at run "
            "time — claim forfeited, swap not executed",
            league_id, tid, pid)
        return False

    try:
        results = eng.run_week(week_no, standings_best_first(con, league_id),
                               validate_swap=_swap_stays_fieldable)
    except WaiverError as e:
        raise HTTPException(422, str(e))
    out = []
    with con:
        for r in results:
            winner = r["winner"]
            # Project claim rows to won/lost.
            for row in con.execute(
                "SELECT id, team_id FROM waiver_claims WHERE league_id = ?"
                " AND week_no = ? AND add_player_id = ? AND status = 'pending'",
                (league_id, week_no, r["player_id"]),
            ):
                status = "won" if row["team_id"] == winner else "lost"
                con.execute(
                    "UPDATE waiver_claims SET status = ? WHERE id = ?",
                    (status, row["id"]),
                )
            if winner is not None:
                if r["drop"] is None:
                    # Pure-addition win (no-drop claim): no slot to
                    # steal — the add joins the construction roster on
                    # the bench and no saved lineup is touched.
                    con.execute(
                        "INSERT INTO roster_slots (team_id, player_id, slot, week_no)"
                        " VALUES (?, ?, 'BN', NULL)",
                        (winner, r["player_id"]),
                    )
                else:
                    # Swap roster_slots: the added player takes the dropped slot.
                    slot = con.execute(
                        "SELECT slot FROM roster_slots WHERE team_id = ?"
                        " AND player_id = ? AND week_no IS NULL",
                        (winner, r["drop"]),
                    ).fetchone()
                    slot_name = slot["slot"] if slot else "BN"
                    con.execute(
                        "DELETE FROM roster_slots WHERE team_id = ? AND player_id = ?"
                        " AND week_no IS NULL",
                        (winner, r["drop"]),
                    )
                    con.execute(
                        "INSERT INTO roster_slots (team_id, player_id, slot, week_no)"
                        " VALUES (?, ?, ?, NULL)",
                        (winner, r["player_id"], slot_name),
                    )
                    # Keep the week-1 lineup consistent: the add takes the drop's
                    # vacated week-1 slot (skipped when slot-ineligible, P4-W30).
                    _move_into_week1_slot(con, winner, r["drop"], r["player_id"])
                con.execute(
                    "UPDATE teams SET faab_remaining = ? WHERE id = ?",
                    (eng.remaining[winner], winner),
                )
            out.append({
                "player_id": r["player_id"],
                "winner_team_id": winner,
                "amount": r["amount"],
                "drop_player_id": r["drop"],
                "forfeited_by": r["forfeited_by"],
            })
    _put_cached("waiver", league_id, eng, con)
    return out


# ---------------------------------------------------------------------------
# trades
# ---------------------------------------------------------------------------

def _commissioner_team(con: sqlite3.Connection, league_id: int) -> int:
    league = get_league(con, league_id)
    row = con.execute(
        "SELECT id FROM teams WHERE league_id = ? AND owner_id = ?",
        (league_id, league.get("commissioner_id")),
    ).fetchone()
    if row:
        return row["id"]
    first = con.execute(
        "SELECT id FROM teams WHERE league_id = ? ORDER BY id", (league_id,)
    ).fetchone()
    return first["id"]


def _build_trade(con: sqlite3.Connection, league_id: int) -> TradeEngine:
    teams = _teams(con, league_id)
    rosters = {t["id"]: _roster_pids(con, t["id"]) for t in teams}
    empty = [t["id"] for t in teams if not rosters[t["id"]]]
    if empty:
        raise HTTPException(
            409, f"draft not complete — teams {empty} have empty rosters")
    return TradeEngine(rosters, _commissioner_team(con, league_id))


def _revive_trade(con: sqlite3.Connection, league_id: int) -> TradeEngine:
    cached = _get_cached("trade", league_id)
    if cached is not None:
        return cached
    state = _load_state(con, "trade", league_id)
    if state is None:
        eng = _build_trade(con, league_id)
    else:
        # Normalize JSON string keys before the constructor validates.
        eng = TradeEngine.from_dict({
            "commissioner": state["commissioner"],
            "rosters": {int(k): [int(p) for p in v]
                        for k, v in state["rosters"].items()},
            "next_id": state["next_id"],
            "trades": {
                tid_s: {**t,
                        "parties": [int(p) for p in t["parties"]],
                        "vetoes": [int(v) for v in t["vetoes"]],
                        "gives": {int(k): [int(p) for p in v]
                                  for k, v in t["gives"].items()}}
                for tid_s, t in state["trades"].items()
            },
        })
    _registry[("trade", league_id)] = eng
    return eng


_TRADE_STATUS_MAP = {
    TradeEngine.STATUS_PROPOSED: "proposed",
    TradeEngine.STATUS_ACCEPTED: "accepted",
    TradeEngine.STATUS_UNDER_REVIEW: "accepted",  # offeree accepted; review open
    TradeEngine.STATUS_EXECUTED: "accepted",      # swap done; contract has no 'executed'
    TradeEngine.STATUS_DECLINED: "rejected",
    TradeEngine.STATUS_WITHDRAWN: "rejected",
    TradeEngine.STATUS_VETOED: "vetoed",
    TradeEngine.STATUS_EXPIRED: "expired",
}


def _iso(ts) -> str | None:
    """Epoch seconds -> ISO UTC string (same format as review_deadline)."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts)) if ts else None


def _trade_detail(trade: dict) -> dict:
    """History detail (P4-W1): veto count + lifecycle timestamps.

    The engine stamps `decided_at` at the terminal transition; it is the
    veto moment for a vetoed trade and the execution moment for an
    executed one, so vetoed_at/executed_at split it by final status.
    """
    decided_at = trade.get("decided_at")
    status = trade["status"]
    return {
        "veto_count": len(trade.get("vetoes") or []),
        "proposed_at": _iso(trade.get("proposed_at")),
        "accepted_at": _iso(trade.get("accepted_at")),
        "vetoed_at": _iso(decided_at)
                     if status == TradeEngine.STATUS_VETOED else None,
        "executed_at": _iso(decided_at)
                       if status == TradeEngine.STATUS_EXECUTED else None,
    }


def _trade_to_out(trade: dict, db_id: int) -> dict:
    """Project an engine trade to the API contract.

    db_id is the trades-table id — the only id the API ever exposes.
    The engine-internal id never leaves the service layer.
    """
    proposer, offeree = trade["parties"][0], trade["parties"][1]
    gives = trade["gives"]
    return {
        "id": db_id,
        "league_id": None,  # filled by caller
        "from_team_id": proposer,
        "to_team_id": offeree,
        "gives": list(gives.get(proposer, [])),
        "receives": list(gives.get(offeree, [])),
        "status": _TRADE_STATUS_MAP[trade["status"]],
        "review_deadline": _iso(trade.get("review_until")),
        **_trade_detail(trade),
    }


def _db_id_for_engine(con: sqlite3.Connection, league_id: int, engine_id: int) -> int:
    """trades-table id for an engine trade id (must exist after sync)."""
    row = con.execute(
        "SELECT id FROM trades WHERE league_id = ? AND engine_id = ?",
        (league_id, engine_id),
    ).fetchone()
    if not row:
        raise HTTPException(500, f"trade engine_id {engine_id} has no DB row")
    return row["id"]


def _sync_trade_row(con: sqlite3.Connection, league_id: int, trade: dict) -> int:
    """Mirror engine trade into the trades table (read projection).

    Returns the trades-table id — the only trade id the API exposes.
    """
    detail = _trade_detail(trade)
    row = con.execute(
        "SELECT id FROM trades WHERE league_id = ? AND engine_id = ?",
        (league_id, trade["id"]),
    ).fetchone()
    if row:
        db_id = row["id"]
    else:
        # Insert first so _trade_to_out can carry the real DB id.
        cur = con.execute(
            "INSERT INTO trades (league_id, from_team_id, to_team_id, gives,"
            " receives, status, review_deadline, engine_id, veto_count,"
            " proposed_at, accepted_at, vetoed_at, executed_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (league_id, trade["parties"][0], trade["parties"][1],
             json.dumps(list(trade["gives"].get(trade["parties"][0], []))),
             json.dumps(list(trade["gives"].get(trade["parties"][1], []))),
             _TRADE_STATUS_MAP[trade["status"]],
             _iso(trade.get("review_until")),
             trade["id"],
             detail["veto_count"], detail["proposed_at"],
             detail["accepted_at"], detail["vetoed_at"],
             detail["executed_at"]),
        )
        db_id = cur.lastrowid
    out = _trade_to_out(trade, db_id)
    con.execute(
        "UPDATE trades SET status = ?, review_deadline = ?, veto_count = ?,"
        " proposed_at = ?, accepted_at = ?, vetoed_at = ?, executed_at = ?"
        " WHERE id = ?",
        (out["status"], out["review_deadline"], out["veto_count"],
         out["proposed_at"], out["accepted_at"], out["vetoed_at"],
         out["executed_at"], db_id),
    )
    return db_id


def _role_counts(player_ids, roles: dict) -> tuple[dict, dict]:
    """(domestic_by_role, overseas_by_role) for a flat player-id list —
    the input shape draft_engine.d8_reachable consumes."""
    d: dict = {}
    o: dict = {}
    for pid in player_ids:
        meta = roles.get(pid) or {}
        target = o if meta.get("is_overseas") else d
        role = meta.get("role")
        target[role] = target.get(role, 0) + 1
    return d, o


def _unfieldable_after_swap(con: sqlite3.Connection, rosters_after: dict) -> int | None:
    """Return the first team id whose post-swap roster cannot field a
    D8-legal XI (exact check via d8_reachable at picks_remaining=0), or
    None when both sides stay fieldable (P4-W24 D8 guard, league-core
    filing)."""
    roles = player_roles_map(con)
    for tid, pids in rosters_after.items():
        d, o = _role_counts(pids, roles)
        if not d8_reachable(d, o, 0):
            return tid
    return None


def _settle_trades(con: sqlite3.Connection, league_id: int) -> None:
    """Expire stale proposals; execute review-closed trades (roster swap)."""
    try:
        eng = _revive_trade(con, league_id)
    except TradeError as e:
        # P4-W29: a pre-existing sub-14 roster (left behind by a fiat
        # drop from before the commissioner-drop floor below, e.g. the
        # Pi demo league's 13-man team) makes TradeEngine construction
        # fail for the whole league. That must not 500 every trade
        # read/write league-wide: skip settling for this league — the
        # defined fate, following the P4-W23 pattern below — log loudly
        # so the commissioner sees it, and let reads serve the trades
        # table projection. Propose/accept revive the engine themselves
        # and surface this as a 422 instead.
        log.warning(
            "league %s: trade engine cannot be constructed (%s) — "
            "skipping trade settle for this league", league_id, e)
        return
    now = time.time()
    changed = eng.sweep(now=now)
    for tid, trade in list(eng._trades.items()):
        if trade["status"] == TradeEngine.STATUS_UNDER_REVIEW \
                and now >= (trade["review_until"] or float("inf")):
            # D8 re-check at settle: rosters may have changed during the
            # review window (another trade executed first), so a swap
            # that was legal at proposal can now brick a team's lineup.
            a0, b0 = trade["parties"][0], trade["parties"][1]
            gives0 = trade["gives"]
            after = {
                a0: [p for p in eng._rosters[a0] if p not in gives0[a0]] + list(gives0[b0]),
                b0: [p for p in eng._rosters[b0] if p not in gives0[b0]] + list(gives0[a0]),
            }
            bad = _unfieldable_after_swap(con, after)
            if bad is not None:
                log.warning(
                    "league %s: trade %s would leave team %s unable to field "
                    "a legal XI (D8) — expiring it instead of executing",
                    league_id, tid, bad)
                trade["status"] = TradeEngine.STATUS_EXPIRED
                trade["decided_at"] = now
                changed.append(tid)
                continue
            try:
                result = eng.execute(tid, now=now)
            except TradeError as e:
                # P4-W23: the trade can never execute — its players were
                # already moved by another executed trade (the engine
                # validates before mutating, P4-L1, so rosters are
                # untouched). Give it a defined terminal fate instead of
                # 500ing every trade read for the league forever: expire
                # it (a status the API contract already exposes) and log
                # loudly so the commissioner sees it in the server log.
                log.warning(
                    "league %s: trade %s cannot execute (%s) — expiring it",
                    league_id, tid, e)
                trade["status"] = TradeEngine.STATUS_EXPIRED
                trade["decided_at"] = now
                changed.append(tid)
                continue
            if result["status"] == TradeEngine.STATUS_EXECUTED:
                a, b = result["parties"][0], result["parties"][1]
                gives = result["gives"]
                for pid in gives[a]:
                    con.execute(
                        "UPDATE roster_slots SET team_id = ? WHERE team_id = ?"
                        " AND player_id = ? AND week_no IS NULL", (b, a, pid))
                for pid in gives[b]:
                    con.execute(
                        "UPDATE roster_slots SET team_id = ? WHERE team_id = ?"
                        " AND player_id = ? AND week_no IS NULL", (a, b, pid))
                # Week-1 lineups: paired slot swap so both XIs keep their
                # D7 slot counts (Yahoo convention).
                _swap_week1_slots(con, a, b, gives[a], gives[b])
            changed.append(tid)
    with con:
        for tid in eng._trades:
            _sync_trade_row(con, league_id, eng._trades[tid])
    if changed:
        _put_cached("trade", league_id, eng, con)


def propose_trade(con: sqlite3.Connection, league_id: int, from_team_id: int,
                  to_team_id: int, gives: list[int], receives: list[int]) -> dict:
    get_league(con, league_id)
    _settle_trades(con, league_id)
    # D8-reachability guard (P4-W24, league-core filing): the trade
    # engine holds no player metadata, so check here that the swap
    # leaves BOTH teams able to field a D8-legal XI. Only checked when
    # the offered players are actually on the offering rosters —
    # otherwise the engine's own validation raises the right 422.
    rosters = {t["id"]: _roster_pids(con, t["id"]) for t in _teams(con, league_id)}
    if from_team_id in rosters and to_team_id in rosters \
            and set(gives) <= set(rosters[from_team_id]) \
            and set(receives) <= set(rosters[to_team_id]):
        after = {
            from_team_id: [p for p in rosters[from_team_id] if p not in gives] + list(receives),
            to_team_id: [p for p in rosters[to_team_id] if p not in receives] + list(gives),
        }
        bad = _unfieldable_after_swap(con, after)
        if bad is not None:
            name = next((t["name"] for t in _teams(con, league_id) if t["id"] == bad),
                        f"team {bad}")
            raise HTTPException(
                422,
                f"trade would leave {name} unable to field a legal XI "
                "(role minimums / overseas cap) — rejected by the D8 guard")
    try:
        # Revive inside the try (P4-W29): with a pre-existing sub-14
        # roster in the league, construction itself raises TradeError —
        # surface it as the same defined 422 as any other illegal trade,
        # never a 500.
        eng = _revive_trade(con, league_id)
        trade = eng.propose(from_team_id, to_team_id, list(gives),
                            list(receives), week=current_week(con, league_id))
    except TradeError as e:
        raise HTTPException(422, str(e))
    with con:
        _sync_trade_row(con, league_id, trade)
    _put_cached("trade", league_id, eng, con)
    out = _trade_to_out(trade, _db_id_for_engine(con, league_id, trade["id"]))
    out["league_id"] = league_id
    return out


def _db_engine_id(con: sqlite3.Connection, league_id: int, trade_id: int) -> int:
    """DB trade id -> engine trade id."""
    row = con.execute(
        "SELECT engine_id FROM trades WHERE id = ? AND league_id = ?",
        (trade_id, league_id),
    ).fetchone()
    if not row or row["engine_id"] is None:
        raise HTTPException(404, f"trade {trade_id} not found")
    return row["engine_id"]


def respond_trade(con: sqlite3.Connection, league_id: int, trade_id: int,
                   action: str, team_id: int | None = None) -> dict:
    get_league(con, league_id)
    # 404 on unknown trade before touching engine state (draft may be live).
    eid = _db_engine_id(con, league_id, trade_id)
    _settle_trades(con, league_id)
    try:
        # Revive inside the try (P4-W29): same construction-failure ->
        # 422 conversion as propose_trade, never a 500.
        eng = _revive_trade(con, league_id)
        if action == "accept":
            trade = eng.get_trade(eid)
            offeree = trade["parties"][1]
            trade = eng.accept(eid, offeree)
        elif action == "reject":
            trade = eng.get_trade(eid)
            offeree = trade["parties"][1]
            trade = eng.decline(eid, offeree)
        elif action == "veto":
            if team_id is None:
                raise HTTPException(422, "veto requires team_id")
            trade = eng.veto(eid, team_id)
        else:
            raise HTTPException(400, f"unknown action {action}")
    except TradeError as e:
        raise HTTPException(422, str(e))
    with con:
        _sync_trade_row(con, league_id, trade)
    _put_cached("trade", league_id, eng, con)
    out = _trade_to_out(trade, _db_id_for_engine(con, league_id, trade["id"]))
    out["league_id"] = league_id
    return out


def commissioner_roster_move(con: sqlite3.Connection, league_id: int,
                             team_id: int, player_id: int, action: str,
                             note: str) -> dict:
    """Commissioner roster fiat (P4-W25): add/drop a player by decree,
    with a mandatory audit note in league_adjustments.

    Add respects league-wide ownership and the 15-man cap. Drop also
    clears the player from the team's saved weekly lineups, and is
    refused while the team has a pending waiver claim using this
    player as its drop piece (the claim would strand mid-run — the
    drop-freeze tangle the commissioner must resolve first). Drop is
    also floored at ACTIVE_ROSTER_SIZE (14) players (P4-W29): a roster
    below that makes TradeEngine construction fail league-wide, so a
    fiat drop must never create one. Engine
    caches for the league are invalidated so waiver/trade engines
    revive from the new rosters."""
    get_league(con, league_id)
    team = next((t for t in _teams(con, league_id) if t["id"] == team_id), None)
    if team is None:
        raise HTTPException(404, f"team {team_id} not found in league {league_id}")
    prow = con.execute("SELECT name FROM players WHERE id = ?",
                       (player_id,)).fetchone()
    if not prow:
        raise HTTPException(404, f"player {player_id} not found")
    player_name = prow["name"]
    if action == "add":
        owner = owned_map(con, league_id).get(player_id)
        if owner is not None:
            raise HTTPException(
                409, f"{player_name} is already rostered in this league "
                     f"(team {owner})")
        count = con.execute(
            "SELECT COUNT(*) FROM roster_slots WHERE team_id = ? AND week_no IS NULL",
            (team_id,)).fetchone()[0]
        if count >= constants.ROSTER_SIZE:
            raise HTTPException(
                422, f"team already carries {constants.ROSTER_SIZE} players — "
                     "drop someone first")
        con.execute(
            "INSERT INTO roster_slots (team_id, player_id, slot, week_no)"
            " VALUES (?, ?, 'BN', NULL)", (team_id, player_id))
        kind = "roster_add"
    else:  # drop
        on_roster = con.execute(
            "SELECT 1 FROM roster_slots WHERE team_id = ? AND player_id = ?"
            " AND week_no IS NULL", (team_id, player_id)).fetchone()
        if not on_roster:
            raise HTTPException(422, f"{player_name} is not on this team's roster")
        pending = con.execute(
            "SELECT COUNT(*) FROM waiver_claims WHERE team_id = ?"
            " AND drop_player_id = ? AND status = 'pending'",
            (team_id, player_id)).fetchone()[0]
        if pending:
            raise HTTPException(
                409, f"{player_name} is the drop piece of a pending waiver "
                     "claim for this team — resolve that claim first")
        # Roster floor (P4-W29): never drop below ACTIVE_ROSTER_SIZE.
        # Below 14 the trade engine refuses to construct for the whole
        # league, so one fiat drop used to brick all trading with 500s.
        count = con.execute(
            "SELECT COUNT(*) FROM roster_slots WHERE team_id = ? AND week_no IS NULL",
            (team_id,)).fetchone()[0]
        if count <= ACTIVE_ROSTER_SIZE:
            raise HTTPException(
                422, f"cannot drop {player_name}: this team has only "
                     f"{count} players — a commissioner drop cannot take "
                     f"a roster below {ACTIVE_ROSTER_SIZE} players; "
                     "add a player first")
        con.execute(
            "DELETE FROM roster_slots WHERE team_id = ? AND player_id = ?",
            (team_id, player_id))
        kind = "roster_drop"
    cur = con.execute(
        "INSERT INTO league_adjustments (league_id, team_id, kind, faab_delta,"
        " faab_after, player_id, player_name, note)"
        " VALUES (?, ?, ?, 0, ?, ?, ?, ?)",
        (league_id, team_id, kind, team["faab_remaining"], player_id,
         player_name, note))
    con.commit()
    _registry.pop(("waiver", league_id), None)
    _registry.pop(("trade", league_id), None)
    row = con.execute(
        "SELECT * FROM league_adjustments WHERE id = ?", (cur.lastrowid,)).fetchone()
    out = dict(row)
    out["team_name"] = team["name"]
    return out


def list_trades(con: sqlite3.Connection, league_id: int,
                status: str | None = None) -> list[dict]:
    get_league(con, league_id)
    has_rows = con.execute(
        "SELECT COUNT(*) FROM trades WHERE league_id = ?", (league_id,)
    ).fetchone()[0]
    if has_rows == 0 and _load_state(con, "trade", league_id) is None:
        return []  # draft not complete yet — no trades can exist
    _settle_trades(con, league_id)
    sql = "SELECT * FROM trades WHERE league_id = ?"
    params: list = [league_id]
    if status:
        sql += " AND status = ?"
        params.append(status)
    sql += " ORDER BY created_at DESC"
    out = []
    for r in con.execute(sql, params):
        keys = r.keys()
        out.append({
            "id": r["id"], "league_id": r["league_id"],
            "from_team_id": r["from_team_id"], "to_team_id": r["to_team_id"],
            "gives": json.loads(r["gives"] or "[]"),
            "receives": json.loads(r["receives"] or "[]"),
            "status": r["status"], "review_deadline": r["review_deadline"],
            # P4-W1 detail columns; guarded for pre-migration rows/DBs.
            "veto_count": (r["veto_count"] or 0) if "veto_count" in keys else 0,
            "proposed_at": r["proposed_at"] if "proposed_at" in keys else None,
            "accepted_at": r["accepted_at"] if "accepted_at" in keys else None,
            "vetoed_at": r["vetoed_at"] if "vetoed_at" in keys else None,
            "executed_at": r["executed_at"] if "executed_at" in keys else None,
        })
    return out
