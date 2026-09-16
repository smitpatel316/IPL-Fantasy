"""IPL Fantasy — P2-L1 snake draft engine.

Sandbox-first, stdlib-only, deterministic draft state machine for the
IPL fantasy league app (D2 snake draft, D7 15-man rosters: 11 starters +
3 bench + 1 IL, D8 overseas cap). Smit ruled 2026-09-15 (P2-L8): 11
starters via a 2nd UTIL slot; the draft fills only the 14 fillable slots
(14 rounds) — the IL slot is NEVER filled during the draft
(no direct-to-IL picks); it opens post-draft for injured players
(roster service owns that rule).

D8 is enforced in two places, split by concern:
- WEEKLY LINEUP LOCK (roster service, P2-L2): at most 4 overseas players
  among the 11 starters.
- DRAFT TIME (this engine): D8 *feasibility*, role-aware and exact. Any
  pick (domestic or overseas) is illegal when it would make a D8-legal
  11 unreachable (UnfieldableRoster): with R picks left after this one,
  the team must still be able to complete to a roster admitting a legal
  11 (d8_reachable). A flat "7 domestic" headcount is NOT the rule: a
  7-domestic roster can still be unfieldable (overseas concentrated in
  AR/BOWL with no domestic cover — the seed-16/40 sandbox failure), and
  role cover, not headcount, is what the guard checks. Teams may carry
  up to 7 overseas players on the roster (only 4 may start); the
  guardrail binds only when the roster would otherwise be bricked. The
  pool is assumed to contain domestic players of every role (a
  degenerate pool raises PoolExhausted).

The engine is deliberately keyed on opaque player_id strings: it bakes
in no player names. Role/overseas metadata is supplied as a plain
``roles`` dict (``player_id -> {"role": "WK|BAT|AR|BOWL", "is_overseas": bool}``),
so it works directly against phase1's player_roles registry after a
player_name -> player_id join. Players with missing ``is_overseas``
metadata are treated as domestic for the feasibility check — the engine
never invents overseas-ness (the roster service is fail-closed on
missing metadata at lineup lock).

Determinism: the draft order is a seeded shuffle of the teams
(``random.Random(seed)``). The pick clock is driven by an injectable
``clock`` callable (defaults to ``time.time``) so expiry is testable
without sleeping.

JSON contract: ``to_dict()`` emits the full draft state the draft-room
WebSocket will broadcast; the web team owns the transport.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class DraftError(Exception):
    """Base class for all draft-engine errors."""


class NotYourTurn(DraftError):
    """A team tried to pick (or be auto-picked) out of turn."""


class PlayerUnavailable(DraftError):
    """Player is not in the draft pool or has already been drafted."""


class RosterFull(DraftError):
    """The team already has 14 players (D7 fillable-roster cap)."""


class DoNotDraft(DraftError):
    """Player is on the team's Do-Not-Draft list."""


class PoolExhausted(DraftError):
    """No eligible players remain for this team to draft."""


class UnfieldableRoster(DraftError):
    """A pick would make a D8-legal 11 unreachable.

    Reachability is role-aware and exact (see d8_reachable()): with the
    team's remaining picks, it must still be possible to complete to a
    14-man roster admitting a D8-legal 11 (role bodies + at most 4
    forced overseas starters). Applies to domestic picks too — a
    domestic pick in the wrong role can strand the roster just as well.
    A flat domestic headcount is NOT the rule: 7 domestic players can
    still be unfieldable when role cover is missing.
    """


class DraftNotLive(DraftError):
    """Operation requires status == 'live' (or the draft is already complete)."""


class ClockNotExpired(DraftError):
    """expire_pick() was called before the pick deadline."""


# ---------------------------------------------------------------------------
# Roster slot model (D7, as ruled by Smit 2026-09-15 — P2-L8).
#
# 15-man rosters = 11 starters (WK1 BAT3 AR2 BOWL3 UTIL2) + 3 bench + 1 IL.
# The draft fills only the 14 fillable slots: 11 starters, then 3 bench.
# The IL slot is NEVER filled during the draft — there are no
# direct-to-IL picks. Injured players may still be drafted, but they
# occupy a normal roster slot (role slot / UTIL / bench). Post-draft,
# a player who has missed or is expected to miss a game is IL-eligible
# (single tier, no IL+) — the roster service (P2-L2) owns that rule.
ROSTER_SLOTS = ("WK", "BAT", "AR", "BOWL", "UTIL", "BN", "IL")

STARTER_COUNTS = {"WK": 1, "BAT": 3, "AR": 2, "BOWL": 3, "UTIL": 2}
BENCH_SIZE = 3
# NOTE: IL exists in ROSTER_SLOTS only for shape consistency with the
# roster service; the draft never assigns to it (Smit's P2-L8 ruling).

# UTIL accepts BAT/AR/BOWL — never WK (D7).
UTIL_ELIGIBLE_ROLES = ("BAT", "AR", "BOWL")

# Starter slots a player of a given role may occupy, in assignment order
# (role slot first, UTIL as the overflow).
ELIGIBLE_SLOTS = {
    "WK": ("WK",),
    "BAT": ("BAT", "UTIL"),
    "AR": ("AR", "UTIL"),
    "BOWL": ("BOWL", "UTIL"),
}

DRAFT_ROSTER_CAP = 14  # 11 starters + 3 bench; IL never draft-filled

# D8: at most 4 overseas players among the 11 fantasy starters.
MAX_OVERSEAS_STARTERS = 4
# Rigid starter slots (everything except the flexible UTIL): a D8-legal
# 11 must cover WK1/BAT3/AR2/BOWL3 with role-eligible players; the 2
# UTIL slots accept any BAT/AR/BOWL.
RIGID_SLOT_NEEDS = {s: c for s, c in STARTER_COUNTS.items() if s != "UTIL"}
NUM_UTIL_SLOTS = STARTER_COUNTS["UTIL"]
# Flex-role bodies needed on the roster: the 8 rigid BAT/AR/BOWL slots
# plus the 2 UTIL slots.
FLEX_BODIES_NEEDED = (
    sum(RIGID_SLOT_NEEDS[r] for r in UTIL_ELIGIBLE_ROLES) + NUM_UTIL_SLOTS
)  # 8 + 2 = 10


def _d8_end_state_ok(domestic_by_role: dict, overseas_by_role: dict) -> bool:
    """Exact end-state check: does this 14-man roster admit a D8-legal 11?

    Necessary and sufficient:
    - bodies: every rigid slot's role has enough players (domestic +
      overseas), and there are >= 10 BAT/AR/BOWL bodies for the 8 rigid
      flex slots + 2 UTIL;
    - cover: the forced overseas starters (rigid slots not coverable by
      a domestic player, plus UTIL slots not coverable by a spare
      domestic BAT/AR/BOWL) number at most MAX_OVERSEAS_STARTERS.
    Sufficiency is constructive: fill rigid slots with domestic players
    first (overseas only for the forced deficits — realizable because
    bodies exist), then UTIL with spare domestic flex players (overseas
    for the rest — realizable because flex bodies >= 10).
    """
    need = RIGID_SLOT_NEEDS
    d = domestic_by_role
    o = overseas_by_role
    for r in need:
        if d.get(r, 0) + o.get(r, 0) < need[r]:
            return False
    flex_bodies = sum(d.get(r, 0) + o.get(r, 0)
                      for r in UTIL_ELIGIBLE_ROLES)
    if flex_bodies < FLEX_BODIES_NEEDED:
        return False
    rigid_forced = sum(max(0, need[r] - d.get(r, 0)) for r in need)
    flex_domestic = sum(max(0, d.get(r, 0) - need[r])
                        for r in UTIL_ELIGIBLE_ROLES)
    util_forced = max(0, NUM_UTIL_SLOTS - flex_domestic)
    return rigid_forced + util_forced <= MAX_OVERSEAS_STARTERS


def d8_reachable(domestic_by_role: dict, overseas_by_role: dict,
                 picks_remaining: int) -> bool:
    """Can `picks_remaining` future picks complete the roster to one
    with a D8-legal 11? Exact under the ideal-pool assumption.

    The pool is assumed to contain domestic players of every role, so
    future picks are modeled as domestic players of freely chosen roles.
    Restricting to domestic is without loss: replacing any overseas
    future pick with a domestic one of the same role keeps all bodies
    and can only improve cover. At picks_remaining=0 this reduces to
    _d8_end_state_ok, which is necessary and sufficient.

    The draft's guardrail blocks any pick (domestic or overseas) that
    would make this return False — a flat "7 domestic" headcount is NOT
    the rule (a 7-domestic roster can be unfieldable when overseas
    players concentrate in AR/BOWL with no domestic cover).
    """
    roles = ("WK", "BAT", "AR", "BOWL")
    d = domestic_by_role
    o = overseas_by_role

    # Enumerate allocations of `picks_remaining` indistinguishable
    # domestic picks across the 4 roles (stars and bars).
    def allocations(remaining, idx):
        if idx == len(roles) - 1:
            yield (remaining,)
            return
        for v in range(remaining + 1):
            for rest in allocations(remaining - v, idx + 1):
                yield (v,) + rest

    for alloc in allocations(picks_remaining, 0):
        final_domestic = {r: d.get(r, 0) + alloc[i]
                          for i, r in enumerate(roles)}
        if _d8_end_state_ok(final_domestic, o):
            return True
    return False


def _new_roster() -> dict:
    return {slot: [] for slot in ROSTER_SLOTS}


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DraftConfig:
    """Draft setup.

    teams: sequence of (team_id, team_name). Draft order is a seeded
    random shuffle of these teams; pass an explicit draft_order to fix it.
    """
    teams: tuple                    # ((team_id, team_name), ...)
    rounds: int = 14                # D7 (Smit ruling 2026-09-15): 14 rounds,
                                    # one pick per fillable slot (IL not draft-filled)
    pick_clock_secs: int = 90
    seed: int | None = 42
    draft_order: tuple | None = None  # explicit order overrides the shuffle
    enforce_d8_feasibility: bool = True
    # D8 guardrail (UnfieldableRoster / D8-legal filtering in auto_pick).
    # The product always leaves this ON. It exists so unit tests for
    # unrelated features (clock, DND, JSON) can use short drafts where a
    # D8-legal 11 is unreachable by construction; short drafts are not a
    # product configuration (Smit locked 14 rounds).

    @property
    def team_ids(self) -> tuple:
        return tuple(t[0] for t in self.teams)

    @property
    def num_teams(self) -> int:
        return len(self.teams)

    @property
    def total_picks(self) -> int:
        return self.num_teams * self.rounds

    def resolved_order(self) -> tuple:
        if self.draft_order is not None:
            return tuple(self.draft_order)
        rng = random.Random(self.seed)
        order = list(self.team_ids)
        rng.shuffle(order)
        return tuple(order)


# ---------------------------------------------------------------------------
# Draft state machine
# ---------------------------------------------------------------------------

class Draft:
    """Snake draft state machine.

    status: 'scheduled' -> 'live' -> 'complete'.
    """

    STATUS_SCHEDULED = "scheduled"
    STATUS_LIVE = "live"
    STATUS_COMPLETE = "complete"

    def __init__(
        self,
        config: DraftConfig,
        pool: list,
        roles: dict | None = None,
        ranks: dict | None = None,
        dnd: dict | None = None,
        clock=None,
    ):
        """
        pool:  draft universe as a ranked list of player_ids, best first.
               This ranking is the league ADP proxy — the auto-pick
               fallback when a team has no custom pre-draft ranks.
        roles: player_id -> {"role": "WK|BAT|AR|BOWL", "is_overseas": bool}
        ranks: team_id -> ranked list of player_ids (custom pre-draft ranks)
        dnd:   team_id -> collection of player_ids to never auto-pick
        clock: callable returning seconds (epoch); default time.time.
        """
        self.config = config
        self.pool = list(pool)
        self.roles = dict(roles or {})
        self.ranks = {t: list(r) for t, r in (ranks or {}).items()}
        self.dnd = {t: set(s) for t, s in (dnd or {}).items()}
        self.clock = clock or time.time

        self.draft_order = config.resolved_order()
        self.status = self.STATUS_SCHEDULED
        self.current_pick_no = 1
        self.pick_deadline = None
        self.picks: list[dict] = []
        self.rosters = {tid: _new_roster() for tid in config.team_ids}
        self.event_log: list[dict] = []
        self._event("draft.created", {
            "draft_order": list(self.draft_order),
            "rounds": config.rounds,
            "pick_clock_secs": config.pick_clock_secs,
            "pool_size": len(self.pool),
        })

    # -- event log ---------------------------------------------------------
    def _event(self, event_type: str, payload: dict):
        self.event_log.append({
            "seq": len(self.event_log) + 1,
            "ts": self.clock(),
            "type": event_type,
            "payload": payload,
        })

    # -- snake mapping -----------------------------------------------------
    def pick_no_to_round_team(self, pick_no: int) -> tuple[int, str]:
        """pick_no (1-based) -> (round_no, team_id)."""
        n = self.config.num_teams
        if not 1 <= pick_no <= self.config.total_picks:
            raise DraftError(f"pick_no {pick_no} out of range")
        round_no = (pick_no - 1) // n + 1
        idx = (pick_no - 1) % n
        if round_no % 2 == 1:      # odd rounds: draft order
            team_id = self.draft_order[idx]
        else:                      # even rounds: reversed
            team_id = self.draft_order[n - 1 - idx]
        return round_no, team_id

    @property
    def on_clock_team_id(self):
        if self.status != self.STATUS_LIVE:
            return None
        return self.pick_no_to_round_team(self.current_pick_no)[1]

    @property
    def picks_made(self) -> int:
        return len(self.picks)

    @property
    def drafted(self) -> set:
        return {p["player_id"] for p in self.picks}

    # -- lifecycle ---------------------------------------------------------
    def start(self):
        if self.status != self.STATUS_SCHEDULED:
            raise DraftNotLive("draft already started")
        self.status = self.STATUS_LIVE
        self.current_pick_no = 1
        self._reset_deadline()
        self._event("draft.started", {
            "current_pick_no": 1,
            "on_clock_team_id": self.on_clock_team_id,
            "pick_deadline": self.pick_deadline,
        })
        return self

    def _reset_deadline(self):
        self.pick_deadline = self.clock() + self.config.pick_clock_secs

    def _require_live(self):
        if self.status != self.STATUS_LIVE:
            raise DraftNotLive(f"draft is {self.status}, not live")

    def _require_team(self, team_id):
        if team_id not in self.rosters:
            raise DraftError(f"unknown team_id {team_id!r}")

    # -- eligibility -------------------------------------------------------
    def _ranked_candidates(self, team_id) -> list:
        """Available players for a team, best-ranked first.

        Uses the team's pre-draft ranks when present, falling back to the
        league ADP proxy (the pool order). Skips drafted players and the
        team's Do-Not-Draft list.
        """
        self._require_team(team_id)
        dnd = self.dnd.get(team_id, set())
        drafted = self.drafted
        team_ranks = self.ranks.get(team_id)
        pool_set = set(self.pool)
        if team_ranks:
            order = [p for p in team_ranks
                     if p in pool_set and p not in drafted and p not in dnd]
            # Any pool players missing from custom ranks fall back to pool order.
            seen = set(order)
            order.extend(p for p in self.pool
                         if p not in drafted and p not in dnd and p not in seen)
            return order
        return [p for p in self.pool if p not in drafted and p not in dnd]

    def _open_starter_slots(self, team_id) -> set:
        roster = self.rosters[team_id]
        return {
            slot for slot, cap in STARTER_COUNTS.items()
            if len(roster[slot]) < cap
        }

    # -- D8 feasibility ----------------------------------------------------
    def _is_overseas(self, player_id) -> bool:
        # Missing metadata -> treated as domestic: the engine never
        # invents overseas-ness.
        return bool((self.roles.get(player_id) or {}).get("is_overseas", False))

    def _roster_composition(self, team_id) -> tuple:
        """(domestic_by_role, overseas_by_role) for the team's roster."""
        d, o = {}, {}
        for slot in ROSTER_SLOTS:
            for pid in self.rosters[team_id][slot]:
                role = (self.roles.get(pid) or {}).get("role")
                target = o if self._is_overseas(pid) else d
                target[role] = target.get(role, 0) + 1
        return d, o

    def _picks_remaining_after(self, team_id) -> int:
        """Picks this team still has AFTER the current pick is made."""
        made = sum(len(v) for v in self.rosters[team_id].values())
        return self.config.rounds - made - 1

    def _pick_keeps_d8_reachable(self, team_id, player_id) -> bool:
        """Would drafting player_id now keep a D8-legal 11 reachable?

        Applies to domestic and overseas picks alike: a domestic pick in
        the wrong role can also strand the roster (e.g. drafting a 5th
        WK when AR/BOWL cover is missing and no picks remain to repair
        it). Exact via d8_reachable().
        """
        d, o = self._roster_composition(team_id)
        role = (self.roles.get(player_id) or {}).get("role")
        if self._is_overseas(player_id):
            o = dict(o)
            o[role] = o.get(role, 0) + 1
        else:
            d = dict(d)
            d[role] = d.get(role, 0) + 1
        return d8_reachable(d, o, self._picks_remaining_after(team_id))

    def _assign_slot(self, team_id, player_id) -> str:
        """Pick the roster slot a player fills (role slot > UTIL > BN).

        Players with unknown/missing role metadata go straight to the
        bench — the engine never invents a role. The IL slot is NEVER
        assigned during the draft (Smit's P2-L8 ruling): injured players
        are drafted into normal slots; the roster service moves them to
        IL post-draft.

        Raises RosterFull when no legal slot is open (e.g. every slot the
        player's role may occupy is full and the bench is full) — the
        manager must draft a player whose role fits an open starter
        slot instead.
        """
        role = (self.roles.get(player_id) or {}).get("role")
        roster = self.rosters[team_id]
        for slot in ELIGIBLE_SLOTS.get(role, ()):
            if len(roster[slot]) < STARTER_COUNTS[slot]:
                roster[slot].append(player_id)
                return slot
        if len(roster["BN"]) < BENCH_SIZE:
            roster["BN"].append(player_id)
            return "BN"
        raise RosterFull(
            f"team {team_id!r} has no open slot for role {role!r} "
            f"(starters/UTIL/bench full; IL is never draft-filled)")

    # -- picks -------------------------------------------------------------
    def manual_pick(self, team_id, player_id) -> dict:
        """Record a manual pick with full validation."""
        self._require_live()
        self._require_team(team_id)
        if team_id != self.on_clock_team_id:
            raise NotYourTurn(
                f"team {team_id!r} is not on the clock "
                f"(on clock: {self.on_clock_team_id!r})"
            )
        if player_id not in self.pool:
            raise PlayerUnavailable(f"player {player_id!r} is not in the draft pool")
        if player_id in self.drafted:
            raise PlayerUnavailable(f"player {player_id!r} is already drafted")
        if player_id in self.dnd.get(team_id, set()):
            raise DoNotDraft(f"player {player_id!r} is on team {team_id!r}'s DND list")
        if sum(len(v) for v in self.rosters[team_id].values()) >= DRAFT_ROSTER_CAP:
            raise RosterFull(f"team {team_id!r} roster is full (14)")
        if (self.config.enforce_d8_feasibility
                and not self._pick_keeps_d8_reachable(team_id, player_id)):
            raise UnfieldableRoster(
                f"team {team_id!r} cannot draft player {player_id!r}: "
                f"no D8-legal 11 would remain reachable with "
                f"{self._picks_remaining_after(team_id)} picks left "
                f"(max {MAX_OVERSEAS_STARTERS} overseas starters)")
        return self._record_pick(team_id, player_id, is_auto=False)

    def auto_pick(self, team_id=None) -> dict:
        """Pick the best available player for a team (records is_auto=True).

        Starters-before-bench fill: if any starter slot is open, the
        highest-ranked player whose role can fill one is taken; otherwise
        the highest-ranked available player goes to the bench.
        """
        self._require_live()
        if team_id is None:
            team_id = self.on_clock_team_id
        self._require_team(team_id)
        if team_id != self.on_clock_team_id:
            raise NotYourTurn(
                f"team {team_id!r} is not on the clock "
                f"(on clock: {self.on_clock_team_id!r})"
            )
        candidates = self._ranked_candidates(team_id)
        if not candidates:
            raise PoolExhausted(f"no eligible players left for team {team_id!r}")
        # D8 feasibility: a pick that would leave the roster unable to
        # field a legal 11 is not a legal pick — skip it for the best
        # legal candidate instead of bricking the roster. Reachability
        # depends only on (role, is_overseas), so check each distinct
        # kind once. (Skipped entirely when enforce_d8_feasibility is
        # False — short test drafts where a legal 11 is unreachable by
        # construction.)
        legal = list(candidates)
        if self.config.enforce_d8_feasibility:
            reachable_kind = {}
            legal = []
            for p in candidates:
                kind = ((self.roles.get(p) or {}).get("role"),
                        self._is_overseas(p))
                if kind not in reachable_kind:
                    reachable_kind[kind] = self._pick_keeps_d8_reachable(
                        team_id, p)
                if reachable_kind[kind]:
                    legal.append(p)
        if not legal:
            raise PoolExhausted(
                f"no D8-legal picks remain for team {team_id!r} "
                f"(every candidate would make a D8-legal 11 unreachable)")

        open_slots = self._open_starter_slots(team_id)
        chosen = None
        for player_id in legal:
            role = (self.roles.get(player_id) or {}).get("role")
            if open_slots and any(
                s in open_slots for s in ELIGIBLE_SLOTS.get(role, ())
            ):
                chosen = player_id
                break
        if chosen is None:
            # No starter slots open (or no ranked player can fill the open
            # ones) — take the best legal available for the bench.
            chosen = legal[0]
        return self._record_pick(team_id, chosen, is_auto=True)

    def expire_pick(self) -> dict:
        """Fire when the pick clock runs out: auto-pick for the on-clock team."""
        self._require_live()
        if self.clock() < self.pick_deadline:
            raise ClockNotExpired(
                f"pick deadline not reached "
                f"({self.pick_deadline - self.clock():.1f}s remaining)"
            )
        team_id = self.on_clock_team_id
        self._event("pick.expired", {
            "pick_no": self.current_pick_no,
            "team_id": team_id,
            "deadline": self.pick_deadline,
        })
        return self.auto_pick(team_id)

    def _record_pick(self, team_id, player_id, is_auto: bool) -> dict:
        pick_no = self.current_pick_no
        round_no, _ = self.pick_no_to_round_team(pick_no)
        slot = self._assign_slot(team_id, player_id)
        pick = {
            "pick_no": pick_no,
            "round_no": round_no,
            "team_id": team_id,
            "player_id": player_id,
            "slot": slot,
            "is_auto": is_auto,
        }
        self.picks.append(pick)
        self._event("draft.pick", pick)
        self.current_pick_no += 1
        if self.current_pick_no > self.config.total_picks:
            self.status = self.STATUS_COMPLETE
            self.pick_deadline = None
            self._event("draft.completed", {"total_picks": len(self.picks)})
        else:
            self._reset_deadline()
        return pick

    # -- DND / ranks -------------------------------------------------------
    def add_to_dnd(self, team_id, player_id):
        self._require_team(team_id)
        self.dnd.setdefault(team_id, set()).add(player_id)

    def set_ranks(self, team_id, ranked_player_ids: list):
        self._require_team(team_id)
        self.ranks[team_id] = list(ranked_player_ids)

    # -- JSON contract -----------------------------------------------------
    def to_dict(self) -> dict:
        """Full draft state, JSON-serializable (the draft-room WebSocket payload)."""
        return {
            "draft": {
                "status": self.status,
                "rounds": self.config.rounds,
                "teams": [
                    {"id": tid, "name": name}
                    for tid, name in self.config.teams
                ],
                "draft_order": list(self.draft_order),
                "seed": self.config.seed,
                "pick_clock_secs": self.config.pick_clock_secs,
            },
            "current_pick_no": self.current_pick_no,
            "total_picks": self.config.total_picks,
            "on_clock_team_id": self.on_clock_team_id,
            "pick_deadline": self.pick_deadline,
            "picks": [dict(p) for p in self.picks],
            "rosters": {
                tid: {slot: list(pids) for slot, pids in roster.items()}
                for tid, roster in self.rosters.items()
            },
            "dnd": {tid: sorted(s) for tid, s in self.dnd.items()},
            "event_log": [dict(e) for e in self.event_log],
        }

    @classmethod
    def from_dict(cls, state: dict, pool: list, roles: dict | None = None,
                  clock=None) -> "Draft":
        """Rebuild a Draft from a to_dict() snapshot (pool/roles re-supplied)."""
        d = state["draft"]
        config = DraftConfig(
            teams=tuple((t["id"], t["name"]) for t in d["teams"]),
            rounds=d["rounds"],
            pick_clock_secs=d["pick_clock_secs"],
            seed=d.get("seed"),
            draft_order=tuple(d["draft_order"]),
        )
        draft = cls.__new__(cls)
        draft.config = config
        draft.pool = list(pool)
        draft.roles = dict(roles or {})
        draft.ranks = {}            # custom ranks are advisory only; not restored
        draft.dnd = {t: set(s) for t, s in state.get("dnd", {}).items()}
        draft.clock = clock or time.time
        draft.draft_order = tuple(d["draft_order"])
        draft.status = d["status"]
        draft.current_pick_no = state["current_pick_no"]
        draft.pick_deadline = state["pick_deadline"]
        draft.picks = [dict(p) for p in state["picks"]]
        draft.rosters = {
            tid: {slot: list(pids) for slot, pids in roster.items()}
            for tid, roster in state["rosters"].items()
        }
        draft.event_log = [dict(e) for e in state["event_log"]]
        return draft
