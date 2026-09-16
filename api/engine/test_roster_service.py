"""Tests for roster_service.py — hand-derived, not snapshots of the code.

D7 slot model (Smit ruling 2026-09-15): 15-man rosters = 11 starters
(WK1 BAT3 AR2 BOWL3 UTIL2) + BN3 + IL1. D8: max 4 overseas starters.

IL rule (Smit 2026-09-15, single tier, no IL+):
- IL is NEVER filled during the draft (no direct-to-IL picks). The
  14-man draft output has an empty IL slot.
- Injured players may be drafted but occupy a normal roster spot.
- Post-draft, a player who has missed or is expected to miss a game is
  IL-eligible. Only IL-eligible players may occupy IL.
- Moving an IL-eligible player to IL frees a roster spot (add_player).

Plain unittest, stdlib only. Run:  python3 test_roster_service.py
"""

import json
import unittest

from api.engine.roster_service import (
    ACTIVE_ROSTER_CAP,
    ROSTER_SIZE,
    STARTERS_TOTAL,
    SLOT_CAPACITY,
    DuplicatePlayer,
    ILIneligible,
    IneligibleSlot,
    IncompleteLineup,
    LineupError,
    LineupLocked,
    LineupService,
    OverseasCapViolated,
    RoleMetadataMissing,
    SlotOverflow,
    UnknownPlayer,
    UnknownTeam,
    MAX_OVERSEAS_STARTERS,
)

NOW = 1_000_000.0


def _roles():
    # 15 players. Overseas: b1, b2, a1, o1 (4). o5 is the 5th overseas
    # (cap-breaker). b6 is the IL-eligible player (missed a game).
    return {
        "w1": {"role": "WK",   "is_overseas": False},
        "b1": {"role": "BAT",  "is_overseas": True},
        "b2": {"role": "BAT",  "is_overseas": True},
        "b3": {"role": "BAT",  "is_overseas": False},
        "b4": {"role": "BAT",  "is_overseas": False},
        "b5": {"role": "BAT",  "is_overseas": False},
        "b6": {"role": "BAT",  "is_overseas": False},  # IL-eligible
        "a1": {"role": "AR",   "is_overseas": True},
        "a2": {"role": "AR",   "is_overseas": False},
        "a3": {"role": "AR",   "is_overseas": False},
        "o1": {"role": "BOWL", "is_overseas": True},
        "o2": {"role": "BOWL", "is_overseas": False},
        "o3": {"role": "BOWL", "is_overseas": False},
        "o4": {"role": "BOWL", "is_overseas": False},
        "o5": {"role": "BOWL", "is_overseas": True},    # cap-breaker
    }


def _draft_roster():
    # 14-man draft output (IL never draft-filled): everyone but b6.
    return ["w1", "b1", "b2", "b3", "b4", "b5",
            "a1", "a2", "a3", "o1", "o2", "o3", "o4", "o5"]


def _roster_with_b6():
    # 14-man roster containing the IL-eligible player instead of o5.
    return [p for p in _draft_roster() if p != "o5"] + ["b6"]


def _roster15():
    # 15-man roster: draft output + b6 (IL slot still empty until moved).
    return _draft_roster() + ["b6"]


def _svc(roster, il_eligible=(), now=NOW):
    roles = _roles()
    return LineupService({"t1": list(roster), "t2": list(roster)}, roles,
                         il_eligible=set(il_eligible),
                         clock=lambda: now)


def _valid():
    # 11 starters, exactly 4 overseas (b1,b2,a1,o1); BN x3; IL empty.
    return {
        "w1": "WK",
        "b1": "BAT", "b2": "BAT", "b3": "BAT",
        "a1": "AR", "a2": "AR",
        "o1": "BOWL", "o2": "BOWL", "o3": "BOWL",
        "b4": "UTIL", "o4": "UTIL",          # second UTIL slot (D7 ruling)
        "b5": "BN", "a3": "BN", "o5": "BN",  # BN x3
    }


def _valid_with_b6():
    # _valid() with o5 swapped for b6 (14-man roster incl. eligible b6).
    v = dict(_valid())
    del v["o5"]
    v["b6"] = "BN"
    return v


class TestSlotModel(unittest.TestCase):
    def test_happy_path_14_man_roster(self):
        svc = _svc(_draft_roster())
        out = svc.set_lineup("t1", 1, _valid(), lock_deadline=2_000_000.0,
                             now=NOW)
        self.assertEqual(len(out["starters"]), 11)
        self.assertEqual(len(out["starters"]), STARTERS_TOTAL)
        self.assertEqual(out["overseas_starters"], 4)
        self.assertEqual(out["overseas_starters"], MAX_OVERSEAS_STARTERS)
        self.assertFalse(out["locked"])
        starters = svc.get_starters("t1", 1)
        self.assertEqual(set(starters),
                         {"w1", "b1", "b2", "b3", "a1", "a2",
                          "o1", "o2", "o3", "b4", "o4"})

    def test_il_empty_post_draft(self):
        # The 14-man draft output has an empty IL slot — valid state.
        svc = _svc(_draft_roster())
        self.assertIsNone(svc.get_il("t1"))
        self.assertEqual(svc.active_count("t1"), 14)
        self.assertEqual(svc.active_count("t1"), ACTIVE_ROSTER_CAP)
        svc.set_lineup("t1", 1, _valid(), now=NOW)  # no IL assignment needed

    def test_util_capacity_two(self):
        bad = dict(_valid())
        bad["b5"] = "UTIL"  # third UTIL (b4, o4 already there)
        with self.assertRaises(SlotOverflow):
            _svc(_draft_roster()).set_lineup("t1", 1, bad, now=NOW)

    def test_bn_capacity_three(self):
        bad = dict(_valid())
        bad["b4"] = "BN"  # fourth BN (b5, a3, o5 already there)
        with self.assertRaises(SlotOverflow):
            _svc(_draft_roster()).set_lineup("t1", 1, bad, now=NOW)

    def test_bat_capacity_three(self):
        bad = dict(_valid())
        bad["b5"] = "BAT"  # fourth BAT (b1, b2, b3 already there)
        with self.assertRaises(SlotOverflow):
            _svc(_draft_roster()).set_lineup("t1", 1, bad, now=NOW)

    def test_overseas_cap_eleven_starters(self):
        # o5 (5th overseas) starts over o2 -> 5 overseas starters.
        bad = dict(_valid())
        bad["o5"] = "BOWL"
        bad["o2"] = "BN"
        with self.assertRaises(OverseasCapViolated):
            _svc(_draft_roster()).set_lineup("t1", 1, bad, now=NOW)

    def test_overseas_on_bench_does_not_count(self):
        # o5 is overseas but on BN in _valid() — the 4-starter cap holds.
        svc = _svc(_draft_roster())
        out = svc.set_lineup("t1", 1, _valid(), now=NOW)
        self.assertEqual(out["overseas_starters"], 4)

    def test_wk_cannot_util(self):
        bad = dict(_valid())
        bad["w1"] = "UTIL"
        bad["b5"] = "BN"
        with self.assertRaises(IneligibleSlot):
            _svc(_draft_roster()).set_lineup("t1", 1, bad, now=NOW)

    def test_backup_wk_may_sit_on_bench(self):
        # P2-L7 sandbox integration finding: the draft engine benches a
        # second WK as overflow; the lineup service must accept that
        # roster (BN is inactive — any role may sit there).
        roles = _roles()
        roles["w2"] = {"role": "WK", "is_overseas": False}
        roster = [p for p in _draft_roster() if p != "o5"] + ["w2"]
        svc = LineupService({"t1": roster}, roles, clock=lambda: NOW)
        ok = dict(_valid())
        del ok["o5"]
        ok["w2"] = "BN"
        svc.set_lineup("t1", 1, ok, now=NOW)  # must not raise
        self.assertEqual(len(svc.get_starters("t1", 1)), 11)

    def test_bat_cannot_wk_slot(self):
        bad = dict(_valid())
        bad["w1"] = "BN"
        bad["b3"] = "WK"
        with self.assertRaises(IneligibleSlot):
            _svc(_draft_roster()).set_lineup("t1", 1, bad, now=NOW)

    def test_ar_can_util(self):
        alt = dict(_valid())
        alt["o4"] = "BN"
        alt["a3"] = "UTIL"  # AR into the second UTIL slot
        svc = _svc(_draft_roster())
        out = svc.set_lineup("t1", 1, alt, now=NOW)
        self.assertEqual(len(out["starters"]), 11)

    def test_slot_capacities_match_d7(self):
        self.assertEqual(SLOT_CAPACITY,
                         {"WK": 1, "BAT": 3, "AR": 2, "BOWL": 3,
                          "UTIL": 2, "BN": 3, "IL": 1})
        self.assertEqual(ROSTER_SIZE, 15)

    def test_roster_size_bounds(self):
        roles = _roles()
        with self.assertRaises(LineupError):  # 13 too few
            LineupService({"t1": _draft_roster()[:13]}, roles)
        with self.assertRaises(LineupError):  # 16 too many
            LineupService({"t1": _draft_roster() + ["b6", "x1"]},
                          {**roles, "x1": {"role": "BAT",
                                           "is_overseas": False}})
        LineupService({"t1": _draft_roster()}, roles)       # 14 ok
        LineupService({"t1": _roster15()}, roles)            # 15 ok

    def test_unknown_role_fails_closed(self):
        roles = _roles()
        del roles["b4"]["role"]
        svc = LineupService({"t1": _draft_roster()}, roles,
                            clock=lambda: NOW)
        with self.assertRaises(RoleMetadataMissing):
            svc.set_lineup("t1", 1, _valid(), now=NOW)

    def test_unknown_team(self):
        with self.assertRaises(UnknownTeam):
            _svc(_draft_roster()).set_lineup("nope", 1, _valid(), now=NOW)

    def test_unknown_player(self):
        with self.assertRaises(UnknownPlayer):
            _svc(_draft_roster()).set_lineup(
                "t1", 1, {**_valid(), "ghost": "BN"}, now=NOW)

    def test_incomplete_lineup_rejected(self):
        partial = {k: v for k, v in _valid().items() if k != "b5"}
        with self.assertRaises(IncompleteLineup):
            _svc(_draft_roster()).set_lineup("t1", 1, partial, now=NOW)


class TestILRule(unittest.TestCase):
    """Smit's IL rule (2026-09-15): single tier, no IL+."""

    def test_il_placement_requires_eligibility(self):
        # b6 on the roster but NOT designated IL-eligible -> IL rejected.
        svc = _svc(_roster15(), il_eligible=())
        with self.assertRaises(ILIneligible):
            svc.set_lineup("t1", 1, {**_valid(), "b6": "IL"}, now=NOW)

    def test_eligible_player_may_stay_in_normal_spot(self):
        # IL-eligible b6 drafted into a normal roster spot (BN), IL empty.
        svc = _svc(_roster_with_b6(), il_eligible={"b6"})
        out = svc.set_lineup("t1", 1, _valid_with_b6(), now=NOW)
        self.assertEqual(len(out["starters"]), 11)
        self.assertIsNone(svc.get_il("t1"))

    def test_move_to_il_requires_eligibility(self):
        svc = _svc(_roster_with_b6(), il_eligible=())
        with self.assertRaises(ILIneligible):
            svc.move_to_il("t1", "b6")

    def test_move_to_il_unknown_player(self):
        svc = _svc(_roster_with_b6(), il_eligible={"ghost"})
        with self.assertRaises(UnknownPlayer):
            svc.move_to_il("t1", "ghost")

    def test_move_to_il_frees_spot_then_add(self):
        # The Yahoo-style flow: draft 14 -> injury -> IL -> add replacement.
        svc = _svc(_roster_with_b6(), il_eligible={"b6"})
        res = svc.move_to_il("t1", "b6")
        self.assertEqual(res["active_count"], 13)
        self.assertEqual(svc.get_il("t1"), "b6")
        res = svc.add_player("t1", "fa1",
                             {"role": "BAT", "is_overseas": False})
        self.assertEqual(res["roster_size"], 15)
        self.assertEqual(svc.active_count("t1"), 14)
        # Weekly lineup: b6 must sit in IL; fa1 takes the freed BN spot.
        assignments = {k: ("IL" if k == "b6" else v)
                       for k, v in _valid_with_b6().items()}
        assignments["fa1"] = "BN"
        out = svc.set_lineup("t1", 1, assignments, now=NOW)
        self.assertEqual(len(out["starters"]), 11)
        self.assertEqual(out["overseas_starters"], 4)

    def test_add_player_refused_when_no_free_spot(self):
        # 14 active, nobody on IL -> no room to add.
        svc = _svc(_draft_roster())
        with self.assertRaises(LineupError):
            svc.add_player("t1", "fa1",
                           {"role": "BAT", "is_overseas": False})

    def test_add_player_refused_when_roster_full(self):
        # 15 rostered (14 active + nobody moved) -> roster is full.
        svc = _svc(_roster15())
        with self.assertRaises(LineupError):
            svc.add_player("t1", "fa1",
                           {"role": "BAT", "is_overseas": False})

    def test_add_player_duplicate_rejected(self):
        svc = _svc(_roster_with_b6(), il_eligible={"b6"})
        svc.move_to_il("t1", "b6")
        with self.assertRaises(DuplicatePlayer):
            svc.add_player("t1", "b6",
                           {"role": "BAT", "is_overseas": False})

    def test_add_player_requires_role_metadata(self):
        svc = _svc(_roster_with_b6(), il_eligible={"b6"})
        svc.move_to_il("t1", "b6")
        with self.assertRaises(RoleMetadataMissing):
            svc.add_player("t1", "fa1", {})

    def test_il_assignment_must_match_roster_state(self):
        # After move_to_il, the weekly assignment must place b6 in IL.
        svc = _svc(_roster_with_b6(), il_eligible={"b6"})
        svc.move_to_il("t1", "b6")
        with self.assertRaises(ILIneligible):
            svc.set_lineup("t1", 1, _valid_with_b6(), now=NOW)  # b6 on BN

    def test_il_single_tier_cap_one(self):
        svc = _svc(_roster15(), il_eligible={"b6", "o5"})
        svc.move_to_il("t1", "b6")
        with self.assertRaises(SlotOverflow):  # no IL+ : second IL move refused
            svc.move_to_il("t1", "o5")

    def test_il_player_never_counts_as_starter(self):
        svc = _svc(_roster_with_b6(), il_eligible={"b6"})
        svc.move_to_il("t1", "b6")
        assignments = {k: ("IL" if k == "b6" else v)
                       for k, v in _valid_with_b6().items()}
        svc.set_lineup("t1", 1, assignments, now=NOW)
        starters = svc.get_starters("t1", 1)
        self.assertEqual(len(starters), 11)
        self.assertNotIn("b6", starters)

    def test_set_il_eligible_updates_designation(self):
        svc = _svc(_draft_roster())
        self.assertEqual(svc.set_il_eligible(["o5"]), {"o5"})
        # o5 (missed a game per the feed) can now go to IL.
        svc.move_to_il("t1", "o5")
        self.assertEqual(svc.get_il("t1"), "o5")
        # ...and back off when the feed clears him.
        svc.set_il_eligible([])
        self.assertEqual(svc.il_eligible, set())

    def test_activate_from_il(self):
        svc = _svc(_roster_with_b6(), il_eligible={"b6"})
        svc.move_to_il("t1", "b6")
        self.assertEqual(svc.active_count("t1"), 13)
        res = svc.activate_from_il("t1")
        self.assertEqual(res["activated"], "b6")
        self.assertIsNone(svc.get_il("t1"))
        self.assertEqual(svc.active_count("t1"), 14)

    def test_activate_from_il_refused_when_active_full(self):
        # 15 rostered, b6 moved to IL (14 active) -> must drop first.
        svc = _svc(_roster15(), il_eligible={"b6"})
        svc.move_to_il("t1", "b6")
        self.assertEqual(svc.active_count("t1"), 14)
        with self.assertRaises(LineupError):
            svc.activate_from_il("t1")

    def test_activate_from_il_empty(self):
        svc = _svc(_draft_roster())
        with self.assertRaises(LineupError):
            svc.activate_from_il("t1")


class TestLockAndReads(unittest.TestCase):
    def test_lock_freezes_lineup(self):
        svc = _svc(_draft_roster())
        svc.set_lineup("t1", 1, _valid(), lock_deadline=2_000_000.0, now=NOW)
        svc.lock("t1", 1, now=1_100_000.0)
        self.assertTrue(svc.is_locked("t1", 1))
        with self.assertRaises(LineupLocked):
            svc.set_lineup("t1", 1, _valid(), now=1_200_000.0)

    def test_lock_requires_submission(self):
        svc = _svc(_draft_roster())
        with self.assertRaises(LineupError):
            svc.lock("t1", 1, now=NOW)

    def test_deadline_freezes_unlocked_lineup(self):
        svc = _svc(_draft_roster())
        svc.set_lineup("t1", 1, _valid(), lock_deadline=1_500_000.0, now=NOW)
        with self.assertRaises(LineupLocked):
            svc.set_lineup("t1", 1, _valid(), now=1_600_000.0)
        self.assertTrue(svc.is_locked("t1", 1, now=1_600_000.0))

    def test_resubmit_before_deadline_ok(self):
        svc = _svc(_draft_roster())
        svc.set_lineup("t1", 1, _valid(), lock_deadline=2_000_000.0, now=NOW)
        alt = dict(_valid())
        alt["b4"], alt["b5"] = "BN", "UTIL"  # swap the UTIL/BN BATs
        out = svc.set_lineup("t1", 1, alt, now=1_100_000.0)
        self.assertEqual(out["overseas_starters"], 4)

    def test_deadline_is_sticky(self):
        svc = _svc(_draft_roster())
        svc.set_lineup("t1", 1, _valid(), lock_deadline=1_500_000.0, now=NOW)
        with self.assertRaises(LineupLocked):
            svc.set_lineup("t1", 1, _valid(), lock_deadline=3_000_000.0,
                           now=1_600_000.0)

    def test_missing_lineup_teams(self):
        svc = _svc(_draft_roster())
        svc.set_lineup("t1", 1, _valid(), now=NOW)
        self.assertEqual(svc.teams_missing_lineup(1), ["t2"])
        self.assertIsNone(svc.get_lineup("t2", 1))
        self.assertIsNone(svc.get_starters("t2", 1))

    def test_json_roundtrip_with_il_state(self):
        svc = _svc(_roster_with_b6(), il_eligible={"b6"})
        svc.move_to_il("t1", "b6")
        assignments = {k: ("IL" if k == "b6" else v)
                       for k, v in _valid_with_b6().items()}
        svc.set_lineup("t1", 1, assignments, lock_deadline=2_000_000.0,
                       now=NOW)
        svc.lock("t1", 1, now=1_100_000.0)
        svc2 = LineupService.from_dict(svc.to_dict(), _roles())
        self.assertEqual(svc2.get_lineup("t1", 1), svc.get_lineup("t1", 1))
        self.assertEqual(svc2.get_il("t1"), "b6")
        self.assertEqual(svc2.il_eligible, {"b6"})
        self.assertTrue(svc2.is_locked("t1", 1, now=1_200_000.0))
        self.assertEqual(svc2.get_starters("t1", 1),
                         svc.get_starters("t1", 1))
        json.dumps(svc.to_dict())  # must be JSON-serializable


if __name__ == "__main__":
    unittest.main()
