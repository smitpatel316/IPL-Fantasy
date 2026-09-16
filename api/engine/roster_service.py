"""IPL Fantasy — P2-L2 roster/lineup service.

Sandbox-first, stdlib-only weekly lineup manager for the IPL fantasy
league app (D5 weekly lock, D7 15-man rosters, D8 max 4
overseas starters).

Slot model (D7, as ruled by Smit 2026-09-15 — P2-L8): 15-man rosters =
11 starters (WK1 BAT3 AR2 BOWL3 UTIL2) + 3 bench + 1 IL.

IL rule (Smit 2026-09-15, single tier, no IL+):
- The IL slot is NEVER filled during the draft (no direct-to-IL picks);
  injured players may be drafted but occupy a normal roster spot.
- Post-draft, a player who has missed or is expected to miss a game is
  IL-eligible. Only IL-eligible players may occupy the IL slot, and IL
  holds at most one player. IL players never count as starters.
- Moving a player to IL frees a roster spot: the team may then add a
  replacement (``add_player``) up to the 15-man total / 14-active cap.

Design notes:
- Keyed on opaque player_id strings; role/overseas metadata comes in as
  a ``roles`` dict (``player_id -> {"role": "WK|BAT|AR|BOWL",
  "is_overseas": bool}``) in the same shape as P2-L1's draft engine, so
  it reads directly off phase1's player_roles registry.
- Players with unknown/missing role metadata are FAIL-CLOSED: the lineup
  is rejected rather than guessed (D8's overseas count cannot be
  verified without metadata).
- Lock semantics: a team may submit/re-submit any time BEFORE the
  week's lock deadline; an explicit ``lock()`` freezes the lineup early
  (Yahoo-style "locked" state); after the deadline passes, the lineup is
  frozen regardless. Lineups are keyed by (team_id, week).

JSON contract: ``to_dict()`` emits all weekly lineups; the matchup
engine (P2-L5) consumes ``get_starters(team_id, week)`` and the web
team owns transport.
"""

from __future__ import annotations

import time


# ---------------------------------------------------------------------------
# Slot model (D7, as ruled by Smit 2026-09-15 — P2-L8) — mirrors
# draft_engine.py's constants
# ---------------------------------------------------------------------------

ROSTER_SLOTS = ("WK", "BAT", "AR", "BOWL", "UTIL", "BN", "IL")
STARTER_SLOTS = ("WK", "BAT", "AR", "BOWL", "UTIL")
SLOT_CAPACITY = {"WK": 1, "BAT": 3, "AR": 2, "BOWL": 3, "UTIL": 2,
                 "BN": 3, "IL": 1}

STARTERS_TOTAL = sum(SLOT_CAPACITY[s] for s in STARTER_SLOTS)  # 11
ROSTER_SIZE = 15          # total roster cap (active + IL)
ACTIVE_ROSTER_CAP = 14    # 11 starters + 3 bench; IL sits outside this

# D8: at most 4 overseas players among the 11 starters.
MAX_OVERSEAS_STARTERS = 4

# Role -> slots the role may occupy. Unknown roles map to () and are
# rejected in _validate_roles (fail-closed); BN/IL would be a guess.
# Every role may use IL — but only IL-eligible players may actually
# occupy it (Smit's P2-L8 IL rule; enforced in _validate).
# Every role may sit on the bench (inactive) or IL (if eligible); UTIL is
# BAT/AR/BOWL only, and the WK slot takes WK only. A drafted backup
# keeper lives on BN — the draft engine benches overflow there, so the
# lineup service must accept it (integration fix found by the P2-L7
# sandbox: a 2-WK roster could never submit a legal lineup otherwise).
ROLE_TO_SLOTS = {
    "WK": ("WK", "BN", "IL"),
    "BAT": ("BAT", "UTIL", "BN", "IL"),
    "AR": ("AR", "UTIL", "BN", "IL"),
    "BOWL": ("BOWL", "UTIL", "BN", "IL"),
}


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class LineupError(Exception):
    """Base class for all lineup-service errors."""


class UnknownTeam(LineupError):
    """team_id has no registered roster."""


class UnknownPlayer(LineupError):
    """player_id is not on the team's 15-man roster."""


class RoleMetadataMissing(LineupError):
    """Role/overseas metadata is missing for a player (fail-closed)."""


class IneligibleSlot(LineupError):
    """A player was assigned to a slot their role may not occupy."""


class ILIneligible(LineupError):
    """A player who has not missed / is not expected to miss a game was
    placed on (or moved to) IL — Smit's P2-L8 IL rule, single tier."""


class SlotOverflow(LineupError):
    """A slot received more players than its capacity."""


class IncompleteLineup(LineupError):
    """Every rostered player must be placed in exactly one slot."""


class DuplicatePlayer(LineupError):
    """A player appears more than once in the assignments."""


class OverseasCapViolated(LineupError):
    """More than 4 overseas players among the 11 starters (D8)."""


class LineupLocked(LineupError):
    """Edit attempted on a frozen lineup (explicit lock or past deadline)."""


class WeekFinalized(LineupError):
    """Operation requested after the week's scoring week closed."""


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class LineupService:
    """Weekly lineup submission + validation + lock.

    teams: mapping team_id -> list of 14 or 15 rostered player_ids (the
    draft output is 14; 15 only with an IL-eligible player to fill IL).
    roles: player_id -> {"role": ..., "is_overseas": bool}.
    il_eligible: set of player_ids designated IL-eligible (missed or
    expected to miss a game — the injury feed's designation; single
    tier, no IL+). Updated via set_il_eligible().
    clock: callable returning epoch seconds (default time.time).
    """

    def __init__(self, teams: dict, roles: dict, il_eligible=None, clock=None):
        for tid, roster in teams.items():
            if (not 14 <= len(roster) <= ROSTER_SIZE
                    or len(set(roster)) != len(roster)):
                raise LineupError(
                    f"team {tid!r} roster must be 14 or 15 unique "
                    f"player_ids (got {len(roster)} / {len(set(roster))} unique)")
        self._rosters = {tid: list(roster) for tid, roster in teams.items()}
        self.roles = dict(roles)
        self.il_eligible = set(il_eligible or ())
        self.clock = clock or time.time
        # Roster-level IL occupancy: team_id -> player_id | None.
        # Set via move_to_il(); the weekly assignment must then place
        # that player in the IL slot.
        self._il = {tid: None for tid in self._rosters}
        # (team_id, week) -> {"assignments": {pid: slot},
        #                     "lock_deadline": float|None,
        #                     "locked": bool, "locked_at": float|None}
        self._weeks: dict = {}

    # -- registration ------------------------------------------------------
    def _require_team(self, team_id):
        if team_id not in self._rosters:
            raise UnknownTeam(f"unknown team_id {team_id!r}")

    def _state(self, team_id, week):
        return self._weeks.get((team_id, week))

    # -- IL roster management (Smit's P2-L8 IL rule) -----------------------
    def set_il_eligible(self, player_ids) -> set:
        """Refresh the league-wide IL-eligible designation (injury feed).

        A player is IL-eligible iff they have missed or are expected to
        miss a game. Single tier, no IL+.
        """
        self.il_eligible = set(player_ids)
        return set(self.il_eligible)

    def active_count(self, team_id) -> int:
        """Rostered players not on IL (cap: ACTIVE_ROSTER_CAP = 14)."""
        self._require_team(team_id)
        return len(self._rosters[team_id]) - (1 if self._il[team_id] else 0)

    def move_to_il(self, team_id, player_id) -> dict:
        """Move an IL-eligible player to the IL slot (roster level).

        This is the operation that frees a roster spot: afterwards the
        team may ``add_player`` a replacement (up to the 15-man total /
        14-active cap). The next ``set_lineup`` must place this player
        in the IL slot. Single tier — IL holds at most one player.
        """
        self._require_team(team_id)
        if player_id not in self._rosters[team_id]:
            raise UnknownPlayer(
                f"player {player_id!r} is not on team {team_id!r}'s roster")
        if player_id not in self.il_eligible:
            raise ILIneligible(
                f"player {player_id!r} is not IL-eligible (has not missed "
                f"and is not expected to miss a game)")
        if self._il[team_id] is not None:
            raise SlotOverflow(
                f"team {team_id!r} IL slot already holds "
                f"{self._il[team_id]!r} (single tier, no IL+)")
        self._il[team_id] = player_id
        return {"team_id": team_id, "il_player": player_id,
                "active_count": self.active_count(team_id)}

    def activate_from_il(self, team_id) -> dict:
        """Return the IL player to the active roster.

        Refused when the active roster is already full (14) — the team
        must drop/waive someone first (waiver engine's job).
        """
        self._require_team(team_id)
        il_player = self._il[team_id]
        if il_player is None:
            raise LineupError(f"team {team_id!r} has no player on IL")
        if self.active_count(team_id) >= ACTIVE_ROSTER_CAP:
            raise LineupError(
                f"team {team_id!r} active roster is full (14) — drop a "
                f"player before activating {il_player!r} from IL")
        self._il[team_id] = None
        return {"team_id": team_id, "activated": il_player,
                "active_count": self.active_count(team_id)}

    def add_player(self, team_id, player_id, role_meta: dict) -> dict:
        """Add a free-agent player to the roster (post-IL-move pickup).

        Allowed only when there is a free roster spot: total < 15 AND
        active < 14. Moving an IL-eligible player to IL is what frees
        the active spot (Smit's P2-L8 IL rule).
        """
        self._require_team(team_id)
        if player_id in self._rosters[team_id]:
            raise DuplicatePlayer(
                f"player {player_id!r} is already on team {team_id!r}'s roster")
        if len(self._rosters[team_id]) >= ROSTER_SIZE:
            raise LineupError(
                f"team {team_id!r} roster is full (15)")
        if self.active_count(team_id) >= ACTIVE_ROSTER_CAP:
            raise LineupError(
                f"team {team_id!r} has no free roster spot — move an "
                f"IL-eligible player to IL first")
        role = (role_meta or {}).get("role")
        if role not in ROLE_TO_SLOTS:
            raise RoleMetadataMissing(
                f"role metadata missing/invalid for player {player_id!r} — "
                f"refusing to add without it")
        self.roles[player_id] = {"role": role,
                                 "is_overseas": bool(role_meta.get("is_overseas"))}
        self._rosters[team_id].append(player_id)
        return {"team_id": team_id, "added": player_id,
                "roster_size": len(self._rosters[team_id])}

    def get_il(self, team_id):
        """The player_id on the team's IL, or None."""
        self._require_team(team_id)
        return self._il[team_id]

    # -- validation --------------------------------------------------------
    def _validate(self, team_id, assignments: dict) -> dict:
        """Validate a full slot assignment. Returns overseas counts.

        All rostered players must be placed. IL occupancy must match the
        roster-level IL state (set via move_to_il), and only IL-eligible
        players (missed / expected to miss a game) may sit in IL.
        """
        roster = self._rosters[team_id]
        seen = set()
        slot_fill = {slot: 0 for slot in ROSTER_SLOTS}

        for pid, slot in assignments.items():
            if pid in seen:
                raise DuplicatePlayer(f"player {pid!r} assigned more than once")
            seen.add(pid)
            if pid not in roster:
                raise UnknownPlayer(
                    f"player {pid!r} is not on team {team_id!r}'s roster")
            meta = self.roles.get(pid)
            if meta is None or meta.get("role") not in ROLE_TO_SLOTS:
                raise RoleMetadataMissing(
                    f"role metadata missing for player {pid!r} — refusing "
                    f"to guess eligibility/overseas status")
            if slot not in ROSTER_SLOTS:
                raise IneligibleSlot(f"unknown slot {slot!r}")
            if slot not in ROLE_TO_SLOTS[meta["role"]]:
                raise IneligibleSlot(
                    f"role {meta['role']!r} may not occupy slot {slot!r}")
            if slot == "IL" and pid not in self.il_eligible:
                raise ILIneligible(
                    f"player {pid!r} is not IL-eligible (has not missed and "
                    f"is not expected to miss a game) — cannot occupy IL")
            slot_fill[slot] += 1
            if slot_fill[slot] > SLOT_CAPACITY[slot]:
                raise SlotOverflow(
                    f"slot {slot!r} capacity {SLOT_CAPACITY[slot]} exceeded")

        missing = set(roster) - set(assignments)
        if missing:
            raise IncompleteLineup(
                f"{len(missing)} rostered player(s) not placed: "
                f"{sorted(missing)[:5]}{'...' if len(missing) > 5 else ''}")

        il_player = self._il[team_id]
        if il_player is not None and assignments.get(il_player) != "IL":
            raise ILIneligible(
                f"player {il_player!r} is on IL (move_to_il) and must "
                f"occupy the IL slot")

        starters = [pid for pid, slot in assignments.items()
                    if slot in STARTER_SLOTS]
        if len(starters) != STARTERS_TOTAL:
            raise IncompleteLineup(
                f"expected {STARTERS_TOTAL} starters, got {len(starters)}")
        overseas = sum(1 for pid in starters
                       if self.roles[pid].get("is_overseas"))
        if overseas > MAX_OVERSEAS_STARTERS:
            raise OverseasCapViolated(
                f"{overseas} overseas starters > cap {MAX_OVERSEAS_STARTERS} (D8)")
        return {"starters": starters, "overseas_starters": overseas}

    def _check_editable(self, team_id, week, now, lock_deadline):
        """Raise LineupLocked if the week is frozen for this team."""
        st = self._state(team_id, week)
        if st is not None and st["locked"]:
            raise LineupLocked(
                f"team {team_id!r} week {week} lineup is locked "
                f"(locked_at={st['locked_at']})")
        deadline = lock_deadline
        if st is not None and st.get("lock_deadline") is not None:
            deadline = st["lock_deadline"]
        if deadline is not None and now is not None and now > deadline:
            raise LineupLocked(
                f"team {team_id!r} week {week} deadline passed "
                f"(deadline={deadline}, now={now})")

    # -- submission / lock -------------------------------------------------
    def set_lineup(self, team_id, week, assignments: dict,
                   lock_deadline=None, now=None) -> dict:
        """Submit (or re-submit pre-deadline) a team's weekly lineup.

        assignments: {player_id: slot} covering all 15 rostered players.
        lock_deadline: epoch seconds; the first non-None deadline seen for
        (team_id, week) is sticky (the league schedule owns it).
        Returns a summary: {"starters": [...], "overseas_starters": n,
        "locked": False}.
        """
        self._require_team(team_id)
        now = self.clock() if now is None else now
        self._check_editable(team_id, week, now, lock_deadline)
        summary = self._validate(team_id, assignments)
        st = self._state(team_id, week)
        sticky_deadline = lock_deadline
        if st is not None and st.get("lock_deadline") is not None:
            sticky_deadline = st["lock_deadline"]
        self._weeks[(team_id, week)] = {
            "assignments": dict(assignments),
            "lock_deadline": sticky_deadline,
            "locked": False,
            "locked_at": None,
        }
        return {**summary, "locked": False}

    def lock(self, team_id, week, lock_deadline=None, now=None) -> dict:
        """Freeze the lineup early (Yahoo-style). No edits afterwards.

        Must have a submitted lineup; must be before the deadline.
        """
        self._require_team(team_id)
        now = self.clock() if now is None else now
        st = self._state(team_id, week)
        if st is None or not st["assignments"]:
            raise LineupError(
                f"team {team_id!r} week {week}: nothing submitted to lock")
        self._check_editable(team_id, week, now, lock_deadline)
        st["locked"] = True
        st["locked_at"] = now
        return {"team_id": team_id, "week": week, "locked_at": now}

    # -- reads -------------------------------------------------------------
    def get_lineup(self, team_id, week):
        """Full slot assignment for (team_id, week), or None if unset."""
        st = self._state(team_id, week)
        return dict(st["assignments"]) if st else None

    def get_starters(self, team_id, week) -> list:
        """The 11 starters (for the matchup engine); None if unset."""
        st = self._state(team_id, week)
        if st is None:
            return None
        return [pid for pid, slot in st["assignments"].items()
                if slot in STARTER_SLOTS]

    def is_locked(self, team_id, week, now=None) -> bool:
        """True if explicitly locked or the deadline has passed."""
        st = self._state(team_id, week)
        if st is None:
            return False
        if st["locked"]:
            return True
        if now is None:
            now = self.clock()
        dl = st.get("lock_deadline")
        return dl is not None and now > dl

    def teams_missing_lineup(self, week) -> list:
        """team_ids with no submitted lineup for the week."""
        return [tid for tid in self._rosters
                if (tid, week) not in self._weeks]

    # -- JSON contract -----------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "rosters": {tid: list(r) for tid, r in self._rosters.items()},
            "il_eligible": sorted(self.il_eligible),
            "il": dict(self._il),
            "weeks": {
                f"{tid}|{week}": {
                    "assignments": dict(st["assignments"]),
                    "lock_deadline": st["lock_deadline"],
                    "locked": st["locked"],
                    "locked_at": st["locked_at"],
                }
                for (tid, week), st in self._weeks.items()
            },
        }

    @classmethod
    def from_dict(cls, state: dict, roles: dict, clock=None) -> "LineupService":
        svc = cls(state["rosters"], roles,
                  il_eligible=state.get("il_eligible"), clock=clock)
        svc._il = {tid: state.get("il", {}).get(tid)
                   for tid in svc._rosters}
        for key, st in state["weeks"].items():
            tid, week_s = key.rsplit("|", 1)
            svc._weeks[(tid, int(week_s))] = {
                "assignments": dict(st["assignments"]),
                "lock_deadline": st["lock_deadline"],
                "locked": st["locked"],
                "locked_at": st["locked_at"],
            }
        return svc
