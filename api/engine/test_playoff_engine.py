"""Tests for playoff_engine.py — hand-derived, not snapshots of the code.

D9: top-4 playoffs, weeks 7–8 (semis + final). Consolation: week-7 5v6,
week-8 3rd-place game. Tie -> higher regular-season seed advances.

Plain unittest, stdlib only. Run:  python3 test_playoff_engine.py
"""

import json
import unittest

from api.engine.playoff_engine import (
    BadSeeds,
    BracketNotReady,
    MissingWeeklyTotal,
    PlayoffBracket,
    PlayoffConfig,
    PlayoffError,
    UnknownTeam,
    WeekAlreadyFinal,
    WeekOutOfRange,
)

NAMES = (("s1", "Alpha"), ("s2", "Bravo"), ("s3", "Charlie"),
         ("s4", "Delta"), ("s5", "Echo"), ("s6", "Foxtrot"))


def _bracket(reseed=False, consolation=("s5", "s6")):
    return PlayoffBracket(
        PlayoffConfig(seeds=("s1", "s2", "s3", "s4"),
                      consolation=consolation,
                      reseed=reseed,
                      team_names=NAMES),
        clock=lambda: 1_000_000.0)


def _week7_points(**over):
    pts = {"s1": 100.0, "s2": 100.0, "s3": 110.0,
           "s4": 90.0, "s5": 80.0, "s6": 70.0}
    pts.update(over)
    return pts


class TestBracketConstruction(unittest.TestCase):
    def test_semifinal_pairings_fixed(self):
        b = _bracket()
        self.assertEqual(b.semifinal_pairings(), [("s1", "s4"), ("s2", "s3")])

    def test_consolation_pairing(self):
        self.assertEqual(_bracket().consolation_pairings(), [("s5", "s6")])
        self.assertEqual(_bracket(consolation=()).consolation_pairings(), [])

    def test_bad_seeds_rejected(self):
        with self.assertRaises(BadSeeds):
            PlayoffBracket(PlayoffConfig(seeds=("s1", "s2", "s3")))
        with self.assertRaises(BadSeeds):
            PlayoffBracket(PlayoffConfig(seeds=("s1", "s2", "s3", "s3")))
        with self.assertRaises(BadSeeds):
            PlayoffBracket(PlayoffConfig(seeds=("s1", "s2", "s3", "s4"),
                                         consolation=("s4", "s6")))
        with self.assertRaises(BadSeeds):
            PlayoffBracket(PlayoffConfig(seeds=("s1", "s2", "s3", "s4"),
                                         consolation=("s5",)))

    def test_champion_none_before_final(self):
        b = _bracket()
        self.assertIsNone(b.champion())
        b.record_week(7, _week7_points())
        self.assertIsNone(b.champion())  # week 8 not recorded yet


class TestWeekRecording(unittest.TestCase):
    def test_week7_final_pairing(self):
        b = _bracket()
        b.record_week(7, _week7_points())  # s1 beats s4; s3 beats s2
        self.assertEqual(b.final_pairings(),
                         [("s1", "s3"), ("s4", "s2")])

    def test_week8_before_week7_rejected(self):
        b = _bracket()
        with self.assertRaises(BracketNotReady):
            b.record_week(8, {"s1": 1.0, "s3": 2.0, "s4": 3.0, "s2": 4.0})

    def test_non_playoff_weeks_rejected(self):
        b = _bracket()
        with self.assertRaises(WeekOutOfRange):
            b.record_week(6, _week7_points())
        with self.assertRaises(WeekOutOfRange):
            b.record_week(9, _week7_points())  # defined week, not playoff
        with self.assertRaises(WeekOutOfRange):
            b.record_week(99, _week7_points())

    def test_missing_total_fail_closed(self):
        b = _bracket()
        pts = _week7_points()
        del pts["s6"]
        with self.assertRaises(MissingWeeklyTotal):
            b.record_week(7, pts)

    def test_unknown_team_in_points(self):
        b = _bracket()
        pts = _week7_points()
        pts["ghost"] = 50.0
        with self.assertRaises(UnknownTeam):
            b.record_week(7, pts)

    def test_double_record_rejected(self):
        b = _bracket()
        b.record_week(7, _week7_points())
        with self.assertRaises(WeekAlreadyFinal):
            b.record_week(7, _week7_points())

    def test_zero_is_valid_score(self):
        b = _bracket()
        pts = {t: 0.0 for t in ("s1", "s2", "s3", "s4", "s5", "s6")}
        rec = b.record_week(7, pts)  # all ties -> higher seeds advance
        winners = {m["winner"] for m in rec["matchups"]}
        self.assertEqual(winners, {"s1", "s2", "s5"})

    def test_negative_total_rejected(self):
        b = _bracket()
        with self.assertRaises(PlayoffError):
            b.record_week(7, _week7_points(s1=-5.0))


class TestOutcomes(unittest.TestCase):
    def _played(self):
        b = _bracket()
        b.record_week(7, _week7_points())
        # Final: s3 upsets s1. 3rd-place: s2 beats s4.
        b.record_week(8, {"s1": 110.0, "s3": 120.0,
                          "s4": 100.0, "s2": 105.0})
        return b

    def test_champion_upset(self):
        self.assertEqual(self._played().champion(), "s3")

    def test_placements_full(self):
        # 1st s3 (upset), 2nd s1, 3rd s2, 4th s4, 5th s5, 6th s6.
        self.assertEqual(self._played().placements(),
                         {1: "s3", 2: "s1", 3: "s2",
                          4: "s4", 5: "s5", 6: "s6"})

    def test_placements_require_week8(self):
        b = _bracket()
        b.record_week(7, _week7_points())
        with self.assertRaises(BracketNotReady):
            b.placements()

    def test_placements_no_consolation(self):
        b = _bracket(consolation=())
        week7 = {t: v for t, v in _week7_points().items()
                 if t not in ("s5", "s6")}
        b.record_week(7, week7)
        b.record_week(8, {"s1": 110.0, "s3": 120.0,
                          "s4": 100.0, "s2": 105.0})
        self.assertEqual(b.placements(),
                         {1: "s3", 2: "s1", 3: "s2", 4: "s4"})

    def test_tie_goes_to_higher_seed(self):
        b = _bracket()
        # s1v4 tied -> s1 advances; s2v3 tied -> s2 advances.
        b.record_week(7, _week7_points(s1=100.0, s4=100.0,
                                      s2=105.0, s3=105.0,
                                      s5=70.0, s6=70.0))
        self.assertEqual(b.final_pairings(),
                         [("s1", "s2"), ("s4", "s3")])

    def test_final_tie_higher_seed_champion(self):
        b = _bracket()
        b.record_week(7, _week7_points())
        b.record_week(8, {"s1": 115.0, "s3": 115.0,
                          "s4": 100.0, "s2": 105.0})
        self.assertEqual(b.champion(), "s1")  # s1 outranks s3

    def test_reseed_orders_higher_seed_first(self):
        # Upsets: s4 beats s1, s3 beats s2.
        pts = _week7_points(s1=80.0, s4=120.0, s2=90.0, s3=130.0)
        plain = _bracket(reseed=False)
        plain.record_week(7, pts)
        self.assertEqual(plain.final_pairings(),
                         [("s4", "s3"), ("s1", "s2")])
        reseeded = _bracket(reseed=True)
        reseeded.record_week(7, pts)
        # Same teams meet (pairing-neutral for 4 teams), higher seed first.
        self.assertEqual(reseeded.final_pairings(),
                         [("s3", "s4"), ("s1", "s2")])


class TestJsonContract(unittest.TestCase):
    def test_roundtrip_mid_playoffs(self):
        b = _bracket()
        b.record_week(7, _week7_points())
        b2 = PlayoffBracket.from_dict(b.to_dict(), clock=lambda: 2_000_000.0)
        self.assertEqual(b2.final_pairings(), b.final_pairings())
        b2.record_week(8, {"s1": 110.0, "s3": 120.0,
                           "s4": 100.0, "s2": 105.0})
        self.assertEqual(b2.placements(),
                         {1: "s3", 2: "s1", 3: "s2",
                          4: "s4", 5: "s5", 6: "s6"})
        json.dumps(b.to_dict())  # must be JSON-serializable


if __name__ == "__main__":
    unittest.main()
