"""Tests for matchup_scheduler.py — hand-derived scenarios.

Plain unittest, stdlib only. Run:  python3 test_matchup_scheduler.py

All expected pairings below are hand-computed from the circle method:
with order [A,B,C,D,E,F], round r pairs (order[i], order[n-1-i]) and the
rotation keeps the first fixed and moves the last to position 1.
"""

import random
import unittest

from api.engine.matchup_scheduler import (
    FANTASY_WEEKS,
    REGULAR_SEASON_WEEKS,
    ScheduleConfig,
    Season,
    WeekAlreadyFinal,
    WeekNotFinalized,
    WeekOutOfRange,
    DuplicateTeam,
    MissingWeeklyTotal,
    OddTeamCount,
    ScheduleError,
    UnknownTeam,
    generate_schedule,
    week_dates,
)


def _cfg6(order=("A", "B", "C", "D", "E", "F"), seed=42):
    teams = tuple((t, f"Team {t}") for t in order)
    return ScheduleConfig(teams=teams, seed=seed, team_order=tuple(order))


def _cfg4(order=("A", "B", "C", "D"), seed=42):
    teams = tuple((t, f"Team {t}") for t in order)
    return ScheduleConfig(teams=teams, seed=seed, team_order=tuple(order))


class TestScheduleGeneration(unittest.TestCase):
    def test_round_robin_pairings_hand_derived(self):
        sched = generate_schedule(_cfg6())
        # Hand-computed circle-method rounds for [A,B,C,D,E,F].
        self.assertEqual(sched[1], [("A", "F"), ("B", "E"), ("C", "D")])
        self.assertEqual(sched[2], [("A", "E"), ("F", "D"), ("B", "C")])
        self.assertEqual(sched[3], [("A", "D"), ("E", "C"), ("F", "B")])
        self.assertEqual(sched[4], [("A", "C"), ("D", "B"), ("E", "F")])
        self.assertEqual(sched[5], [("A", "B"), ("C", "F"), ("D", "E")])

    def test_week_6_replays_week_1_rivalry_week(self):
        sched = generate_schedule(_cfg6())
        self.assertEqual(sched[6], sched[1])
        self.assertNotEqual(sched[6], sched[2])

    def test_every_pair_meets_exactly_once_in_round_robin(self):
        sched = generate_schedule(_cfg6())
        seen = set()
        for week in (1, 2, 3, 4, 5):
            for a, b in sched[week]:
                self.assertNotEqual(a, b, "no team plays itself")
                pair = frozenset((a, b))
                self.assertNotIn(pair, seen, f"duplicate pairing {pair}")
                seen.add(pair)
        self.assertEqual(len(seen), 15)  # C(6,2)

    def test_each_team_plays_once_per_week(self):
        sched = generate_schedule(_cfg6())
        for week in REGULAR_SEASON_WEEKS:
            flat = [t for pair in sched[week] for t in pair]
            self.assertEqual(sorted(flat), ["A", "B", "C", "D", "E", "F"])

    def test_four_team_schedule(self):
        sched = generate_schedule(_cfg4())
        self.assertEqual(sched[1], [("A", "D"), ("B", "C")])
        self.assertEqual(sched[2], [("A", "C"), ("D", "B")])
        self.assertEqual(sched[3], [("A", "B"), ("C", "D")])
        # Weeks 4-6 are past the 3-round robin: replay round 1.
        self.assertEqual(sched[4], sched[1])
        self.assertEqual(sched[5], sched[1])
        self.assertEqual(sched[6], sched[1])

    def test_odd_team_count_raises(self):
        teams = tuple((t, f"Team {t}") for t in "ABCDE")
        with self.assertRaises(OddTeamCount):
            generate_schedule(ScheduleConfig(teams=teams, team_order=tuple("ABCDE")))
        with self.assertRaises(OddTeamCount):
            generate_schedule(ScheduleConfig(teams=(("A", "Team A"),),
                                             team_order=("A",)))

    def test_duplicate_team_raises(self):
        teams = (("A", "x"), ("A", "y"))
        with self.assertRaises(DuplicateTeam):
            generate_schedule(ScheduleConfig(teams=teams, team_order=("A", "A")))

    def test_team_order_must_be_permutation(self):
        with self.assertRaises(ScheduleError):
            generate_schedule(_cfg4(order=("A", "B", "C", "D")).__class__(
                teams=tuple((t, f"Team {t}") for t in "ABCD"),
                team_order=("A", "B", "C", "Z")))

    def test_seeded_shuffle_is_deterministic(self):
        teams = tuple((t, f"Team {t}") for t in "ABCDEF")
        c1 = ScheduleConfig(teams=teams, seed=7)
        c2 = ScheduleConfig(teams=teams, seed=7)
        self.assertEqual(c1.resolved_order(), c2.resolved_order())
        self.assertEqual(sorted(c1.resolved_order()), list("ABCDEF"))


class TestWeekDates(unittest.TestCase):
    def test_week_dates_hand_checked(self):
        self.assertEqual(week_dates(1), ("2027-03-08", "2027-03-14"))
        self.assertEqual(week_dates(6), ("2027-04-12", "2027-04-18"))
        self.assertEqual(week_dates(9), ("2027-05-03", "2027-05-09"))
        self.assertEqual(len(FANTASY_WEEKS), 9)

    def test_unknown_week_raises(self):
        with self.assertRaises(WeekOutOfRange):
            week_dates(10)
        with self.assertRaises(WeekOutOfRange):
            week_dates(0)


def _season4(seed=42, now=1_000_000.0):
    return Season(_cfg4(seed=seed), clock=lambda: now)


class TestRecordWeek(unittest.TestCase):
    def test_winners_and_tie_hand_derived(self):
        s = _season4(now=1234.5)
        rec = s.record_week(1, {"A": 100.0, "B": 90.0, "C": 90.0, "D": 50.0})
        by_pair = {(m["team_a"], m["team_b"]): m for m in rec["matchups"]}
        # Week 1 pairings are (A,D) and (B,C).
        self.assertEqual(by_pair[("A", "D")]["winner"], "A")
        self.assertEqual(by_pair[("A", "D")]["score_a"], 100.0)
        self.assertEqual(by_pair[("A", "D")]["score_b"], 50.0)
        self.assertIsNone(by_pair[("B", "C")]["winner"])  # 90-90 tie
        self.assertEqual(rec["status"], "final")
        self.assertEqual(rec["week_start"], "2027-03-08")
        self.assertEqual(rec["week_end"], "2027-03-14")
        self.assertEqual(rec["finalized_at"], 1234.5)
        self.assertEqual(s.finalized_weeks, [1])

    def test_zero_score_is_valid_d10(self):
        s = _season4()
        rec = s.record_week(1, {"A": 0.0, "B": 0.0, "C": 0.0, "D": 0.0})
        self.assertTrue(all(m["winner"] is None for m in rec["matchups"]))

    def test_missing_team_raises_fail_closed(self):
        s = _season4()
        with self.assertRaises(MissingWeeklyTotal):
            s.record_week(1, {"A": 100.0, "B": 90.0, "C": 90.0})  # no D

    def test_unknown_team_id_raises(self):
        s = _season4()
        totals = {"A": 100.0, "B": 90.0, "C": 90.0, "D": 50.0, "ZZZ": 10.0}
        with self.assertRaises(UnknownTeam):
            s.record_week(1, totals)

    def test_negative_score_raises(self):
        s = _season4()
        totals = {"A": -5.0, "B": 90.0, "C": 90.0, "D": 50.0}
        with self.assertRaises(ScheduleError):
            s.record_week(1, totals)

    def test_non_numeric_score_raises(self):
        s = _season4()
        totals = {"A": "100", "B": 90.0, "C": 90.0, "D": 50.0}
        with self.assertRaises(ScheduleError):
            s.record_week(1, totals)

    def test_bool_score_rejected(self):
        s = _season4()
        totals = {"A": True, "B": 90.0, "C": 90.0, "D": 50.0}
        with self.assertRaises(ScheduleError):
            s.record_week(1, totals)

    def test_double_record_raises(self):
        s = _season4()
        totals = {"A": 100.0, "B": 90.0, "C": 90.0, "D": 50.0}
        s.record_week(1, totals)
        with self.assertRaises(WeekAlreadyFinal):
            s.record_week(1, totals)

    def test_playoff_and_dark_weeks_have_no_matchups(self):
        s = _season4()
        totals = {"A": 100.0, "B": 90.0, "C": 90.0, "D": 50.0}
        for week in (7, 8, 9):
            with self.assertRaises(WeekNotFinalized):
                s.record_week(week, totals)

    def test_week_out_of_range(self):
        s = _season4()
        totals = {"A": 100.0, "B": 90.0, "C": 90.0, "D": 50.0}
        with self.assertRaises(WeekOutOfRange):
            s.record_week(10, totals)


class TestStandings(unittest.TestCase):
    def _two_weeks(self):
        s = _season4()
        # Week 1: (A,D) A 100-50; (B,C) B 90-40.
        s.record_week(1, {"A": 100.0, "B": 90.0, "C": 40.0, "D": 50.0})
        # Week 2: (A,C) C 70-60; (D,B) B 65-55.
        s.record_week(2, {"A": 60.0, "B": 65.0, "C": 70.0, "D": 55.0})
        return s

    def test_team_record_hand_derived(self):
        s = self._two_weeks()
        a = s.team_record("A")
        self.assertEqual((a["W"], a["L"], a["T"]), (1, 1, 0))
        self.assertEqual(a["points_for"], 160.0)
        self.assertEqual(a["points_against"], 120.0)
        self.assertEqual(a["team_name"], "Team A")
        b = s.team_record("B")
        self.assertEqual((b["W"], b["L"], b["T"]), (2, 0, 0))
        self.assertEqual(b["points_for"], 155.0)

    def test_standings_order_wins_then_points_for(self):
        s = self._two_weeks()
        # B 2-0; A and C both 1-1 but A PF 160 > C PF 110; D 0-2.
        order = [r["team_id"] for r in s.standings()]
        self.assertEqual(order, ["B", "A", "C", "D"])

    def test_head_to_head_breaks_points_for_tie(self):
        s = _season4()
        # Week 1: (A,D) A 100-50; (B,C) B 100-50.
        s.record_week(1, {"A": 100.0, "B": 100.0, "C": 50.0, "D": 50.0})
        # Week 2: (A,C) C 100-50; (D,B) B 100-50.
        s.record_week(2, {"A": 50.0, "B": 100.0, "C": 100.0, "D": 50.0})
        # A and C: 1-1, PF 150 each. Only meeting: C beat A -> C first.
        order = [r["team_id"] for r in s.standings()]
        self.assertEqual(order, ["B", "C", "A", "D"])

    def test_seeded_coin_flip_is_deterministic(self):
        # 2-team league: every week is A vs B; all ties -> coin flip.
        teams = (("A", "Team A"), ("B", "Team B"))
        cfg = ScheduleConfig(teams=teams, seed=7, team_order=("A", "B"))
        totals = {"A": 50.0, "B": 50.0}
        s1 = Season(cfg)
        s2 = Season(cfg)
        s1.record_week(1, totals)
        s1.record_week(2, totals)
        s2.record_week(1, totals)
        s2.record_week(2, dict(reversed(list(totals.items()))))
        o1 = [r["team_id"] for r in s1.standings()]
        o2 = [r["team_id"] for r in s2.standings()]
        self.assertEqual(o1, o2)  # independent of dict ordering
        self.assertEqual(sorted(o1), ["A", "B"])  # strict total order
        # Independent replication of the seeded key draw.
        rng = random.Random(7)
        keys = {tid: rng.random() for tid in sorted(("A", "B"))}
        expected_first = max(keys, key=keys.get)
        self.assertEqual(o1[0], expected_first)

    def test_unknown_team_record_raises(self):
        s = _season4()
        with self.assertRaises(UnknownTeam):
            s.team_record("ZZZ")


class TestPlayoffSeeds(unittest.TestCase):
    def _full_season(self):
        s = _season4()
        weeks = {
            # Week: (A,B,C,D) scores. Pairings: w1 (A,D),(B,C);
            # w2 (A,C),(D,B); w3 (A,B),(C,D); w4-6 replay w1.
            1: (100.0, 50.0, 40.0, 50.0),
            2: (100.0, 50.0, 40.0, 50.0),
            3: (100.0, 50.0, 40.0, 50.0),
            4: (100.0, 50.0, 40.0, 50.0),
            5: (100.0, 50.0, 40.0, 50.0),
            6: (100.0, 50.0, 40.0, 50.0),
        }
        for week, (a, b, c, d) in weeks.items():
            s.record_week(week, {"A": a, "B": b, "C": c, "D": d})
        return s

    def test_seeds_require_complete_regular_season(self):
        s = _season4()
        s.record_week(1, {"A": 100.0, "B": 50.0, "C": 40.0, "D": 50.0})
        with self.assertRaises(WeekNotFinalized):
            s.playoff_seeds()

    def test_seeds_hand_derived(self):
        s = self._full_season()
        # A: 6-0-0 PF 600. B: 4-1-1 PF 300. D: 1-4-1 PF 300. C: 0-6-0.
        seeds = s.playoff_seeds()
        self.assertEqual(seeds, ["A", "B", "D", "C"])


class TestJsonContract(unittest.TestCase):
    def test_round_trip_preserves_state(self):
        s = _season4(seed=9)
        s.record_week(1, {"A": 100.0, "B": 90.0, "C": 40.0, "D": 50.0})
        s.record_week(2, {"A": 60.0, "B": 65.0, "C": 70.0, "D": 55.0})
        snap = s.to_dict()
        s2 = Season.from_dict(snap)
        self.assertEqual(s2.finalized_weeks, [1, 2])
        self.assertEqual(s2.schedule, s.schedule)
        self.assertEqual(
            [r["team_id"] for r in s2.standings()],
            [r["team_id"] for r in s.standings()],
        )
        # Restored season stays live: week 3 records fine.
        s2.record_week(3, {"A": 10.0, "B": 20.0, "C": 30.0, "D": 40.0})
        self.assertEqual(s2.finalized_weeks, [1, 2, 3])

    def test_round_trip_empty_season(self):
        s = _season4(seed=9)
        s2 = Season.from_dict(s.to_dict())
        self.assertEqual(s2.finalized_weeks, [])
        self.assertEqual(s2.schedule, s.schedule)


if __name__ == "__main__":
    unittest.main(verbosity=2)
