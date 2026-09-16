"""IPL Fantasy — P2-L3 waiver engine.

Sandbox-first, stdlib-only weekly FAAB waiver system (D6: $100 season
budget, blind bids, Wednesday run, 2-day freeze for drops, reverse-
standings tiebreak).

Design notes:
- Every claim MUST name a drop (rosters are fixed 15-man; there are no
  open slots). The dropped player is frozen for 2 days and cannot be
  claimed until the freeze lifts.
- Bids are blind by construction: the engine stores them but exposes no
  read API for other teams' bids; the web layer is responsible for
  hiding them (to_dict includes bids for persistence only).
- Budget enforcement: a single bid may not exceed the team's remaining
  budget at submit time. Within a run, wins are awarded in descending
  winning-bid order; if a team's remaining budget can no longer cover
  its winning bid (it won earlier claims), the claim is forfeited to the
  next-highest affordable bidder.
- Tiebreak: reverse standings (worst team wins). `standings` is a list
  of team_ids ordered best-first (the P2-L5 output); internally reversed.
- Weeks are caller-supplied ints; the "Wednesday ~3am PT" cadence is the
  league schedule's job — the engine just resolves a submitted bid set.

JSON contract: to_dict() emits budgets, rosters, bids, freezes, and run
history for persistence; the web team owns transport.
"""

from __future__ import annotations

import time


FREEZE_SECS = 2 * 86400          # 2-day freeze for drops (D6)
SEASON_BUDGET = 100             # $100 FAAB (D6)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class WaiverError(Exception):
    """Base class for all waiver-engine errors."""


class UnknownTeam(WaiverError):
    """team_id is not in the league."""


class UnknownPlayer(WaiverError):
    """player_id is not in the waiver/free-agent pool."""


class NotOnRoster(WaiverError):
    """drop_player_id is not on the bidding team's roster."""


class FrozenPlayer(WaiverError):
    """player_id is inside its 2-day post-drop freeze."""


class OverBudget(WaiverError):
    """Bid exceeds the team's remaining FAAB budget."""


class BidClosed(WaiverError):
    """Bid submitted for a week whose run already executed."""


class WeekAlreadyRun(WaiverError):
    """run_week called twice for the same week."""


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class WaiverEngine:
    """Weekly FAAB waiver wire.

    teams:  mapping team_id -> list of rostered player_ids (15-man).
    pool:   collection of claimable free-agent player_ids.
    budget: season FAAB budget per team (D6: 100).
    clock:  callable returning epoch seconds (default time.time).
    """

    def __init__(self, teams: dict, pool, budget: int = SEASON_BUDGET,
                 clock=None):
        self._rosters = {tid: list(r) for tid, r in teams.items()}
        self.pool = set(pool)
        self.budget = budget
        self.remaining = {tid: budget for tid in teams}
        self.clock = clock or time.time
        # (team_id, week) -> {player_id: {"amount": int, "drop": player_id|None,
        #                                 "ts": float}}
        self._bids: dict = {}
        # player_id -> freeze expiry (epoch secs)
        self._frozen: dict = {}
        # week -> list of run result dicts
        self._runs: dict = {}

    # -- guards ------------------------------------------------------------
    def _require_team(self, team_id):
        if team_id not in self._rosters:
            raise UnknownTeam(f"unknown team_id {team_id!r}")

    def _frozen_until(self, player_id, now) -> float | None:
        exp = self._frozen.get(player_id)
        if exp is not None and now < exp:
            return exp
        return None

    # -- bidding -----------------------------------------------------------
    def submit_bid(self, team_id, week, player_id, amount: int,
                   drop_player_id=None, now=None) -> dict:
        """Submit (or overwrite) a blind bid for a week.

        drop_player_id is required: 15-man rosters have no open slots.
        """
        self._require_team(team_id)
        now = self.clock() if now is None else now
        if week in self._runs:
            raise BidClosed(f"week {week} waivers already ran")
        if player_id not in self.pool:
            raise UnknownPlayer(f"player {player_id!r} is not claimable")
        frozen = self._frozen_until(player_id, now)
        if frozen is not None:
            raise FrozenPlayer(
                f"player {player_id!r} frozen until {frozen}")
        if drop_player_id is None:
            raise WaiverError("a drop_player_id is required (rosters are "
                              "fixed 15-man)")
        if drop_player_id not in self._rosters[team_id]:
            raise NotOnRoster(
                f"player {drop_player_id!r} is not on team {team_id!r}'s roster")
        if amount < 0:
            raise WaiverError(f"bid amount must be >= 0 (got {amount})")
        if amount > self.remaining[team_id]:
            raise OverBudget(
                f"bid ${amount} exceeds team {team_id!r}'s remaining "
                f"${self.remaining[team_id]}")
        bid = {"amount": amount, "drop": drop_player_id, "ts": now}
        self._bids.setdefault((team_id, week), {})[player_id] = bid
        return {"team_id": team_id, "week": week, "player_id": player_id,
                **bid}

    def cancel_bid(self, team_id, week, player_id):
        """Withdraw a bid before the week's run."""
        self._require_team(team_id)
        if week in self._runs:
            raise BidClosed(f"week {week} waivers already ran")
        self._bids.get((team_id, week), {}).pop(player_id, None)

    # -- run ---------------------------------------------------------------
    def run_week(self, week, standings_best_first: list, now=None) -> list:
        """Resolve all bids for a week (the Wednesday run).

        standings_best_first: team_ids ordered best -> worst; ties are
        broken by reverse order (worst team wins).
        Returns a list of result dicts, one per claimed player:
        {"player_id", "winner", "amount", "drop", "forfeited_by": [...]}.
        """
        if week in self._runs:
            raise WeekAlreadyRun(f"week {week} waivers already ran")
        now = self.clock() if now is None else now
        rank = {tid: i for i, tid in
                enumerate(reversed(standings_best_first))}  # worst team: 0
        unknown = [tid for tid in self._bids if tid[0] not in rank and tid[1] == week]
        if unknown:
            raise WaiverError(f"standings missing teams: {sorted({t for t, _ in unknown})}")

        # Collect (player -> [(team, amount, drop)]), skipping frozen players
        # (a freeze may have landed after the bid was submitted).
        claims: dict = {}
        for (tid, wk), bids in self._bids.items():
            if wk != week:
                continue
            for pid, bid in bids.items():
                if self._frozen_until(pid, now) is not None:
                    continue
                claims.setdefault(pid, []).append(
                    (tid, bid["amount"], bid["drop"]))

        # Process players in descending top-bid order for determinism.
        results = []
        for pid in sorted(claims, key=lambda p: -max(b[1] for b in claims[p])):
            bidders = sorted(claims[pid],
                             key=lambda b: (-b[1], rank.get(b[0], 10 ** 9)))
            winner = None
            forfeited = []
            for tid, amount, drop in bidders:
                if amount <= self.remaining[tid]:
                    winner = (tid, amount, drop)
                    break
                forfeited.append(tid)
            if winner is None:
                results.append({"player_id": pid, "winner": None,
                                "amount": None, "drop": None,
                                "forfeited_by": forfeited})
                continue
            tid, amount, drop = winner
            # Settle: pay, swap roster, freeze the drop.
            self.remaining[tid] -= amount
            self._rosters[tid].remove(drop)
            self._rosters[tid].append(pid)
            self.pool.discard(pid)
            self.pool.add(drop)
            self._frozen[drop] = now + FREEZE_SECS
            results.append({"player_id": pid, "winner": tid, "amount": amount,
                            "drop": drop, "forfeited_by": forfeited})
        self._runs[week] = results
        return [dict(r) for r in results]

    # -- reads -------------------------------------------------------------
    def get_bids(self, team_id, week) -> dict:
        """A team's own bids for a week (blind: only your own are readable)."""
        self._require_team(team_id)
        return {pid: dict(b)
                for pid, b in self._bids.get((team_id, week), {}).items()}

    def get_roster(self, team_id) -> list:
        self._require_team(team_id)
        return list(self._rosters[team_id])

    def get_budget(self, team_id) -> int:
        self._require_team(team_id)
        return self.remaining[team_id]

    def is_frozen(self, player_id, now=None) -> bool:
        now = self.clock() if now is None else now
        return self._frozen_until(player_id, now) is not None

    def get_run(self, week):
        return [dict(r) for r in self._runs[week]] if week in self._runs else None

    # -- JSON contract -----------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "budget": self.budget,
            "rosters": {tid: list(r) for tid, r in self._rosters.items()},
            "pool": sorted(self.pool),
            "remaining": dict(self.remaining),
            "bids": {f"{tid}|{week}": {pid: dict(b) for pid, b in bids.items()}
                     for (tid, week), bids in self._bids.items()},
            "frozen": dict(self._frozen),
            "runs": {w: [dict(r) for r in res]
                     for w, res in self._runs.items()},
        }

    @classmethod
    def from_dict(cls, state: dict, clock=None) -> "WaiverEngine":
        eng = cls(state["rosters"], state["pool"],
                  budget=state["budget"], clock=clock)
        eng.remaining = dict(state["remaining"])
        for key, bids in state["bids"].items():
            tid, week_s = key.rsplit("|", 1)
            eng._bids[(tid, int(week_s))] = {pid: dict(b)
                                            for pid, b in bids.items()}
        eng._frozen = dict(state["frozen"])
        eng._runs = {int(w): [dict(r) for r in res]
                     for w, res in state["runs"].items()}
        return eng
