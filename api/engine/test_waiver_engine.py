"""Tests for waiver_engine.py — hand-derived scenarios.

Rewritten 2026-09-15 from pytest to stdlib unittest (same 14 scenarios):
pytest is not installed in this container, so the old file could not
execute here (ModuleNotFoundError). No changes to waiver_engine.py.

Plain unittest, stdlib only. Run:  python3 test_waiver_engine.py
"""

import json
import unittest

from api.engine.waiver_engine import (
    WaiverEngine, WaiverError, UnknownTeam, UnknownPlayer, NotOnRoster,
    FrozenPlayer, OverBudget, BidClosed, WeekAlreadyRun, FREEZE_SECS,
)

NOW = 1_000_000.0
STANDINGS = ["best", "mid", "worst"]  # best-first


def _eng(now=NOW, budget=100):
    teams = {
        "best":  [f"b{i}" for i in range(15)],
        "mid":   [f"m{i}" for i in range(15)],
        "worst": [f"w{i}" for i in range(15)],
    }
    pool = ["fa1", "fa2", "fa3", "fa4"]
    return WaiverEngine(teams, pool, budget=budget, clock=lambda: now)


class TestBidding(unittest.TestCase):
    def test_highest_bid_wins_and_pays(self):
        eng = _eng()
        eng.submit_bid("best", 1, "fa1", 20, drop_player_id="b0")
        eng.submit_bid("worst", 1, "fa1", 30, drop_player_id="w0")
        res = eng.run_week(1, STANDINGS)
        self.assertEqual(len(res), 1)
        r = res[0]
        self.assertEqual(r["winner"], "worst")
        self.assertEqual(r["amount"], 30)
        self.assertEqual(r["drop"], "w0")
        self.assertEqual(r["forfeited_by"], [])
        self.assertEqual(eng.get_budget("worst"), 70)
        self.assertEqual(eng.get_budget("best"), 100)  # losers pay nothing
        roster = eng.get_roster("worst")
        self.assertIn("fa1", roster)
        self.assertNotIn("w0", roster)
        self.assertEqual(len(roster), 15)

    def test_tie_goes_to_worst_team(self):
        eng = _eng()
        eng.submit_bid("best", 1, "fa1", 25, drop_player_id="b0")
        eng.submit_bid("worst", 1, "fa1", 25, drop_player_id="w0")
        eng.submit_bid("mid", 1, "fa1", 25, drop_player_id="m0")
        res = eng.run_week(1, STANDINGS)
        self.assertEqual(res[0]["winner"], "worst")

    def test_zero_dollar_bids_tiebreak(self):
        eng = _eng()
        eng.submit_bid("best", 1, "fa1", 0, drop_player_id="b0")
        eng.submit_bid("mid", 1, "fa1", 0, drop_player_id="m0")
        res = eng.run_week(1, STANDINGS)
        # reverse standings: mid beats best
        self.assertEqual(res[0]["winner"], "mid")
        self.assertEqual(eng.get_budget("mid"), 100)

    def test_blind_no_cross_team_reads(self):
        eng = _eng()
        eng.submit_bid("best", 1, "fa1", 42, drop_player_id="b0")
        # worst sees only its own bids
        self.assertEqual(eng.get_bids("worst", 1), {})


class TestBudget(unittest.TestCase):
    def test_over_budget_bid_rejected_at_submit(self):
        eng = _eng(budget=100)
        with self.assertRaises(OverBudget):
            eng.submit_bid("best", 1, "fa1", 101, drop_player_id="b0")

    def test_unaffordable_win_forfeits_to_next_bidder(self):
        eng = _eng(budget=100)
        # worst wins fa1 for 90, then can't afford its 30 bid on fa2.
        eng.submit_bid("worst", 1, "fa1", 90, drop_player_id="w0")
        eng.submit_bid("worst", 1, "fa2", 30, drop_player_id="w1")
        eng.submit_bid("mid", 1, "fa2", 25, drop_player_id="m0")
        res = {r["player_id"]: r for r in eng.run_week(1, STANDINGS)}
        self.assertEqual(res["fa1"]["winner"], "worst")
        self.assertEqual(res["fa2"]["winner"], "mid")
        self.assertEqual(res["fa2"]["forfeited_by"], ["worst"])
        self.assertEqual(eng.get_budget("worst"), 10)


class TestFreeze(unittest.TestCase):
    def test_drop_freeze_blocks_reclaim_for_two_days(self):
        eng = _eng(now=NOW)
        eng.submit_bid("worst", 1, "fa1", 10, drop_player_id="w0")
        eng.run_week(1, STANDINGS, now=NOW)
        self.assertTrue(eng.is_frozen("w0", now=NOW))
        with self.assertRaises(FrozenPlayer):
            eng.submit_bid("best", 2, "w0", 5, drop_player_id="b0",
                           now=NOW + FREEZE_SECS - 1)
        # After the freeze lifts, the bid is accepted.
        bid = eng.submit_bid("best", 2, "w0", 5, drop_player_id="b0",
                             now=NOW + FREEZE_SECS + 1)
        self.assertEqual(bid["amount"], 5)
        self.assertFalse(eng.is_frozen("w0", now=NOW + FREEZE_SECS + 1))

    def test_dropped_player_returns_to_pool(self):
        eng = _eng()
        self.assertNotIn("w0", eng.pool)
        eng.submit_bid("worst", 1, "fa1", 10, drop_player_id="w0")
        eng.run_week(1, STANDINGS)
        self.assertIn("w0", eng.pool)
        self.assertNotIn("fa1", eng.pool)


class TestGuards(unittest.TestCase):
    def test_bid_after_run_closed(self):
        eng = _eng()
        eng.run_week(1, STANDINGS)
        with self.assertRaises(BidClosed):
            eng.submit_bid("best", 1, "fa1", 5, drop_player_id="b0")
        with self.assertRaises(WeekAlreadyRun):
            eng.run_week(1, STANDINGS)

    def test_unknown_and_offroster_drops(self):
        eng = _eng()
        with self.assertRaises(UnknownPlayer):
            eng.submit_bid("best", 1, "ghost", 5, drop_player_id="b0")
        with self.assertRaises(NotOnRoster):
            # w0 is the worst team's player, not best's.
            eng.submit_bid("best", 1, "fa1", 5, drop_player_id="w0")
        with self.assertRaises(UnknownTeam):
            eng.submit_bid("nope", 1, "fa1", 5, drop_player_id="b0")

    def test_drop_required(self):
        eng = _eng()
        with self.assertRaises(WaiverError):
            eng.submit_bid("best", 1, "fa1", 5, drop_player_id=None)

    def test_resubmit_overwrites_and_cancel(self):
        eng = _eng()
        eng.submit_bid("best", 1, "fa1", 10, drop_player_id="b0")
        eng.submit_bid("best", 1, "fa1", 15, drop_player_id="b1")
        bids = eng.get_bids("best", 1)
        self.assertEqual(bids["fa1"]["amount"], 15)
        self.assertEqual(bids["fa1"]["drop"], "b1")
        eng.cancel_bid("best", 1, "fa1")
        self.assertEqual(eng.get_bids("best", 1), {})
        res = eng.run_week(1, STANDINGS)
        self.assertEqual(res, [])


def _eng_sized(sizes, now=NOW, budget=100):
    """Engine whose teams have explicit roster sizes (P4-W26)."""
    teams = {}
    for tid, n in sizes.items():
        prefix = tid[0]
        teams[tid] = [f"{prefix}{i}" for i in range(n)]
    pool = ["fa1", "fa2", "fa3", "fa4"]
    return WaiverEngine(teams, pool, budget=budget, clock=lambda: now)


class TestNoDropFill(unittest.TestCase):
    """P4-W26: rosters are 15-man (D7) but the draft fills only 14,
    so a no-drop claim must be allowed while a team is under 15 and
    still required at a full 15."""

    def test_no_drop_claim_accepted_and_fills_open_spot_at_run(self):
        eng = _eng_sized({"best": 15, "mid": 15, "worst": 14})
        bid = eng.submit_bid("worst", 1, "fa1", 12)  # no drop named
        self.assertIsNone(bid["drop"])
        res = eng.run_week(1, STANDINGS)
        r = res[0]
        self.assertEqual(r["winner"], "worst")
        self.assertEqual(r["amount"], 12)
        self.assertIsNone(r["drop"])
        self.assertEqual(r["forfeited_by"], [])
        roster = eng.get_roster("worst")
        self.assertEqual(len(roster), 15)          # 14 -> 15, filled
        self.assertIn("fa1", roster)
        self.assertNotIn("fa1", eng.pool)
        self.assertEqual(eng.get_budget("worst"), 88)
        # Nobody was dropped, so nobody is frozen or returned to pool.
        self.assertFalse(any(eng.is_frozen(f"w{i}", now=NOW)
                             for i in range(14)))

    def test_no_drop_claim_rejected_at_full_15(self):
        eng = _eng_sized({"best": 15, "mid": 15, "worst": 15})
        with self.assertRaises(WaiverError):
            eng.submit_bid("worst", 1, "fa1", 5)  # no drop, roster full

    def test_swap_with_drop_still_works_when_under_15(self):
        eng = _eng_sized({"best": 15, "mid": 15, "worst": 14})
        eng.submit_bid("worst", 1, "fa1", 10, drop_player_id="w0")
        res = eng.run_week(1, STANDINGS)
        self.assertEqual(res[0]["winner"], "worst")
        self.assertEqual(res[0]["drop"], "w0")
        roster = eng.get_roster("worst")
        self.assertEqual(len(roster), 14)          # swap: size unchanged
        self.assertIn("fa1", roster)
        self.assertNotIn("w0", roster)
        self.assertIn("w0", eng.pool)
        self.assertTrue(eng.is_frozen("w0", now=NOW))

    def test_second_no_drop_claim_forfeits_once_spot_fills(self):
        # A 14-man team names no drop on two claims; winning the first
        # fills it to 15, so its second no-drop claim must forfeit at
        # settlement to the next bidder rather than exceed the cap.
        eng = _eng_sized({"best": 15, "mid": 14, "worst": 14})
        eng.submit_bid("worst", 1, "fa1", 50)
        eng.submit_bid("worst", 1, "fa2", 40)
        eng.submit_bid("mid", 1, "fa2", 30)
        res = {r["player_id"]: r for r in eng.run_week(1, STANDINGS)}
        self.assertEqual(res["fa1"]["winner"], "worst")
        self.assertEqual(len(eng.get_roster("worst")), 15)
        self.assertEqual(res["fa2"]["winner"], "mid")
        self.assertEqual(res["fa2"]["forfeited_by"], ["worst"])
        self.assertEqual(len(eng.get_roster("mid")), 15)


class TestMultiWeek(unittest.TestCase):
    def test_multi_week_independence(self):
        eng = _eng()
        eng.submit_bid("best", 1, "fa1", 10, drop_player_id="b0")
        eng.run_week(1, STANDINGS)
        eng.submit_bid("best", 2, "fa2", 20, drop_player_id="b1")
        res = eng.run_week(2, STANDINGS)
        self.assertEqual(res[0]["winner"], "best")
        self.assertEqual(eng.get_budget("best"), 70)


class TestJsonContract(unittest.TestCase):
    def test_json_roundtrip(self):
        eng = _eng(now=NOW)
        eng.submit_bid("worst", 1, "fa1", 30, drop_player_id="w0", now=NOW)
        eng.run_week(1, STANDINGS, now=NOW)
        eng2 = WaiverEngine.from_dict(eng.to_dict())
        json.dumps(eng.to_dict())
        self.assertEqual(eng2.get_budget("worst"), 70)
        self.assertEqual(eng2.get_roster("worst"), eng.get_roster("worst"))
        self.assertTrue(eng2.is_frozen("w0", now=NOW))
        self.assertEqual(eng2.get_run(1), eng.get_run(1))

    def test_json_roundtrip_with_pending_bids_int_ids(self):
        """P4-W24 regression: a bid persisted via JSON (the server
        restart path) must revive with (int, int) bid keys and int
        player ids — a str team id made the revived bid invisible to
        int-id lookups, and the service layer's duplicate
        re-normalization crashed on the tuple keys outright."""
        teams = {9: list(range(1, 16)), 10: list(range(16, 31))}
        eng = WaiverEngine(teams, [41, 42], budget=100, clock=lambda: NOW)
        eng.submit_bid(9, 1, 41, 12, drop_player_id=3, now=NOW)
        state = json.loads(json.dumps(eng.to_dict()))
        eng2 = WaiverEngine.from_dict(state)
        bids = eng2.get_bids(9, 1)
        self.assertEqual(list(bids), [41])
        self.assertEqual(bids[41]["amount"], 12)
        res = eng2.run_week(1, [10, 9], now=NOW)
        self.assertEqual(res[0]["winner"], 9)
        self.assertIn(41, eng2.get_roster(9))
        self.assertNotIn(3, eng2.get_roster(9))


if __name__ == "__main__":
    unittest.main()
