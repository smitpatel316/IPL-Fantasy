"""Tests for trade_engine.py — hand-derived scenarios.

Ported 2026-09-15 from pytest to stdlib unittest: pytest is not
installed in this environment, so the old file could not run at all
(the earlier "13/13" claim was never verifiable here). Same 13
scenarios, plus a 14-man roster regression test for the P2-L7
integration fix (the draft produces 14-man rosters; trades must work
at 14, not just at the full 15).

Plain unittest, stdlib only. Run:  python3 test_trade_engine.py
"""

import json
import unittest

from api.engine.trade_engine import (
    TradeEngine, TradeError, UnknownTeam, UnknownPlayer, UnbalancedTrade,
    PendingCapExceeded, TradeDeadlinePassed, InvalidTradeState, NotAParty,
    VetoNotAllowed, TRADE_DEADLINE_WEEK, REVIEW_WINDOW_SECS,
    PROPOSAL_TTL_SECS, MAX_PENDING_OUT,
)

NOW = 1_000_000.0


def _eng(now=NOW, n_teams=6, roster_size=15):
    teams = {f"t{i}": [f"p{i}_{j}" for j in range(roster_size)]
             for i in range(n_teams)}
    return TradeEngine(teams, commissioner="t0", clock=lambda: now)


def _propose(eng, a="t1", b="t2", ga=None, gb=None, week=3, now=NOW):
    ga = ga or [f"p{a[1:]}_{0}"]
    gb = gb or [f"p{b[1:]}_{0}"]
    return eng.propose(a, b, ga, gb, week=week, now=now)


class TestTradeLifecycle(unittest.TestCase):
    def test_full_lifecycle_executes(self):
        eng = _eng()
        t = _propose(eng, ga=["p1_0", "p1_1"], gb=["p2_0", "p2_1"])
        self.assertEqual(t["status"], "proposed")
        eng.accept(t["id"], "t2", now=NOW)
        tr = eng.get_trade(t["id"])
        self.assertEqual(tr["status"], "under_review")
        self.assertEqual(tr["review_until"], NOW + REVIEW_WINDOW_SECS)
        eng.execute(t["id"], now=NOW + REVIEW_WINDOW_SECS + 1)
        tr = eng.get_trade(t["id"])
        self.assertEqual(tr["status"], "executed")
        r1, r2 = eng.get_roster("t1"), eng.get_roster("t2")
        self.assertIn("p2_0", r1)
        self.assertIn("p2_1", r1)
        self.assertNotIn("p1_0", r1)
        self.assertIn("p1_0", r2)
        self.assertIn("p1_1", r2)
        self.assertNotIn("p2_0", r2)
        self.assertEqual(len(r1), 15)
        self.assertEqual(len(r2), 15)

    def test_fourteen_man_rosters_trade(self):
        # P2-L7: the draft produces 14-man rosters. Trades must work at
        # 14 — size is preserved by the balanced-trade rule, not by a
        # fixed size of 15.
        eng = _eng(roster_size=14)
        t = _propose(eng, ga=["p1_0"], gb=["p2_0"], week=5)
        eng.accept(t["id"], "t2", now=NOW)
        eng.execute(t["id"], now=NOW + REVIEW_WINDOW_SECS + 1)
        self.assertEqual(eng.get_trade(t["id"])["status"], "executed")
        r1, r2 = eng.get_roster("t1"), eng.get_roster("t2")
        self.assertEqual(len(r1), 14)
        self.assertEqual(len(r2), 14)
        self.assertIn("p2_0", r1)
        self.assertIn("p1_0", r2)

    def test_execute_before_window_closes_rejected(self):
        eng = _eng()
        t = _propose(eng)
        eng.accept(t["id"], "t2", now=NOW)
        with self.assertRaises(InvalidTradeState):
            eng.execute(t["id"], now=NOW + REVIEW_WINDOW_SECS - 1)


class TestVeto(unittest.TestCase):
    def test_veto_threshold_blocks_trade(self):
        # 6 teams -> ceil((6-2)/3) = 2 vetoes needed.
        eng = _eng(n_teams=6)
        self.assertEqual(eng.veto_threshold(), 2)
        t = _propose(eng)
        eng.accept(t["id"], "t2", now=NOW)
        eng.veto(t["id"], "t3", now=NOW + 100.0)
        self.assertEqual(eng.get_trade(t["id"])["status"], "under_review")
        eng.veto(t["id"], "t4", now=NOW + 200.0)
        tr = eng.get_trade(t["id"])
        self.assertEqual(tr["status"], "vetoed")
        # Rosters untouched.
        self.assertIn("p1_0", eng.get_roster("t1"))

    def test_veto_rules(self):
        eng = _eng()
        t = _propose(eng)
        eng.accept(t["id"], "t2", now=NOW)
        with self.assertRaises(VetoNotAllowed):  # party team
            eng.veto(t["id"], "t1", now=NOW + 100.0)
        eng.veto(t["id"], "t3", now=NOW + 100.0)
        with self.assertRaises(VetoNotAllowed):  # duplicate
            eng.veto(t["id"], "t3", now=NOW + 200.0)
        with self.assertRaises(VetoNotAllowed):  # after window
            eng.veto(t["id"], "t4", now=NOW + REVIEW_WINDOW_SECS + 5)


class TestGuards(unittest.TestCase):
    def test_deadline_blocks_new_proposals(self):
        eng = _eng()
        with self.assertRaises(TradeDeadlinePassed):
            _propose(eng, week=TRADE_DEADLINE_WEEK + 1)
        # Week 6 itself is fine.
        t = _propose(eng, week=TRADE_DEADLINE_WEEK)
        self.assertEqual(t["status"], "proposed")

    def test_pending_cap(self):
        eng = _eng()
        ids = [_propose(eng, b=f"t{i}", week=1)["id"]
               for i in range(2, 2 + MAX_PENDING_OUT)]
        self.assertEqual(len(ids), MAX_PENDING_OUT)
        with self.assertRaises(PendingCapExceeded):
            eng.propose("t1", "t5", ["p1_2"], ["p5_0"], week=1)
        # Declining one frees a slot.
        eng.decline(ids[0], "t2", now=NOW)
        t = eng.propose("t1", "t5", ["p1_2"], ["p5_0"], week=1)
        self.assertEqual(t["status"], "proposed")

    def test_unbalanced_rejected(self):
        eng = _eng()
        with self.assertRaises(UnbalancedTrade):
            eng.propose("t1", "t2", ["p1_0", "p1_1"], ["p2_0"], week=1)

    def test_unknown_player_rejected(self):
        eng = _eng()
        with self.assertRaises(UnknownPlayer):
            # p2_0 is not t1's.
            eng.propose("t1", "t2", ["p2_0"], ["p2_0"], week=1)

    def test_self_trade_and_bad_team(self):
        eng = _eng()
        with self.assertRaises(TradeError):
            eng.propose("t1", "t1", ["p1_0"], ["p1_0"], week=1)
        with self.assertRaises(UnknownTeam):
            eng.propose("t1", "nope", ["p1_0"], ["p1_0"], week=1)

    def test_proposal_expiry(self):
        eng = _eng(now=NOW)
        t = _propose(eng)
        changed = eng.sweep(now=NOW + PROPOSAL_TTL_SECS + 1)
        self.assertEqual(changed, [t["id"]])
        self.assertEqual(eng.get_trade(t["id"])["status"], "expired")
        with self.assertRaises(InvalidTradeState):
            eng.accept(t["id"], "t2", now=NOW + PROPOSAL_TTL_SECS + 2)

    def test_withdraw_and_decline(self):
        eng = _eng()
        t = _propose(eng)
        eng.withdraw(t["id"], "t1")
        self.assertEqual(eng.get_trade(t["id"])["status"], "withdrawn")
        t2 = _propose(eng)
        eng.decline(t2["id"], "t2")
        self.assertEqual(eng.get_trade(t2["id"])["status"], "declined")
        with self.assertRaises(NotAParty):
            eng.accept(t2["id"], "t1")  # proposer can't accept own trade

    def test_pending_for_listing(self):
        eng = _eng()
        t = _propose(eng)
        self.assertEqual(eng.pending_for("t1"), [t["id"]])
        self.assertEqual(eng.pending_for("t3"), [])
        eng.accept(t["id"], "t2", now=NOW)
        # review still counts as pending
        self.assertEqual(eng.pending_for("t2"), [t["id"]])


class TestJsonContract(unittest.TestCase):
    def test_json_roundtrip(self):
        eng = _eng(now=NOW)
        t = _propose(eng)
        eng.accept(t["id"], "t2", now=NOW)
        eng.veto(t["id"], "t3", now=NOW + 100.0)
        eng2 = TradeEngine.from_dict(eng.to_dict())
        json.dumps(eng.to_dict())
        tr = eng2.get_trade(t["id"])
        self.assertEqual(tr["status"], "under_review")
        self.assertEqual(tr["vetoes"], ["t3"])
        eng2.execute(t["id"], now=NOW + REVIEW_WINDOW_SECS + 1)
        self.assertEqual(eng2.get_trade(t["id"])["status"], "executed")


if __name__ == "__main__":
    unittest.main()
