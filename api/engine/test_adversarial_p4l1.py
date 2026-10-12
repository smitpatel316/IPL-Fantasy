"""Adversarial edge-case tests — P4-L1 (Phase 4 hardening loop).

Hand-derived hostile scenarios from the P4-L1 backlog item, one section
per named case:

- Waiver: FAAB tie at exact budget; the same drop player offered on two
  claims in one week (contingency bids must not crash the run).
- Trade: veto landing exactly at the review deadline vs execute at the
  same instant (the boundary must belong to exactly one of them);
  executing a second trade for an already-traded player (atomicity);
  veto threshold in a 2-team league (ceil((2-2)/3) == 0 must not make
  every trade auto-vetoed).
- Roster/IL: IL move mid-week after the lineup is locked (frozen week
  stands, future weeks honour the IL slot); IL-eligibility revocation
  while the player sits on IL with a replacement added (must not
  deadlock every future lineup).
- Playoffs: ties at every stage go to the higher seed; non-finite
  weekly totals (NaN / inf) fail closed in both the playoff engine and
  the matchup scheduler (NaN comparisons are all False, so an
  unguarded NaN silently records as a tie and poisons PF sums).
- Draft: auto-pick when ranks + DND exhaust the one role the team
  still needs (must fail closed with PoolExhausted, state untouched).

Plain unittest, stdlib only. Run:
  repo/.venv/bin/python -m unittest discover -s api/engine
"""

import unittest

from api.engine.draft_engine import Draft, DraftConfig, PoolExhausted
from api.engine.matchup_scheduler import (
    ScheduleConfig, ScheduleError, Season,
)
from api.engine.playoff_engine import (
    PlayoffBracket, PlayoffConfig, PlayoffError,
)
from api.engine.roster_service import (
    ILIneligible, LineupLocked, LineupService,
)
from api.engine.trade_engine import (
    REVIEW_WINDOW_SECS, InvalidTradeState, TradeEngine,
)
from api.engine.waiver_engine import (
    OverBudget, WaiverEngine, WeekAlreadyRun,
)

NOW = 1_000_000.0


# ---------------------------------------------------------------------------
# Waivers
# ---------------------------------------------------------------------------

def _waiver_eng():
    teams = {
        "best":  [f"b{i}" for i in range(15)],
        "mid":   [f"m{i}" for i in range(15)],
        "worst": [f"w{i}" for i in range(15)],
    }
    pool = ["fa1", "fa2", "fa3", "fa4"]
    return WaiverEngine(teams, pool, budget=100, clock=lambda: NOW)


STANDINGS = ["best", "mid", "worst"]  # best-first; worst wins ties


class TestWaiverAdversarial(unittest.TestCase):

    def test_faab_tie_at_exact_full_budget(self):
        # Both contenders bid their ENTIRE remaining budget ($100).
        # Reverse-standings tiebreak: the worst team wins and is drained
        # to exactly $0; the loser keeps its $100.
        eng = _waiver_eng()
        eng.submit_bid("best", 1, "fa1", 100, drop_player_id="b0", now=NOW)
        eng.submit_bid("worst", 1, "fa1", 100, drop_player_id="w0", now=NOW)
        eng.submit_bid("mid", 1, "fa1", 99, drop_player_id="m0", now=NOW)
        results = eng.run_week(1, STANDINGS, now=NOW)
        by_player = {r["player_id"]: r for r in results}
        self.assertEqual(by_player["fa1"]["winner"], "worst")
        self.assertEqual(by_player["fa1"]["amount"], 100)
        self.assertEqual(eng.get_budget("worst"), 0)
        self.assertEqual(eng.get_budget("best"), 100)
        self.assertIn("fa1", eng.get_roster("worst"))
        self.assertNotIn("w0", eng.get_roster("worst"))
        # A drained team cannot bid $1 next week, but a $0 bid is legal
        # and still wins a tie on the reverse-standings tiebreak.
        with self.assertRaises(OverBudget):
            eng.submit_bid("worst", 2, "fa2", 1, drop_player_id="w1",
                           now=NOW)
        eng.submit_bid("worst", 2, "fa2", 0, drop_player_id="w1", now=NOW)
        eng.submit_bid("best", 2, "fa2", 0, drop_player_id="b1", now=NOW)
        results2 = eng.run_week(2, STANDINGS, now=NOW)
        by_player2 = {r["player_id"]: r for r in results2}
        self.assertEqual(by_player2["fa2"]["winner"], "worst")
        self.assertEqual(by_player2["fa2"]["amount"], 0)

    def test_same_drop_on_two_claims_does_not_crash_run(self):
        # Contingency bidding: mid offers m0 as the drop for BOTH fa1
        # ($50) and fa2 ($40). Winning fa1 spends m0; the fa2 claim can
        # no longer settle and must forfeit to the next bidder (best,
        # $30) — the run must not die halfway with the budget already
        # deducted and the week unrecorded.
        eng = _waiver_eng()
        eng.submit_bid("mid", 1, "fa1", 50, drop_player_id="m0", now=NOW)
        eng.submit_bid("mid", 1, "fa2", 40, drop_player_id="m0", now=NOW)
        eng.submit_bid("best", 1, "fa2", 30, drop_player_id="b0", now=NOW)
        results = eng.run_week(1, STANDINGS, now=NOW)
        by_player = {r["player_id"]: r for r in results}
        self.assertEqual(by_player["fa1"]["winner"], "mid")
        self.assertEqual(by_player["fa1"]["amount"], 50)
        self.assertEqual(by_player["fa2"]["winner"], "best")
        self.assertEqual(by_player["fa2"]["amount"], 30)
        self.assertIn("mid", by_player["fa2"]["forfeited_by"])
        self.assertEqual(eng.get_budget("mid"), 50)
        mid_roster = eng.get_roster("mid")
        self.assertIn("fa1", mid_roster)
        self.assertNotIn("fa2", mid_roster)
        self.assertNotIn("m0", mid_roster)
        self.assertIn("fa2", eng.get_roster("best"))
        # The run is recorded exactly once; state is consistent.
        self.assertIsNotNone(eng.get_run(1))
        with self.assertRaises(WeekAlreadyRun):
            eng.run_week(1, STANDINGS, now=NOW)

    def test_same_drop_on_two_claims_unopposed_second_claim_voids(self):
        # Same shape with NO second bidder on fa2: the unsettleable
        # claim resolves as winner=None (not a crash, not a free player
        # whose drop no longer exists).
        eng = _waiver_eng()
        eng.submit_bid("mid", 1, "fa1", 50, drop_player_id="m0", now=NOW)
        eng.submit_bid("mid", 1, "fa2", 40, drop_player_id="m0", now=NOW)
        results = eng.run_week(1, STANDINGS, now=NOW)
        by_player = {r["player_id"]: r for r in results}
        self.assertEqual(by_player["fa1"]["winner"], "mid")
        self.assertIsNone(by_player["fa2"]["winner"])
        self.assertIn("mid", by_player["fa2"]["forfeited_by"])
        self.assertIn("fa2", eng.pool)
        self.assertEqual(eng.get_budget("mid"), 50)


# ---------------------------------------------------------------------------
# Trades
# ---------------------------------------------------------------------------

def _trade_eng(n_teams=6, roster_size=14):
    teams = {f"t{i}": [f"p{i}_{j}" for j in range(roster_size)]
             for i in range(n_teams)}
    return TradeEngine(teams, commissioner="t0", clock=lambda: NOW)


class TestTradeAdversarial(unittest.TestCase):

    def test_veto_at_exact_review_deadline_counts_execute_waits(self):
        # The review deadline instant must belong to exactly one side.
        # Consistent with the proposal TTL (accept AT expires_at is
        # legal; expiry is strictly after), the window protects the
        # vetoers through review_until inclusive: a veto cast at
        # exactly review_until counts, and execute at that same
        # instant must still refuse.
        eng = _trade_eng()
        t = eng.propose("t1", "t2", ["p1_0"], ["p2_0"], week=3, now=NOW)
        eng.accept(t["id"], "t2", now=NOW)
        review_until = NOW + REVIEW_WINDOW_SECS
        eng.veto(t["id"], "t3", now=review_until)
        eng.veto(t["id"], "t4", now=review_until)  # threshold 2 of 6 teams
        tr = eng.get_trade(t["id"])
        self.assertEqual(tr["status"], "vetoed")
        self.assertEqual(tr["decided_at"], review_until)

        eng2 = _trade_eng()
        t2 = eng2.propose("t1", "t2", ["p1_0"], ["p2_0"], week=3, now=NOW)
        eng2.accept(t2["id"], "t2", now=NOW)
        with self.assertRaises(InvalidTradeState):
            eng2.execute(t2["id"], now=review_until)
        done = eng2.execute(t2["id"], now=review_until + 1)
        self.assertEqual(done["status"], "executed")

    def test_execute_second_trade_for_traded_player_fails_atomically(self):
        # t1 offers p1_0 in TWO pending trades. The first executes;
        # the second must fail with InvalidTradeState and leave every
        # roster byte-identical (no partial removal of p1_1 before the
        # missing p1_0 is noticed).
        eng = _trade_eng()
        a = eng.propose("t1", "t2", ["p1_0"], ["p2_0"], week=3, now=NOW)
        b = eng.propose("t1", "t3", ["p1_1", "p1_0"], ["p3_0", "p3_1"],
                        week=3, now=NOW)
        eng.accept(a["id"], "t2", now=NOW)
        eng.accept(b["id"], "t3", now=NOW)
        after = NOW + REVIEW_WINDOW_SECS + 1
        eng.execute(a["id"], now=after)
        snap_t1 = eng.get_roster("t1")
        snap_t3 = eng.get_roster("t3")
        self.assertIn("p1_0", eng.get_roster("t2"))
        with self.assertRaises(InvalidTradeState):
            eng.execute(b["id"], now=after)
        self.assertEqual(eng.get_roster("t1"), snap_t1)
        self.assertEqual(eng.get_roster("t3"), snap_t3)
        self.assertIn("p1_1", eng.get_roster("t1"))

    def test_two_team_league_trade_can_execute(self):
        # ceil((2 - 2) / 3) == 0: with no floor, execute()'s
        # vetoes >= threshold check is 0 >= 0 and EVERY trade in a
        # 2-team league is "vetoed" with zero vetoes cast.
        teams = {"x": [f"x{j}" for j in range(14)],
                 "y": [f"y{j}" for j in range(14)]}
        eng = TradeEngine(teams, commissioner="x", clock=lambda: NOW)
        self.assertGreaterEqual(eng.veto_threshold(), 1)
        t = eng.propose("x", "y", ["x0"], ["y0"], week=3, now=NOW)
        eng.accept(t["id"], "y", now=NOW)
        done = eng.execute(t["id"], now=NOW + REVIEW_WINDOW_SECS + 1)
        self.assertEqual(done["status"], "executed")
        self.assertIn("y0", eng.get_roster("x"))
        self.assertIn("x0", eng.get_roster("y"))


# ---------------------------------------------------------------------------
# Roster / IL
# ---------------------------------------------------------------------------

def _roster_roles():
    roles = {"wk1": {"role": "WK", "is_overseas": False}}
    for i in range(1, 6):
        roles[f"bat{i}"] = {"role": "BAT", "is_overseas": False}
        roles[f"bowl{i}"] = {"role": "BOWL", "is_overseas": False}
    for i in range(1, 4):
        roles[f"ar{i}"] = {"role": "AR", "is_overseas": False}
    roles["new1"] = {"role": "BOWL", "is_overseas": False}
    return roles


def _roster14():
    return (["wk1"] + [f"bat{i}" for i in range(1, 6)]
            + [f"ar{i}" for i in range(1, 4)]
            + [f"bowl{i}" for i in range(1, 6)])


def _valid_assignment():
    return {
        "wk1": "WK",
        "bat1": "BAT", "bat2": "BAT", "bat3": "BAT",
        "ar1": "AR", "ar2": "AR",
        "bowl1": "BOWL", "bowl2": "BOWL", "bowl3": "BOWL",
        "bat4": "UTIL", "ar3": "UTIL",
        "bat5": "BN", "bowl4": "BN", "bowl5": "BN",
    }


class TestRosterILAdversarial(unittest.TestCase):

    def test_il_move_after_lock_freezes_week_governs_future(self):
        # Named case: IL move mid-week AFTER the lineup locked. The
        # locked week is frozen history (starters unchanged, edits
        # still refused); the IL move governs future weeks, which must
        # place the player in the IL slot.
        svc = LineupService({"A": _roster14()}, _roster_roles(),
                            il_eligible={"bowl4"}, clock=lambda: NOW)
        svc.set_lineup("A", 1, _valid_assignment(),
                       lock_deadline=NOW + 100, now=NOW)
        svc.lock("A", 1, now=NOW)
        frozen_starters = svc.get_starters("A", 1)
        svc.move_to_il("A", "bowl4")
        self.assertEqual(svc.get_starters("A", 1), frozen_starters)
        with self.assertRaises(LineupLocked):
            svc.set_lineup("A", 1, _valid_assignment(), now=NOW + 50)
        week2 = dict(_valid_assignment())
        week2["bowl4"] = "IL"
        summary = svc.set_lineup("A", 2, week2, now=NOW + 200)
        self.assertEqual(len(summary["starters"]), 11)
        with self.assertRaises(ILIneligible):
            svc.set_lineup("A", 3, _valid_assignment(), now=NOW + 300)

    def test_il_eligibility_revocation_does_not_deadlock(self):
        # bowl5 goes on IL, a replacement is added (active back to
        # 14), then the injury feed REVOKES bowl5's eligibility (he
        # recovered). Pre-fix this deadlocked the team forever: bowl5
        # had to occupy IL (roster-level IL state) but was no longer
        # IL-eligible, and activate_from_il refused (active full) —
        # no legal lineup existed for any future week. The IL occupant
        # keeps the slot he was legally moved into (eligibility is a
        # move_to_il gate); everyone else still needs eligibility.
        svc = LineupService({"A": _roster14()}, _roster_roles(),
                            il_eligible={"bowl5"}, clock=lambda: NOW)
        svc.move_to_il("A", "bowl5")
        svc.add_player("A", "new1",
                       {"role": "BOWL", "is_overseas": False})
        week1 = dict(_valid_assignment())
        week1["bowl5"] = "IL"   # BN becomes bat5 / bowl4 / new1 (x3)
        week1["new1"] = "BN"    # 15 placed: 11 starters + 3 BN + 1 IL
        svc.set_lineup("A", 1, week1, now=NOW)
        svc.set_il_eligible(set())  # feed: bowl5 recovered
        summary = svc.set_lineup("A", 2, week1, now=NOW + 100)
        self.assertEqual(len(summary["starters"]), 11)
        # A non-occupant still may not take the IL slot.
        bad = dict(week1)
        bad["bowl5"] = "BN"
        bad["new1"] = "IL"
        with self.assertRaises(ILIneligible):
            svc.set_lineup("A", 3, bad, now=NOW + 200)


# ---------------------------------------------------------------------------
# Playoffs + scheduler: ties and non-finite totals
# ---------------------------------------------------------------------------

def _bracket():
    return PlayoffBracket(
        PlayoffConfig(seeds=("s1", "s2", "s3", "s4"),
                      consolation=("s5", "s6")),
        clock=lambda: NOW)


class TestPlayoffAdversarial(unittest.TestCase):

    def test_ties_at_every_stage_go_to_higher_seed(self):
        br = _bracket()
        br.record_week(7, {"s1": 100.0, "s4": 100.0,   # tie -> s1
                           "s2": 120.0, "s3": 120.0,   # tie -> s2
                           "s5": 80.0, "s6": 80.0})    # tie -> s5
        br.record_week(8, {"s1": 90.0, "s2": 90.0,     # final tie -> s1
                           "s3": 70.0, "s4": 70.0})    # 3rd-place tie -> s3
        self.assertEqual(br.champion(), "s1")
        self.assertEqual(br.placements(),
                         {1: "s1", 2: "s2", 3: "s3",
                          4: "s4", 5: "s5", 6: "s6"})

    def test_nonfinite_totals_fail_closed(self):
        for bad in (float("nan"), float("inf"), float("-inf")):
            br = _bracket()
            with self.assertRaises(PlayoffError):
                br.record_week(7, {"s1": bad, "s2": 100.0, "s3": 110.0,
                                   "s4": 90.0, "s5": 80.0, "s6": 70.0})


class TestSchedulerAdversarial(unittest.TestCase):

    def test_nonfinite_totals_fail_closed(self):
        teams = tuple((t, f"Team {t}") for t in "ABCD")
        cfg = ScheduleConfig(teams=teams, seed=42, team_order=tuple("ABCD"))
        for bad in (float("nan"), float("inf")):
            season = Season(cfg, clock=lambda: NOW)
            with self.assertRaises(ScheduleError):
                season.record_week(
                    1, {"A": bad, "B": 10.0, "C": 10.0, "D": 10.0})


# ---------------------------------------------------------------------------
# Draft: auto-pick when ranks + DND exhaust the needed role
# ---------------------------------------------------------------------------

def _draft_roles(pool):
    roles = {}
    for pid in pool:
        if "wk" in pid:
            role = "WK"
        elif "bat" in pid:
            role = "BAT"
        elif "bowl" in pid:
            role = "BOWL"
        else:
            role = "AR"
        roles[pid] = {"role": role, "is_overseas": False}
    return roles


class TestDraftAdversarial(unittest.TestCase):

    def test_auto_pick_when_dnd_exhausts_needed_role(self):
        # A drafts 13 players leaving exactly one open starter slot
        # (BOWL). Every undrafted BAT/AR/BOWL is on A's Do-Not-Draft
        # list; only spare WKs remain available to A. Auto-pick must
        # fail closed (PoolExhausted) and leave the draft untouched —
        # never stuff a third WK onto a full bench or corrupt state.
        a_picks = ["awk", "abat1", "abat2", "abat3", "aar1", "aar2",
                   "abowl1", "abowl2", "abat4", "aar3", "awk2", "awk3",
                   "abat5"]
        b_picks = (["bwk"] + [f"bbat{i}" for i in range(1, 6)]
                   + [f"barr{i}" for i in range(1, 4)]
                   + [f"bbowl{i}" for i in range(1, 6)])
        leftovers = ["awk4", "awk5"]            # only players A may take
        extras = ["xbat", "xar", "xbowl"]       # all on A's DND
        pool = a_picks + b_picks + leftovers + extras
        config = DraftConfig(
            teams=(("A", "Team A"), ("B", "Team B")),
            rounds=14, draft_order=("A", "B"))
        draft = Draft(config, pool, roles=_draft_roles(pool),
                      clock=lambda: NOW)
        for pid in extras:
            draft.add_to_dnd("A", pid)
        draft.start()
        a_iter, b_iter = iter(a_picks), iter(b_picks)
        while draft.picks_made < 27:
            team = draft.on_clock_team_id
            if team == "A":
                draft.manual_pick("A", next(a_iter))
            else:
                draft.manual_pick("B", next(b_iter))
        self.assertEqual(draft.current_pick_no, 28)
        self.assertEqual(draft.on_clock_team_id, "A")
        roster_a = draft.rosters["A"]
        self.assertEqual(sum(len(v) for v in roster_a.values()), 13)
        self.assertEqual(len(roster_a["BOWL"]), 2)  # the one open slot
        with self.assertRaises(PoolExhausted):
            draft.auto_pick("A")
        # State untouched: still pick 28, still live, roster unchanged.
        self.assertEqual(draft.current_pick_no, 28)
        self.assertEqual(draft.status, "live")
        self.assertEqual(
            sum(len(v) for v in draft.rosters["A"].values()), 13)


if __name__ == "__main__":
    unittest.main()
