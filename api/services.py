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
)
# P2-L7 exact best-ADP D8-legal-11 solver (lives in sandbox_season; pure function).
from api.engine.sandbox_season import solve_best_d8_lineup
from api.engine.matchup_scheduler import (
    ScheduleConfig, ScheduleError, generate_schedule,
)
from api.engine.trade_engine import TradeEngine, TradeError
from api.engine.waiver_engine import WaiverEngine, WaiverError

from . import constants
from .routers import get_league, owned_map, player_roles_map

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
    con.commit()


_registry: dict[tuple[str, int], object] = {}


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
    return (row[0] or 0) + 1


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
    ranks = {t["id"]: _team_ranks(con, t["id"]) for t in teams}
    cfg = DraftConfig(
        teams=tuple((t["id"], t["name"]) for t in teams),
        rounds=constants.DRAFT_ROUNDS,
        pick_clock_secs=90,
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
        on_clock = eng.on_clock_team_id if eng.status == Draft.STATUS_LIVE else None
    except HTTPException:
        on_clock = None
    return {
        "id": d["id"], "league_id": d["league_id"], "rounds": d["rounds"],
        "status": d["status"], "current_pick_no": d["current_pick_no"],
        "draft_order": order,
        "on_clock_team_id": on_clock,
    }


def make_pick(con: sqlite3.Connection, draft_id: int, team_id: int,
              player_id: int) -> dict:
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
    return {
        "pick_no": pick["pick_no"], "round_no": pick["round_no"],
        "team_id": pick["team_id"], "player_id": pick["player_id"],
        "is_auto": pick["is_auto"],
    }


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

    Used by waiver wins. If the added player isn't role-eligible for that
    slot the lineup reads valid=False until the manager fixes it via
    PUT /teams/{id}/lineup (same honesty as Yahoo's post-waiver state).
    """
    slot = _week1_slot(con, team_id, drop_pid)
    if slot is None:
        return
    con.execute(
        "DELETE FROM roster_slots WHERE team_id = ? AND player_id = ?"
        " AND week_no = 1",
        (team_id, drop_pid),
    )
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
    """
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
        eng._rosters = {int(k): list(v) for k, v in eng._rosters.items()}
        eng.remaining = {int(k): v for k, v in eng.remaining.items()}
        bids = {}
        for key, inner in eng._bids.items():
            tid_s, week_s = key.rsplit("|", 1)
            bids[(int(tid_s), int(week_s))] = {
                int(pid): dict(b) for pid, b in inner.items()
            }
        eng._bids = bids
        eng._frozen = {int(k): v for k, v in eng._frozen.items()}
    _registry[("waiver", league_id)] = eng
    return eng


def submit_waiver_claim(con: sqlite3.Connection, league_id: int, team_id: int,
                        week_no: int, add_player_id: int,
                        drop_player_id: int | None, bid: int) -> dict:
    get_league(con, league_id)
    team_ids = {t["id"] for t in _teams(con, league_id)}
    if team_id not in team_ids:
        raise HTTPException(404, f"team {team_id} not found")
    eng = _revive_waiver(con, league_id)
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
    eng = _revive_waiver(con, league_id)
    try:
        results = eng.run_week(week_no, standings_best_first(con, league_id))
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
                # vacated week-1 slot.
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
        "review_deadline": (
            time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(trade["review_until"]))
            if trade.get("review_until") else None
        ),
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
            " receives, status, review_deadline, engine_id)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (league_id, trade["parties"][0], trade["parties"][1],
             json.dumps(list(trade["gives"].get(trade["parties"][0], []))),
             json.dumps(list(trade["gives"].get(trade["parties"][1], []))),
             _TRADE_STATUS_MAP[trade["status"]],
             (time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(trade["review_until"]))
              if trade.get("review_until") else None),
             trade["id"]),
        )
        db_id = cur.lastrowid
    out = _trade_to_out(trade, db_id)
    con.execute(
        "UPDATE trades SET status = ?, review_deadline = ? WHERE id = ?",
        (out["status"], out["review_deadline"], db_id),
    )
    return db_id


def _settle_trades(con: sqlite3.Connection, league_id: int) -> None:
    """Expire stale proposals; execute review-closed trades (roster swap)."""
    eng = _revive_trade(con, league_id)
    now = time.time()
    changed = eng.sweep(now=now)
    for tid, trade in list(eng._trades.items()):
        if trade["status"] == TradeEngine.STATUS_UNDER_REVIEW \
                and now >= (trade["review_until"] or float("inf")):
            result = eng.execute(tid, now=now)
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
    eng = _revive_trade(con, league_id)
    try:
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
    eng = _revive_trade(con, league_id)
    try:
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
    return [
        {
            "id": r["id"], "league_id": r["league_id"],
            "from_team_id": r["from_team_id"], "to_team_id": r["to_team_id"],
            "gives": json.loads(r["gives"] or "[]"),
            "receives": json.loads(r["receives"] or "[]"),
            "status": r["status"], "review_deadline": r["review_deadline"],
        }
        for r in con.execute(sql, params)
    ]
