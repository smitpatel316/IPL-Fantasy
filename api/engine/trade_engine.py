"""IPL Fantasy — P2-L4 trade engine.

Sandbox-first, stdlib-only trade system (Yahoo-style with D-league
flavor): propose/accept between two teams, pending-trade cap, 2-day
commissioner review window, one-third-of-league veto, hard deadline at
end of fantasy week 6.

Rules implemented:
- A trade is {gives: {teamA: [pids], teamB: [pids]}} — multi-player both
  sides. All offered players must be on the offering team's roster at
  proposal time.
- Roster-size invariance: both teams must end at exactly 15 players —
  i.e. both sides give the same COUNT (N-for-N). Value can differ.
- Pending cap: a team may have at most MAX_PENDING_OUT trades awaiting
  response/review at once (default 3).
- Flow: proposed -> (accepted | declined | expired | withdrawn) ->
  under_review (2-day commissioner window from acceptance) ->
  (executed | vetoed).
- Veto: any non-involved team may cast one veto vote during review;
  if vetoes >= ceil((num_teams - 2) / 3) the trade is vetoed (one-third
  of the league, excluding the two parties — Yahoo's "1/3 to veto").
- Deadline: no new proposals after end of week 6 (week > TRADE_DEADLINE_WEEK
  rejected); trades still under review when the deadline passes keep
  their 2-day window (they were proposed in time).
- Proposal expiry: unanswered proposals expire after PROPOSAL_TTL_SECS
  (default 3 days) — the offeree's silence is not consent.
- Execution swaps the rosters atomically; executed trades are immutable.

P5-W37 multi-team deals: a deal is a set of directed player legs
[{giver_id, receiver_id, player_ids}] sharing one deal_id. Legs may be
cyclic (A->B, B->C, C->A) or cross (A->B, A->C). The first leg's giver
is the proposer and counts as accepted; every other party must accept
before the deal enters its single 2-day review window. One-third veto
applies to the deal as a whole (same league-wide threshold as trades).
Any party rejecting, or the proposer withdrawing, dissolves the entire
deal into one terminal status. Guard: per-team roster-count invariance
(every team gives as many as it receives); execution is atomic with
validate-before-mutate across all legs.

Determinism: IDs are sequential ints (trades and deals keep separate
namespaces); time comes from an injectable clock. JSON contract:
to_dict()/from_dict() for persistence.
"""

from __future__ import annotations

import math
import time


ROSTER_SIZE = 15           # full roster once the IL slot is occupied
ACTIVE_ROSTER_SIZE = 14  # draft output / normal in-season rosters
_LEGAL_ROSTER_SIZES = (ACTIVE_ROSTER_SIZE, ROSTER_SIZE)
TRADE_DEADLINE_WEEK = 6          # no new proposals after week 6 ends
REVIEW_WINDOW_SECS = 2 * 86400  # 2-day commissioner review (from acceptance)
PROPOSAL_TTL_SECS = 3 * 86400   # unanswered proposals expire after 3 days
MAX_PENDING_OUT = 3              # pending-trade cap per team


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class TradeError(Exception):
    """Base class for all trade-engine errors."""


class UnknownTeam(TradeError):
    """team_id is not in the league."""


class UnknownPlayer(TradeError):
    """player_id is not on the offering team's roster."""


class UnbalancedTrade(TradeError):
    """Sides give different player counts (roster-size invariance)."""


class PendingCapExceeded(TradeError):
    """Team already has MAX_PENDING_OUT trades awaiting action."""


class TradeDeadlinePassed(TradeError):
    """Proposal attempted after the week-6 trade deadline."""


class InvalidTradeState(TradeError):
    """Operation not allowed in the trade's current state."""


class NotAParty(TradeError):
    """Only the two trading teams may accept/decline/withdraw."""


class VetoNotAllowed(TradeError):
    """Veto vote not allowed (party team, duplicate, or wrong state)."""


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class TradeEngine:
    """Proposal -> accept -> 2-day review (veto) -> execute.

    teams: mapping team_id -> list of rostered player_ids (14 active, or
    15 once the IL slot is occupied and a replacement added).
    commissioner: team_id of the commish (review authority; vetoes are
    league-wide, the commish just executes/vetoes the final call).
    clock: callable returning epoch seconds (default time.time).
    """

    STATUS_PROPOSED = "proposed"
    STATUS_ACCEPTED = "accepted"       # transient: immediately -> under_review
    STATUS_UNDER_REVIEW = "under_review"
    STATUS_EXECUTED = "executed"
    STATUS_VETOED = "vetoed"
    STATUS_DECLINED = "declined"
    STATUS_WITHDRAWN = "withdrawn"
    STATUS_EXPIRED = "expired"

    _PENDING = (STATUS_PROPOSED, STATUS_UNDER_REVIEW)

    def __init__(self, teams: dict, commissioner, clock=None):
        # Rosters are 14 during the season and 15 once a team has moved a
        # player to IL and added a replacement (P2-L7 sandbox finding: the
        # draft produces 14-man rosters, so trades must work at 14 — the
        # load-bearing invariant is size preservation, enforced by the
        # balanced-trade check in propose(), not a fixed size of 15).
        for tid, roster in teams.items():
            if len(roster) not in _LEGAL_ROSTER_SIZES or \
                    len(set(roster)) != len(roster):
                raise TradeError(
                    f"team {tid!r} roster must be {ACTIVE_ROSTER_SIZE} or "
                    f"{ROSTER_SIZE} unique players")
        if commissioner not in teams:
            raise UnknownTeam(f"commissioner {commissioner!r} not in league")
        self._rosters = {tid: list(r) for tid, r in teams.items()}
        self.commissioner = commissioner
        self.clock = clock or time.time
        self._trades: dict = {}   # trade_id -> trade dict
        self._next_id = 1
        self._deals: dict = {}    # deal_id -> deal dict (P5-W37)
        self._next_deal_id = 1

    # -- guards ------------------------------------------------------------
    def _require_team(self, team_id):
        if team_id not in self._rosters:
            raise UnknownTeam(f"unknown team_id {team_id!r}")

    def _get(self, trade_id) -> dict:
        try:
            return self._trades[trade_id]
        except KeyError:
            raise TradeError(f"unknown trade_id {trade_id!r}")

    def _pending_count(self, team_id) -> int:
        return (sum(1 for t in self._trades.values()
                    if t["status"] in self._PENDING and team_id in t["parties"])
                + sum(1 for d in self._deals.values()
                      if d["status"] in self._PENDING
                      and team_id in d["parties"]))

    def veto_threshold(self) -> int:
        """Vetoes needed: ceil((num_teams - 2) / 3), floored at 1.

        The floor matters in a 2-team league: the raw formula gives 0,
        and execute()'s `vetoes >= threshold` check would then veto
        every trade with zero vetoes cast (P4-L1).
        """
        return max(1, math.ceil((len(self._rosters) - 2) / 3))

    # -- propose -----------------------------------------------------------
    def propose(self, proposer, offeree, gives_proposer: list,
                gives_offeree: list, week: int, now=None) -> dict:
        """Propose a trade. Both lists are player_ids; counts must match."""
        self._require_team(proposer)
        self._require_team(offeree)
        if proposer == offeree:
            raise TradeError("a team cannot trade with itself")
        now = self.clock() if now is None else now
        if week > TRADE_DEADLINE_WEEK:
            raise TradeDeadlinePassed(
                f"trade deadline was end of week {TRADE_DEADLINE_WEEK}")
        if self._pending_count(proposer) >= MAX_PENDING_OUT:
            raise PendingCapExceeded(
                f"team {proposer!r} already has {MAX_PENDING_OUT} pending trades")
        if self._pending_count(offeree) >= MAX_PENDING_OUT:
            raise PendingCapExceeded(
                f"team {offeree!r} already has {MAX_PENDING_OUT} pending trades")
        for pid in gives_proposer:
            if pid not in self._rosters[proposer]:
                raise UnknownPlayer(
                    f"player {pid!r} not on {proposer!r}'s roster")
        for pid in gives_offeree:
            if pid not in self._rosters[offeree]:
                raise UnknownPlayer(
                    f"player {pid!r} not on {offeree!r}'s roster")
        if len(gives_proposer) != len(gives_offeree):
            raise UnbalancedTrade(
                f"{len(gives_proposer)}-for-{len(gives_offeree)} breaks "
                f"roster-size invariance")
        if len(set(gives_proposer)) != len(gives_proposer) or \
           len(set(gives_offeree)) != len(gives_offeree):
            raise TradeError("duplicate player in trade offer")
        tid = self._next_id
        self._next_id += 1
        trade = {
            "id": tid,
            "proposer": proposer,
            "offeree": offeree,
            "parties": (proposer, offeree),
            "gives": {proposer: list(gives_proposer),
                      offeree: list(gives_offeree)},
            "week": week,
            "status": self.STATUS_PROPOSED,
            "proposed_at": now,
            "expires_at": now + PROPOSAL_TTL_SECS,
            "accepted_at": None,
            "review_until": None,
            "decided_at": None,
            "vetoes": [],          # team_ids, in vote order
        }
        self._trades[tid] = trade
        return dict(trade)

    # -- offeree response --------------------------------------------------
    def _expire_if_stale(self, trade, now) -> bool:
        if trade["status"] == self.STATUS_PROPOSED and now > trade["expires_at"]:
            trade["status"] = self.STATUS_EXPIRED
            trade["decided_at"] = now
            return True
        return False

    def accept(self, trade_id, team_id, now=None) -> dict:
        """Offeree accepts -> trade enters the 2-day review window."""
        trade = self._get(trade_id)
        now = self.clock() if now is None else now
        if team_id != trade["offeree"]:
            raise NotAParty("only the offeree may accept")
        if self._expire_if_stale(trade, now):
            raise InvalidTradeState("proposal already expired")
        if trade["status"] != self.STATUS_PROPOSED:
            raise InvalidTradeState(
                f"cannot accept a {trade['status']} trade")
        trade["status"] = self.STATUS_UNDER_REVIEW
        trade["accepted_at"] = now
        trade["review_until"] = now + REVIEW_WINDOW_SECS
        return dict(trade)

    def decline(self, trade_id, team_id, now=None) -> dict:
        trade = self._get(trade_id)
        now = self.clock() if now is None else now
        if team_id != trade["offeree"]:
            raise NotAParty("only the offeree may decline")
        if trade["status"] != self.STATUS_PROPOSED:
            raise InvalidTradeState(
                f"cannot decline a {trade['status']} trade")
        trade["status"] = self.STATUS_DECLINED
        trade["decided_at"] = now
        return dict(trade)

    def withdraw(self, trade_id, team_id, now=None) -> dict:
        """Proposer withdraws before acceptance."""
        trade = self._get(trade_id)
        now = self.clock() if now is None else now
        if team_id != trade["proposer"]:
            raise NotAParty("only the proposer may withdraw")
        if trade["status"] != self.STATUS_PROPOSED:
            raise InvalidTradeState(
                f"cannot withdraw a {trade['status']} trade")
        trade["status"] = self.STATUS_WITHDRAWN
        trade["decided_at"] = now
        return dict(trade)

    # -- review / veto -----------------------------------------------------
    def veto(self, trade_id, team_id, now=None) -> dict:
        """A non-party team casts a veto vote during the review window.

        Returns the trade; when the threshold is reached the trade flips
        to vetoed immediately.
        """
        trade = self._get(trade_id)
        self._require_team(team_id)
        now = self.clock() if now is None else now
        if trade["status"] != self.STATUS_UNDER_REVIEW:
            raise VetoNotAllowed("trade is not under review")
        # Boundary ownership (P4-L1): the window is [accepted_at,
        # review_until) — at review_until the window has closed and
        # the trade becomes executable (execute refuses only strictly
        # before it, and the API settle path fires at >= review_until;
        # api/services.py _settle_trades). Previously a veto at
        # exactly review_until was ALSO accepted, so a veto and an
        # execute could both "win" at the same instant.
        if now >= trade["review_until"]:
            raise VetoNotAllowed("review window has closed")
        if team_id in trade["parties"]:
            raise VetoNotAllowed("trading parties may not veto")
        if team_id in trade["vetoes"]:
            raise VetoNotAllowed(f"team {team_id!r} already vetoed")
        trade["vetoes"].append(team_id)
        if len(trade["vetoes"]) >= self.veto_threshold():
            trade["status"] = self.STATUS_VETOED
            trade["decided_at"] = now
        return dict(trade)

    def execute(self, trade_id, team_id=None, now=None) -> dict:
        """Commissioner executes after the review window closes unvetoed.

        team_id defaults to the commissioner; anyone calling execute is
        recorded but only the review-window + no-veto conditions matter.
        """
        trade = self._get(trade_id)
        now = self.clock() if now is None else now
        if trade["status"] != self.STATUS_UNDER_REVIEW:
            raise InvalidTradeState(
                f"cannot execute a {trade['status']} trade")
        if now < trade["review_until"]:
            raise InvalidTradeState(
                f"review window still open until {trade['review_until']}")
        if len(trade["vetoes"]) >= self.veto_threshold():
            trade["status"] = self.STATUS_VETOED
            trade["decided_at"] = now
            return dict(trade)
        # Atomic roster swap. Validate BEFORE mutating: a player may
        # have been offered in two pending trades and already moved by
        # the first execution — fail cleanly with rosters untouched
        # instead of dying halfway through the swap (P4-L1).
        a, b = trade["parties"]
        ga, gb = trade["gives"][a], trade["gives"][b]
        missing = [pid for pid in ga if pid not in self._rosters[a]]
        missing += [pid for pid in gb if pid not in self._rosters[b]]
        if missing:
            raise InvalidTradeState(
                f"players no longer on the offering rosters: {missing} "
                f"(already traded away?) — trade cannot execute")
        for pid in ga:
            self._rosters[a].remove(pid)
        for pid in gb:
            self._rosters[b].remove(pid)
        self._rosters[a].extend(gb)
        self._rosters[b].extend(ga)
        trade["status"] = self.STATUS_EXECUTED
        trade["decided_at"] = now
        return dict(trade)

    def sweep(self, now=None) -> list:
        """Expire stale proposals; returns ids whose status changed."""
        now = self.clock() if now is None else now
        changed = []
        for trade in self._trades.values():
            if self._expire_if_stale(trade, now):
                changed.append(trade["id"])
        return changed

    # -- multi-team deals (P5-W37) ---------------------------------------
    def _get_deal(self, deal_id) -> dict:
        try:
            return self._deals[deal_id]
        except KeyError:
            raise TradeError(f"unknown deal_id {deal_id!r}")

    def _expire_deal_if_stale(self, deal, now) -> bool:
        if deal["status"] == self.STATUS_PROPOSED and now > deal["expires_at"]:
            deal["status"] = self.STATUS_EXPIRED
            deal["decided_at"] = now
            return True
        return False

    def propose_deal(self, proposer, legs: list, week: int, now=None) -> dict:
        """Propose a multi-team deal.

        legs: [{giver_id, receiver_id, player_ids}]. The proposer is
        the first leg's giver (callers pass legs[0]["giver_id"]) and
        counts as accepted. Guards: every leg's players must be on the
        giver's roster at proposal time; no player moves twice in one
        deal; EVERY team must give exactly as many players as it
        receives (roster-count invariance); every party must be under
        the pending cap; the week-6 deadline applies to the deal.
        """
        now = self.clock() if now is None else now
        if not legs:
            raise TradeError("a deal needs at least one leg")
        if week > TRADE_DEADLINE_WEEK:
            raise TradeDeadlinePassed(
                f"trade deadline was end of week {TRADE_DEADLINE_WEEK}")
        norm_legs = []
        for leg in legs:
            giver = leg["giver_id"]
            receiver = leg["receiver_id"]
            pids = list(leg["player_ids"])
            self._require_team(giver)
            self._require_team(receiver)
            if giver == receiver:
                raise TradeError("a deal leg cannot send players to the same team")
            if not pids:
                raise TradeError("each deal leg must move at least one player")
            if len(set(pids)) != len(pids):
                raise TradeError("duplicate player in deal leg")
            for pid in pids:
                if pid not in self._rosters[giver]:
                    raise UnknownPlayer(
                        f"player {pid!r} not on {giver!r}'s roster")
            norm_legs.append({"giver_id": giver, "receiver_id": receiver,
                              "player_ids": pids})
        seen = {}
        for leg in norm_legs:
            for pid in leg["player_ids"]:
                if pid in seen:
                    raise TradeError(
                        f"player {pid!r} moves twice in one deal")
                seen[pid] = leg["giver_id"]
        parties = sorted({l["giver_id"] for l in norm_legs}
                         | {l["receiver_id"] for l in norm_legs})
        if proposer not in parties:
            raise TradeError("proposer must be a party to the deal")
        gives_n = {t: 0 for t in parties}
        recv_n = {t: 0 for t in parties}
        for leg in norm_legs:
            gives_n[leg["giver_id"]] += len(leg["player_ids"])
            recv_n[leg["receiver_id"]] += len(leg["player_ids"])
        for t in parties:
            if gives_n[t] != recv_n[t]:
                raise UnbalancedTrade(
                    f"team {t!r} gives {gives_n[t]} but receives "
                    f"{recv_n[t]} — roster-size invariance")
        for t in parties:
            if self._pending_count(t) >= MAX_PENDING_OUT:
                raise PendingCapExceeded(
                    f"team {t!r} already has {MAX_PENDING_OUT} pending trades")
        did = self._next_deal_id
        self._next_deal_id += 1
        deal = {
            "id": did,
            "proposer": proposer,
            "legs": norm_legs,
            "parties": tuple(parties),
            "accepts": [proposer],   # proposer counts as accepted
            "week": week,
            "status": self.STATUS_PROPOSED,
            "proposed_at": now,
            "expires_at": now + PROPOSAL_TTL_SECS,
            "accepted_at": None,
            "review_until": None,
            "decided_at": None,
            "vetoes": [],
        }
        self._deals[did] = deal
        return dict(deal)

    def accept_deal(self, deal_id, team_id, now=None) -> dict:
        """A party accepts. When every party has accepted the deal
        enters the single 2-day review window."""
        deal = self._get_deal(deal_id)
        now = self.clock() if now is None else now
        if team_id not in deal["parties"]:
            raise NotAParty("only a deal party may accept")
        if self._expire_deal_if_stale(deal, now):
            raise InvalidTradeState("deal proposal already expired")
        if deal["status"] != self.STATUS_PROPOSED:
            raise InvalidTradeState(
                f"cannot accept a {deal['status']} deal")
        if team_id in deal["accepts"]:
            raise InvalidTradeState(f"team {team_id!r} already accepted")
        deal["accepts"].append(team_id)
        if set(deal["accepts"]) == set(deal["parties"]):
            deal["status"] = self.STATUS_UNDER_REVIEW
            deal["accepted_at"] = now
            deal["review_until"] = now + REVIEW_WINDOW_SECS
        return dict(deal)

    def decline_deal(self, deal_id, team_id, now=None) -> dict:
        """Any party rejecting dissolves the entire deal."""
        deal = self._get_deal(deal_id)
        now = self.clock() if now is None else now
        if team_id not in deal["parties"]:
            raise NotAParty("only a deal party may reject")
        if deal["status"] != self.STATUS_PROPOSED:
            raise InvalidTradeState(
                f"cannot reject a {deal['status']} deal")
        deal["status"] = self.STATUS_DECLINED
        deal["decided_at"] = now
        return dict(deal)

    def withdraw_deal(self, deal_id, team_id, now=None) -> dict:
        """The proposer withdraws before all parties accept —
        dissolves the entire deal."""
        deal = self._get_deal(deal_id)
        now = self.clock() if now is None else now
        if team_id != deal["proposer"]:
            raise NotAParty("only the proposer may withdraw")
        if deal["status"] != self.STATUS_PROPOSED:
            raise InvalidTradeState(
                f"cannot withdraw a {deal['status']} deal")
        deal["status"] = self.STATUS_WITHDRAWN
        deal["decided_at"] = now
        return dict(deal)

    def veto_deal(self, deal_id, team_id, now=None) -> dict:
        """A non-party team casts a veto vote during the deal's review
        window. Same one-third-of-league threshold as trades, computed
        on the whole league."""
        deal = self._get_deal(deal_id)
        self._require_team(team_id)
        now = self.clock() if now is None else now
        if deal["status"] != self.STATUS_UNDER_REVIEW:
            raise VetoNotAllowed("deal is not under review")
        if now >= deal["review_until"]:
            raise VetoNotAllowed("review window has closed")
        if team_id in deal["parties"]:
            raise VetoNotAllowed("deal parties may not veto")
        if team_id in deal["vetoes"]:
            raise VetoNotAllowed(f"team {team_id!r} already vetoed")
        deal["vetoes"].append(team_id)
        if len(deal["vetoes"]) >= self.veto_threshold():
            deal["status"] = self.STATUS_VETOED
            deal["decided_at"] = now
        return dict(deal)

    def execute_deal(self, deal_id, team_id=None, now=None) -> dict:
        """Execute after the deal's review window closes unvetoed.

        Atomic multi-leg swap: validate BEFORE mutating — every leg's
        players must still be on the giver's roster — so a competing
        execution fails cleanly with all rosters untouched (P4-L1).
        """
        deal = self._get_deal(deal_id)
        now = self.clock() if now is None else now
        if deal["status"] != self.STATUS_UNDER_REVIEW:
            raise InvalidTradeState(
                f"cannot execute a {deal['status']} deal")
        if now < deal["review_until"]:
            raise InvalidTradeState(
                f"review window still open until {deal['review_until']}")
        if len(deal["vetoes"]) >= self.veto_threshold():
            deal["status"] = self.STATUS_VETOED
            deal["decided_at"] = now
            return dict(deal)
        missing = [pid for leg in deal["legs"] for pid in leg["player_ids"]
                   if pid not in self._rosters[leg["giver_id"]]]
        if missing:
            raise InvalidTradeState(
                f"players no longer on the giving rosters: {missing} "
                f"(already traded away?) — deal cannot execute")
        for leg in deal["legs"]:
            for pid in leg["player_ids"]:
                self._rosters[leg["giver_id"]].remove(pid)
        for leg in deal["legs"]:
            self._rosters[leg["receiver_id"]].extend(leg["player_ids"])
        deal["status"] = self.STATUS_EXECUTED
        deal["decided_at"] = now
        return dict(deal)

    def sweep_deals(self, now=None) -> list:
        """Expire stale deal proposals; returns ids whose status changed."""
        now = self.clock() if now is None else now
        changed = []
        for deal in self._deals.values():
            if self._expire_deal_if_stale(deal, now):
                changed.append(deal["id"])
        return changed

    def get_deal(self, deal_id):
        d = self._get_deal(deal_id)
        return {**d, "parties": list(d["parties"]),
                "accepts": list(d["accepts"]),
                "vetoes": list(d["vetoes"]),
                "legs": [{"giver_id": l["giver_id"],
                          "receiver_id": l["receiver_id"],
                          "player_ids": list(l["player_ids"])}
                         for l in d["legs"]]}

    # -- reads -------------------------------------------------------------
    def get_trade(self, trade_id):
        t = self._get(trade_id)
        return {**t, "vetoes": list(t["vetoes"]),
                "gives": {k: list(v) for k, v in t["gives"].items()}}

    def pending_for(self, team_id) -> list:
        self._require_team(team_id)
        return [t["id"] for t in self._trades.values()
                if t["status"] in self._PENDING and team_id in t["parties"]]

    def get_roster(self, team_id) -> list:
        self._require_team(team_id)
        return list(self._rosters[team_id])

    # -- JSON contract -----------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "commissioner": self.commissioner,
            "rosters": {tid: list(r) for tid, r in self._rosters.items()},
            "next_id": self._next_id,
            "trades": {str(tid): {**t, "parties": list(t["parties"]),
                                  "vetoes": list(t["vetoes"]),
                                  "gives": {k: list(v)
                                            for k, v in t["gives"].items()}}
                       for tid, t in self._trades.items()},
            # P5-W37 deals: separate sequential id namespace from trades.
            "next_deal_id": self._next_deal_id,
            "deals": {str(did): {**d, "parties": list(d["parties"]),
                                 "accepts": list(d["accepts"]),
                                 "vetoes": list(d["vetoes"]),
                                 "legs": [{"giver_id": l["giver_id"],
                                           "receiver_id": l["receiver_id"],
                                           "player_ids": list(l["player_ids"])}
                                          for l in d["legs"]]}
                      for did, d in self._deals.items()},
        }

    @classmethod
    def from_dict(cls, state: dict, clock=None) -> "TradeEngine":
        eng = cls(state["rosters"], state["commissioner"], clock=clock)
        eng._next_id = state["next_id"]
        for tid_s, t in state["trades"].items():
            eng._trades[int(tid_s)] = {
                **t, "parties": tuple(t["parties"]),
                "vetoes": list(t["vetoes"]),
                "gives": {k: list(v) for k, v in t["gives"].items()},
            }
        # Pre-P5-W37 engine states carry no deals — default to empty.
        eng._next_deal_id = state.get("next_deal_id", 1)
        for did_s, d in state.get("deals", {}).items():
            eng._deals[int(did_s)] = {
                **d, "parties": tuple(d["parties"]),
                "accepts": list(d.get("accepts", [])),
                "vetoes": list(d["vetoes"]),
                "legs": [{"giver_id": l["giver_id"],
                          "receiver_id": l["receiver_id"],
                          "player_ids": list(l["player_ids"])}
                         for l in d["legs"]],
            }
        return eng
