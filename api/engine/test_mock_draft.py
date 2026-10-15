"""P5-L1: engine-level tests for the mock-draft orchestrator.

Pure stdlib unittest, same convention as the other api/engine tests:
hand-derived cases only, deterministic seeds, no DB.
"""

import unittest

from api.engine import mock_draft
from api.engine.draft_engine import DraftError, PoolExhausted, d8_reachable


ROLES_SEQ = ["WK", "BAT", "BAT", "BAT", "AR", "AR", "BOWL", "BOWL",
             "BOWL", "BAT", "BAT", "AR", "BOWL", "WK", "BAT", "BAT"]


def _make_universe(n_players=130):
    """Best-first pool with full role metadata; half the pool domestic,
    half overseas, so D8-reachable drafts are possible."""
    pool = list(range(n_players))
    roles = {}
    for i, pid in enumerate(pool):
        roles[pid] = {
            "role": ROLES_SEQ[i % len(ROLES_SEQ)],
            "is_overseas": i % 2 == 1,
        }
    return pool, roles


def _composition(report, key):
    d, o = {}, {}
    for slot, pids in report["rosters"][key].items():
        for pid in pids:
            r = roles_of[pid]
            target = o if r["is_overseas"] else d
            target[r["role"]] = target.get(r["role"], 0) + 1
    return d, o


roles_of = {}


class TestMockDraft(unittest.TestCase):
    def setUp(self):
        global roles_of
        self.pool, roles = _make_universe()
        roles_of = roles
        self.roles = roles
        self.teams = [(i, f"Bot {i}") for i in range(8)]
        diffs = {i: ("sharp" if i % 2 == 0 else "casual")
                 for i in range(8)}

    def _run(self, **kw):
        args = dict(pool=self.pool, roles=self.roles, teams=self.teams,
                    difficulties={i: ("sharp" if i % 2 == 0 else "casual")
                                  for i in range(8)},
                    seed=7)
        args.update(kw)
        return mock_draft.run_mock_draft(**args)

    def test_completes_112_picks(self):
        r = self._run()
        self.assertEqual(len(r["picks"]), 112)
        for i, p in enumerate(r["picks"], start=1):
            self.assertEqual(p["pick_no"], i)
        for key, _ in self.teams:
            total = sum(len(v) for v in r["rosters"][key].values())
            self.assertEqual(total, 14, f"team {key} drafted {total}")

    def test_rosters_d8_legal_end_state(self):
        r = self._run()
        for key, _ in self.teams:
            d, o = _composition(r, key)
            self.assertTrue(d8_reachable(d, o, 0),
                            f"team {key} roster is not D8-legal")

    def test_difficulty_diverges(self):
        # Sharp bots must beat casual bots on average consensus rank,
        # measurably: worst sharp avg rank < best casual avg rank.
        r = self._run()
        sharp = [r["avg_consensus_rank"][k]
                 for k, _ in self.teams if k % 2 == 0]
        casual = [r["avg_consensus_rank"][k]
                  for k, _ in self.teams if k % 2 == 1]
        self.assertLess(max(sharp), min(casual),
                        f"sharp {sharp} not measurably better than casual {casual}")

    def test_deterministic_same_seed(self):
        a = self._run()
        b = self._run()
        self.assertEqual([p["player_id"] for p in a["picks"]],
                         [p["player_id"] for p in b["picks"]])

    def test_different_seed_diverges(self):
        a = self._run(seed=7)
        b = self._run(seed=12345)
        self.assertNotEqual([p["player_id"] for p in a["picks"]],
                            [p["player_id"] for p in b["picks"]])

    def test_invalid_difficulty_rejected(self):
        with self.assertRaises(DraftError):
            self._run(difficulties={i: "grandmaster" for i in range(8)})

    def test_locked_ladder_is_two_levels(self):
        self.assertEqual(set(mock_draft.BOT_DIFFICULTIES),
                         {"casual", "sharp"})

    def test_small_pool_fails_loud(self):
        with self.assertRaises(DraftError):
            self._run(pool=self.pool[:100])

    def test_team_count_bounds(self):
        with self.assertRaises(DraftError):
            mock_draft.run_mock_draft(
                pool=self.pool, roles=self.roles,
                teams=[(0, "solo")],
                difficulties={0: "sharp"})
        with self.assertRaises(DraftError):
            mock_draft.run_mock_draft(
                pool=self.pool, roles=self.roles,
                teams=[(i, f"B{i}") for i in range(11)],
                difficulties={i: "sharp" for i in range(11)})

    def test_schedule_boost_diverges_sharp_boards(self):
        ipl_team_of = {pid: ("MI" if i % 3 == 0 else "CSK")
                       for i, pid in enumerate(self.pool)}
        games = {"MI": 6, "CSK": 3}  # MI plays twice as often
        boost = mock_draft.schedule_boost_map(
            self.pool, ipl_team_of, games)
        self.assertTrue(all(v > 0 for k, v in boost.items()
                            if ipl_team_of[k] == "MI"))
        rng_a = __import__("random").Random(1)
        plain = mock_draft.bot_ranks(self.pool, "sharp", rng_a)
        boost_map = {pid: boost[pid] for pid in self.pool}
        rng_b = __import__("random").Random(1)
        weighted = mock_draft.bot_ranks(self.pool, "sharp", rng_b,
                                        schedule_boost=boost_map)
        self.assertNotEqual(plain, weighted)

    def test_schedule_boost_empty_is_honest_noop(self):
        self.assertEqual(
            mock_draft.schedule_boost_map(self.pool, {}, {}), {})


if __name__ == "__main__":
    unittest.main()
