"""Tests for the IPL fantasy snake draft engine (P2-L1).

Plain unittest, stdlib only. Run:  python3 test_draft_engine.py
Deterministic: seeded draft order + injected fake clock (no sleeping).
"""

import itertools
import json
import unittest
from dataclasses import replace

from api.engine.draft_engine import (
    ClockNotExpired,
    DoNotDraft,
    Draft,
    DraftConfig,
    DraftNotLive,
    ELIGIBLE_SLOTS,
    MAX_OVERSEAS_STARTERS,
    NotYourTurn,
    PlayerUnavailable,
    PoolExhausted,
    RosterFull,
    UnfieldableRoster,
    d8_reachable,
)


class FakeClock:
    def __init__(self, t=1000.0):
        self.t = float(t)

    def __call__(self):
        return self.t

    def advance(self, secs):
        self.t += secs


def make_pool(n, prefix="p"):
    return [f"{prefix}{i:03d}" for i in range(1, n + 1)]


def make_roles(pool):
    """Deterministic role cycling; is_overseas every 5th player (used by
    the draft's D8-feasibility guardrail: overseas picks that would leave
    a roster unable to field a legal 11 are illegal)."""
    cycle = ["WK", "BAT", "AR", "BOWL"]
    roles = {}
    for i, pid in enumerate(pool):
        roles[pid] = {"role": cycle[i % 4], "is_overseas": (i % 5 == 0)}
    return roles


SIX_TEAMS = tuple((f"t{i}", f"Team {i}") for i in range(1, 7))


def six_team_config(rounds=14, seed=7, clock_secs=60):
    return DraftConfig(teams=SIX_TEAMS, rounds=rounds,
                       pick_clock_secs=clock_secs, seed=seed)


class TestSnakeOrder(unittest.TestCase):
    def test_serpentine_mapping_6_teams(self):
        cfg = six_team_config()
        clock = FakeClock()
        draft = Draft(cfg, make_pool(100), make_roles(make_pool(100)), clock=clock)
        order = list(draft.draft_order)
        self.assertEqual(len(order), 6)

        def team(pick_no):
            return draft.pick_no_to_round_team(pick_no)[1]

        # Round 1 (odd): draft order; round 2 (even): reversed.
        for i in range(6):
            self.assertEqual(draft.pick_no_to_round_team(i + 1),
                             (1, order[i]), f"pick {i + 1}")
            self.assertEqual(draft.pick_no_to_round_team(12 - i),
                             (2, order[i]), f"pick {12 - i}")
        # Round boundaries.
        self.assertEqual(draft.pick_no_to_round_team(6), (1, order[5]))
        self.assertEqual(draft.pick_no_to_round_team(7), (2, order[5]))
        self.assertEqual(draft.pick_no_to_round_team(12), (2, order[0]))
        self.assertEqual(draft.pick_no_to_round_team(13), (3, order[0]))
        # Last pick: round 14 (even) -> reversed -> first team in order.
        self.assertEqual(draft.pick_no_to_round_team(84), (14, order[0]))
        # on-clock before start is None; after start it's round-1 pick-1 team.
        self.assertIsNone(draft.on_clock_team_id)
        draft.start()
        self.assertEqual(draft.on_clock_team_id, order[0])
        self.assertEqual(draft.current_pick_no, 1)
        self.assertEqual(draft.status, "live")

    def test_seeded_order_is_deterministic(self):
        pool = make_pool(100)
        d1 = Draft(six_team_config(), pool, clock=FakeClock())
        d2 = Draft(six_team_config(), pool, clock=FakeClock())
        self.assertEqual(d1.draft_order, d2.draft_order)
        d3 = Draft(six_team_config(seed=99), pool, clock=FakeClock())
        self.assertNotEqual(d1.draft_order, d3.draft_order)


class TestPickClock(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.pool = make_pool(100)
        self.draft = Draft(six_team_config(), self.pool,
                           make_roles(self.pool), clock=self.clock)
        self.draft.start()

    def test_deadline_set_and_reset(self):
        first = self.draft.pick_deadline
        self.assertEqual(first, 1000.0 + 60)
        on_clock = self.draft.on_clock_team_id
        self.draft.manual_pick(on_clock, "p001")
        self.assertEqual(self.draft.pick_deadline, 1000.0 + 60)

    def test_expire_pick_autopicks_best_available(self):
        on_clock = self.draft.on_clock_team_id
        self.clock.advance(61)  # past the 60s clock
        pick = self.draft.expire_pick()
        self.assertTrue(pick["is_auto"])
        self.assertEqual(pick["team_id"], on_clock)
        self.assertEqual(pick["player_id"], "p001")  # pool order = ADP proxy
        # Pick #1: p001 is WK (cycle) -> fills the WK slot.
        self.assertEqual(pick["slot"], "WK")
        self.assertEqual(self.draft.picks_made, 1)

    def test_expire_before_deadline_raises(self):
        with self.assertRaises(ClockNotExpired):
            self.draft.expire_pick()
        self.assertEqual(self.draft.picks_made, 0)

    def test_dnd_honored_on_autopick(self):
        on_clock = self.draft.on_clock_team_id
        self.draft.add_to_dnd(on_clock, "p001")
        self.clock.advance(61)
        pick = self.draft.expire_pick()
        self.assertTrue(pick["is_auto"])
        self.assertNotEqual(pick["player_id"], "p001")
        # p002 is the next-best available.
        self.assertEqual(pick["player_id"], "p002")


class TestStartersBeforeBench(unittest.TestCase):
    """Auto-pick must fill open starter slots before benching players."""

    def _draft_with_filled_bat_slots(self):
        """Team t1 has BATx3 + UTIL filled; WK slot open; custom ranks."""
        clock = FakeClock()
        pool = make_pool(60)
        roles = make_roles(pool)
        # Force known roles for the players we care about.
        for pid in ["p005", "p006", "p007", "p010"]:
            roles[pid] = {"role": "BAT", "is_overseas": False}
        for pid in ["p008", "p009"]:
            roles[pid] = {"role": "WK", "is_overseas": False}
        roles["p011"] = {"role": "BOWL", "is_overseas": False}
        roles["p018"] = {"role": "BAT", "is_overseas": False}
        cfg = DraftConfig(teams=(("t1", "Team 1"),), rounds=14,
                          pick_clock_secs=60, seed=1)
        draft = Draft(cfg, pool, roles, clock=clock)
        draft.start()
        # Fill BATx3 + UTILx2(BAT overflow) manually.
        for pid in ["p005", "p006", "p007", "p010", "p018"]:
            self.assertEqual(draft.on_clock_team_id, "t1")
            draft.manual_pick("t1", pid)
        roster = draft.rosters["t1"]
        self.assertEqual(len(roster["BAT"]), 3)
        self.assertEqual(len(roster["UTIL"]), 2)
        return draft

    def test_skips_full_role_for_open_starter_slot(self):
        draft = self._draft_with_filled_bat_slots()
        # Custom ranks: #1 is a BAT (no BAT/UTIL slot open), #2 is a WK.
        draft.set_ranks("t1", ["p012", "p009"])
        # p012 -> make it a BAT explicitly.
        draft.roles["p012"] = {"role": "BAT", "is_overseas": False}
        self.clock_advance_and_expire(draft)
        pick = draft.picks[-1]
        self.assertTrue(pick["is_auto"])
        # The WK (rank #2) fills the open WK starter slot, not the top BAT.
        self.assertEqual(pick["player_id"], "p009")
        self.assertEqual(pick["slot"], "WK")

    def test_bench_fallback_when_no_starter_slot_fits(self):
        draft = self._draft_with_filled_bat_slots()
        # Fill the WK slot too; remaining open slots: ARx2, BOWLx3.
        draft.manual_pick("t1", "p008")  # WK
        # Ranks: top is a BAT that fits no open starter slot -> bench.
        draft.roles["p012"] = {"role": "BAT", "is_overseas": False}
        draft.set_ranks("t1", ["p012", "p011"])  # p011 is BOWL (fits)
        self.clock_advance_and_expire(draft)
        pick = draft.picks[-1]
        # p011 (BOWL, rank #2) fills an open BOWL starter slot ahead of
        # the higher-ranked BAT, which cannot start anywhere.
        self.assertEqual(pick["player_id"], "p011")
        self.assertEqual(pick["slot"], "BOWL")

    def test_all_starters_full_picks_best_to_bench(self):
        draft = self._draft_with_filled_bat_slots()
        draft.manual_pick("t1", "p008")  # WK
        draft.manual_pick("t1", "p009")  # WK -> bench (WK full) -- adjust below
        # p009 is WK role; WK slot already taken by p008, so it goes to BN.
        draft.roles["p013"] = {"role": "AR", "is_overseas": False}
        draft.roles["p014"] = {"role": "AR", "is_overseas": False}
        draft.roles["p015"] = {"role": "BOWL", "is_overseas": False}
        draft.roles["p016"] = {"role": "BOWL", "is_overseas": False}
        draft.roles["p017"] = {"role": "BOWL", "is_overseas": False}
        for pid in ["p013", "p014", "p015", "p016", "p017"]:
            draft.manual_pick("t1", pid)
        # Starters now: WK1 BAT3 AR2 BOWL3 UTIL2 = 11 (plus p009 on BN).
        starters = sum(len(draft.rosters["t1"][s])
                       for s in ("WK", "BAT", "AR", "BOWL", "UTIL"))
        self.assertEqual(starters, 11)
        draft.roles["p020"] = {"role": "WK", "is_overseas": False}
        draft.set_ranks("t1", ["p020"])
        self.clock_advance_and_expire(draft)
        pick = draft.picks[-1]
        self.assertTrue(pick["is_auto"])
        self.assertEqual(pick["player_id"], "p020")
        self.assertEqual(pick["slot"], "BN")  # no starter slot open -> bench

    @staticmethod
    def clock_advance_and_expire(draft):
        draft.clock.advance(draft.config.pick_clock_secs + 1)
        return draft.expire_pick()


class TestILRule(unittest.TestCase):
    """P2-L8 (Smit 2026-09-15): IL is never filled during the draft.

    Injured players may be drafted but occupy a normal roster slot;
    the roster service moves them to IL post-draft. The draft engine
    has no injury concept — the invariant is simply: no pick is ever
    assigned the IL slot.
    """

    def test_injured_player_drafted_into_normal_slot(self):
        clock = FakeClock()
        pool = make_pool(40)
        roles = make_roles(pool)
        # Mark p001 "injured" (the draft engine doesn't care — it just
        # never assigns IL).
        roles["p001"] = {"role": "BOWL", "is_overseas": False}
        draft = Draft(DraftConfig(teams=(("t1", "Team 1"),), rounds=14,
                                  pick_clock_secs=60, seed=1),
                      pool, roles, clock=clock)
        draft.start()
        pick = draft.manual_pick("t1", "p001")
        self.assertNotEqual(pick["slot"], "IL")
        self.assertEqual(pick["slot"], "BOWL")

    def test_roster_full_without_il_escape_hatch(self):
        # When every slot the player's role may occupy is full AND the
        # bench is full, the pick raises RosterFull — the manager must
        # draft a player whose role fits an open starter slot instead.
        clock = FakeClock()
        pool = make_pool(40)
        roles = {pid: {"role": "WK", "is_overseas": False} for pid in pool}
        # D8 feasibility off: an all-WK pool can never field a legal 11;
        # this test covers RosterFull from slot assignment, not D8.
        draft = Draft(DraftConfig(teams=(("t1", "Team 1"),), rounds=14,
                                  pick_clock_secs=60, seed=1,
                                  enforce_d8_feasibility=False),
                      pool, roles, clock=clock)
        draft.start()
        draft.manual_pick("t1", "p001")  # WK slot
        draft.manual_pick("t1", "p002")  # WK full -> BN
        draft.manual_pick("t1", "p003")  # BN
        draft.manual_pick("t1", "p004")  # BN (full at 3)
        with self.assertRaises(RosterFull):
            draft.manual_pick("t1", "p005")  # nowhere legal; IL not allowed


def exact_legal_elevens(roster_players, roles):
    """Independent oracle: every D8-legal 11 in a 14-man roster, brute force.

    A legal 11 covers WK1/BAT3/AR2/BOWL3 + UTIL2 (BAT/AR/BOWL) with at
    most 4 overseas players. C(14,11) = 364 combos: cheap and exact.
    Cross-checks the draft's d8_reachable guardrail — the oracle
    knows nothing about the guardrail's formula.
    """
    out = []
    for eleven in itertools.combinations(roster_players, 11):
        if sum(1 for p in eleven
               if (roles.get(p) or {}).get("is_overseas", False)) > 4:
            continue
        need = {"WK": 1, "BAT": 3, "AR": 2, "BOWL": 3}
        flex = 0
        ok = True
        for p in eleven:
            r = (roles.get(p) or {}).get("role")
            if need.get(r, 0) > 0:
                need[r] -= 1
            elif r in ("BAT", "AR", "BOWL"):
                flex += 1
            else:
                ok = False
                break
        if ok and all(v == 0 for v in need.values()) and flex >= 2:
            out.append(eleven)
    return out


class TestD8Feasibility(unittest.TestCase):
    """P2-L7: the draft never lets a team draft an unfieldable roster.

    D8 caps overseas STARTERS at 4. The guardrail is role-aware, not a
    flat domestic headcount: an overseas pick is illegal exactly when it
    would push the minimum forced overseas starters above 4
    (d8_reachable). A 7-domestic roster can still be unfieldable —
    sandbox seeds 16/40 produced exactly that (overseas concentrated in
    AR/BOWL with no domestic cover) — so the guard is on forced
    overseas starters, never on the domestic total.
    """

    def _d8_draft(self):
        # 2 teams x 14 rounds, tiny pool with known overseas flags.
        # Roles are chosen so every player used below fits a real slot.
        teams = (("A", "Team A"), ("B", "Team B"))
        domestic = {
            "d_wk": "WK", "d_wk2": "WK",
            "d_b1": "BAT", "d_b2": "BAT", "d_b3": "BAT",
            "d_a1": "AR", "d_a2": "AR",
            "d_bw1": "BOWL", "d_bw2": "BOWL",
        }
        overseas = {
            "o_bw1": "BOWL", "o_bw2": "BOWL", "o_bw3": "BOWL",
            "o_a1": "AR", "o_a2": "AR",
            "o_b1": "BAT", "o_b2": "BAT",
        }
        extra = {"x_d1": ("BAT", False), "x_d2": ("BAT", False),
                 "x_o1": ("BAT", True), "x_o2": ("BAT", True)}
        pool = list(domestic) + list(overseas) + list(extra)
        roles = {pid: {"role": r, "is_overseas": False}
                 for pid, r in domestic.items()}
        roles.update({pid: {"role": r, "is_overseas": True}
                      for pid, r in overseas.items()})
        roles.update({pid: {"role": r, "is_overseas": ov}
                      for pid, (r, ov) in extra.items()})
        cfg = DraftConfig(teams=teams, rounds=14, pick_clock_secs=60,
                          seed=1, draft_order=("A", "B"))
        draft = Draft(cfg, pool, roles, clock=FakeClock())
        draft.start()
        return draft

    def _stuff_boundary_roster(self, draft):
        # Team A: 13 drafted, 1 pick left. Domestic cover is
        # WK1/BAT3/AR2/BOWL0 — no domestic BOWL exists, so the 3 BOWL
        # slots force 3 overseas starters and the 2 UTIL slots (no spare
        # domestic BAT/AR/BOWL) force 2 more: 5 > 4 -> overseas illegal.
        r = draft.rosters["A"]
        r["WK"] = ["d_wk"]
        r["BAT"] = ["d_b1", "d_b2", "d_b3"]
        r["AR"] = ["d_a1", "d_a2"]
        r["BOWL"] = ["o_bw1", "o_bw2", "o_bw3"]
        r["UTIL"] = ["o_a1", "o_a2"]
        r["BN"] = ["o_b1", "o_b2"]
        return draft

    def _stuff_seed16_shape(self, draft):
        # P2-L7 regression: the sandbox's seeds 16/40 produced a roster
        # with 7 domestic players that is STILL unfieldable — zero
        # domestic AR and only 2 domestic BOWL, so the overseas AR/BOWL
        # starters have no domestic cover. 13 drafted (1 pick left is
        # judged); the would-be 14th is an overseas BAT (x_o2).
        r = draft.rosters["A"]
        r["WK"] = ["d_wk"]
        r["BAT"] = ["d_b1", "d_b2", "d_b3"]
        r["AR"] = ["o_a1", "o_a2"]
        r["BOWL"] = ["o_bw1", "d_bw1", "d_bw2"]
        r["UTIL"] = ["o_b1", "o_b2"]
        r["BN"] = ["d_wk2", "x_o1"]
        return draft

    def test_pick_reachability_formula(self):
        draft = self._d8_draft()
        # Fresh draft: no cover yet but 13 picks left after this one —
        # easily repairable -> an overseas pick is legal.
        self.assertTrue(draft._pick_keeps_d8_reachable("A", "o_bw1"))
        self._stuff_boundary_roster(draft)
        # 13 drafted, 0 picks left after this one: no domestic BOWL
        # cover and no spare flex -> overseas pick illegal, domestic
        # BAT pick legal (it supplies the missing UTIL flex).
        self.assertFalse(draft._pick_keeps_d8_reachable("A", "x_o1"))
        self.assertTrue(draft._pick_keeps_d8_reachable("A", "x_d1"))
        # One fewer drafted player -> 1 pick left after this one, which
        # can cover a BOWL slot -> overseas pick legal again.
        draft.rosters["A"]["BN"].pop()
        self.assertTrue(draft._pick_keeps_d8_reachable("A", "x_o1"))

    def test_seven_domestic_can_still_be_unfieldable(self):
        # P2-L7 regression (sandbox seeds 16/40): 7 domestic players is
        # NOT enough when role cover is missing. Here there is no
        # domestic AR and only 2 domestic BOWL, so the would-be 14-man
        # roster (13 drafted + overseas BAT x_o2) admits no D8-legal 11 —
        # the independent brute-force oracle confirms zero legal 11s —
        # and the guardrail blocks the pick.
        draft = self._stuff_seed16_shape(self._d8_draft())
        d, o = draft._roster_composition("A")
        self.assertEqual(sum(d.values()), 7)
        self.assertFalse(draft._pick_keeps_d8_reachable("A", "x_o2"))
        with self.assertRaises(UnfieldableRoster):
            draft.manual_pick("A", "x_o2")
        roster_14 = [p for slot in ("WK", "BAT", "AR", "BOWL", "UTIL", "BN")
                     for p in draft.rosters["A"][slot]] + ["x_o2"]
        self.assertEqual(
            exact_legal_elevens(roster_14, draft.roles), [],
            "oracle: the 7-domestic roster truly has no D8-legal 11")

    def test_seven_domestic_fieldable_when_cover_exists(self):
        # Same headcount, different shape: domestic cover exists for
        # every rigid slot (WK1/BAT3/AR2/BOWL1), so the last pick may be
        # overseas — and the oracle finds legal 11s.
        draft = self._d8_draft()
        r = draft.rosters["A"]
        r["WK"] = ["d_wk"]
        r["BAT"] = ["d_b1", "d_b2", "d_b3"]
        r["AR"] = ["d_a1", "d_a2"]
        r["BOWL"] = ["o_bw1", "o_bw2", "d_bw1"]
        r["UTIL"] = ["o_a1", "o_a2"]
        r["BN"] = ["o_b1", "o_b2"]
        d, o = draft._roster_composition("A")
        self.assertEqual(sum(d.values()), 7)
        self.assertTrue(draft._pick_keeps_d8_reachable("A", "x_o2"))
        roster_14 = [p for slot in ("WK", "BAT", "AR", "BOWL", "UTIL", "BN")
                     for p in draft.rosters["A"][slot]] + ["x_o2"]
        self.assertGreater(
            len(exact_legal_elevens(roster_14, draft.roles)), 0,
            "oracle: a D8-legal 11 must exist")

    def test_d8_reachable_matches_exact_solver(self):
        # Differential fuzz: d8_reachable(d, o, 0) must agree with the
        # brute-force oracle on whether a D8-legal 11 exists, across
        # random rosters INCLUDING body-short ones (sparse WKs — the
        # case that broke the earlier closed-form formula).
        import random
        rng = random.Random(20260915)
        roles_pool = ["WK"] + ["BAT", "AR", "BOWL"] * 8  # sparse WKs
        mismatches = 0
        for trial in range(500):
            wk_used = 0
            players, roles = [], {}
            for i in range(14):
                role = rng.choice(roles_pool)
                if role == "WK":
                    if wk_used >= 4:
                        role = rng.choice(["BAT", "AR", "BOWL"])
                    else:
                        wk_used += 1
                pid = f"f{trial:03d}_{i:02d}"
                players.append(pid)
                roles[pid] = {"role": role,
                              "is_overseas": rng.random() < 0.35}
            d, o = {}, {}
            for pid in players:
                r = roles[pid]["role"]
                target = o if roles[pid]["is_overseas"] else d
                target[r] = target.get(r, 0) + 1
            formula_says_legal = d8_reachable(d, o, 0)
            oracle_says_legal = len(
                exact_legal_elevens(players, roles)) > 0
            if formula_says_legal != oracle_says_legal:
                mismatches += 1
        self.assertEqual(mismatches, 0,
                         f"{mismatches}/500 formula/oracle mismatches")

    def test_manual_overseas_pick_blocked_at_boundary(self):
        draft = self._stuff_boundary_roster(self._d8_draft())
        self.assertEqual(draft.on_clock_team_id, "A")
        with self.assertRaises(UnfieldableRoster):
            draft.manual_pick("A", "x_o1")

    def test_manual_domestic_pick_allowed_at_boundary(self):
        draft = self._stuff_boundary_roster(self._d8_draft())
        pick = draft.manual_pick("A", "x_d1")
        self.assertEqual(pick["player_id"], "x_d1")
        # BAT and UTIL are full -> bench.
        self.assertEqual(pick["slot"], "BN")

    def test_auto_pick_skips_bricking_overseas_pick(self):
        draft = self._stuff_boundary_roster(self._d8_draft())
        # Rank the illegal overseas player first: auto-pick must skip it
        # for the best D8-legal candidate instead of bricking the roster.
        draft.set_ranks("A", ["x_o1", "x_d1"])
        pick = draft.auto_pick("A")
        self.assertTrue(pick["is_auto"])
        self.assertEqual(pick["player_id"], "x_d1")

    def test_missing_overseas_metadata_treated_as_domestic(self):
        # The engine never invents overseas-ness.
        draft = self._d8_draft()
        draft.roles["x_o1"] = {"role": "BAT"}  # no is_overseas key
        self.assertFalse(draft._is_overseas("x_o1"))

    def test_full_auto_draft_leaves_every_roster_fieldable(self):
        # 2 teams x 14 rounds; the top 20 of the pool are all overseas,
        # so a D8-blind auto-pick would brick rosters. The guardrail must
        # force enough domestic picks — with the right role cover — that
        # every drafted roster admits a D8-legal 11 (checked by the
        # independent brute-force oracle, not the guardrail's formula).
        clock = FakeClock()
        pool = make_pool(60)
        roles = {}
        for i, pid in enumerate(pool):
            roles[pid] = {"role": ["WK", "BAT", "AR", "BOWL"][i % 4],
                          "is_overseas": i < 20}
        cfg = DraftConfig(teams=(("a", "A"), ("b", "B")), rounds=14,
                          pick_clock_secs=60, seed=3)
        draft = Draft(cfg, pool, roles, clock=clock)
        draft.start()
        while draft.status != Draft.STATUS_COMPLETE:
            draft.auto_pick()
        self.assertEqual(draft.picks_made, 28)
        for tid in ("a", "b"):
            players = [pid for slot in
                       ("WK", "BAT", "AR", "BOWL", "UTIL", "BN")
                       for pid in draft.rosters[tid][slot]]
            self.assertEqual(len(players), 14, tid)
            elevens = exact_legal_elevens(players, roles)
            self.assertGreater(
                len(elevens), 0,
                f"team {tid}: drafted roster has no D8-legal 11")


class TestManualPickValidations(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.pool = make_pool(30)
        # Short 2-round draft: D8 feasibility is off (a D8-legal 11 is
        # unreachable by construction in 2 rounds; these tests cover
        # pick validation, not D8).
        cfg = replace(six_team_config(rounds=2), enforce_d8_feasibility=False)
        self.draft = Draft(cfg, self.pool, make_roles(self.pool),
                           clock=self.clock)

    def test_pick_before_start_raises(self):
        with self.assertRaises(DraftNotLive):
            self.draft.manual_pick("t1", "p001")

    def test_not_your_turn(self):
        self.draft.start()
        on_clock = self.draft.on_clock_team_id
        other = next(t for t in ("t1", "t2", "t3", "t4", "t5", "t6")
                     if t != on_clock)
        with self.assertRaises(NotYourTurn):
            self.draft.manual_pick(other, "p001")

    def test_player_not_in_pool(self):
        self.draft.start()
        with self.assertRaises(PlayerUnavailable):
            self.draft.manual_pick(self.draft.on_clock_team_id, "nobody")

    def test_player_already_drafted(self):
        self.draft.start()
        team = self.draft.on_clock_team_id
        # p002 is domestic (p001 is overseas and therefore not draftable
        # in a 2-round draft under the D8-feasibility guardrail).
        self.draft.manual_pick(team, "p002")
        # Advance to that same team's next turn is 11 picks away; simpler:
        # another team cannot take p002 either.
        team2 = self.draft.on_clock_team_id
        with self.assertRaises(PlayerUnavailable):
            self.draft.manual_pick(team2, "p002")

    def test_do_not_draft(self):
        self.draft.start()
        team = self.draft.on_clock_team_id
        self.draft.add_to_dnd(team, "p003")
        with self.assertRaises(DoNotDraft):
            self.draft.manual_pick(team, "p003")

    def test_roster_full(self):
        # 1 team x 15 rounds: roster fills at 14, 15th pick raises RosterFull.
        clock = FakeClock()
        pool = make_pool(25)
        draft = Draft(DraftConfig(teams=(("solo", "Solo"),), rounds=15,
                                  pick_clock_secs=60, seed=1),
                      pool, make_roles(pool), clock=clock)
        draft.start()
        for i in range(14):
            draft.auto_pick()
        self.assertEqual(sum(len(v) for v in draft.rosters["solo"].values()), 14)
        with self.assertRaises(RosterFull):
            draft.manual_pick("solo", pool[14])

    def test_auto_pick_out_of_turn(self):
        self.draft.start()
        on_clock = self.draft.on_clock_team_id
        other = next(t for t in ("t1", "t2", "t3", "t4", "t5", "t6")
                     if t != on_clock)
        with self.assertRaises(NotYourTurn):
            self.draft.auto_pick(other)

    def test_auto_pick_pool_exhausted(self):
        # Basic pool exhaustion (D8 off): fewer players than picks.
        clock = FakeClock()
        pool = make_pool(3)
        cfg = DraftConfig(teams=(("a", "A"), ("b", "B")), rounds=2,
                          pick_clock_secs=60, seed=1,
                          enforce_d8_feasibility=False)
        draft = Draft(cfg, pool, make_roles(pool), clock=clock)
        draft.start()
        first = draft.auto_pick()   # p001
        second = draft.auto_pick()  # p002
        self.assertEqual(first["player_id"], "p001")
        self.assertEqual(second["player_id"], "p002")
        third = draft.auto_pick()   # p003
        self.assertEqual(third["player_id"], "p003")
        # Pool empty -> PoolExhausted.
        with self.assertRaises(PoolExhausted):
            draft.auto_pick()
        self.assertEqual(draft.status, "live")

    def test_auto_pick_pool_exhausted_when_only_bricking_picks_remain(self):
        # D8-specific: 14 rounds, 13 drafted in the seed-16 shape (no
        # D8-legal 11 reachable), and only overseas players left in the
        # pool -> every candidate breaks reachability -> PoolExhausted.
        # 1-team 14-round draft for a clean setup.
        cfg = DraftConfig(teams=(("A", "Team A"),), rounds=14,
                          pick_clock_secs=60, seed=1,
                          draft_order=("A",))
        pool = ([f"d{i}" for i in range(7)] + [f"o{i}" for i in range(6)]
                + ["o_left1", "o_left2"])
        roles = {}
        for i in range(7):
            roles[f"d{i}"] = {"role": ["WK", "WK", "BAT", "BAT", "BAT",
                                       "BOWL", "BOWL"][i],
                              "is_overseas": False}
        for i in range(6):
            roles[f"o{i}"] = {"role": ["AR", "AR", "BOWL", "BAT",
                                       "BAT", "BAT"][i],
                              "is_overseas": True}
        roles["o_left1"] = {"role": "BAT", "is_overseas": True}
        roles["o_left2"] = {"role": "AR", "is_overseas": True}
        draft = Draft(cfg, pool, roles, clock=FakeClock())
        draft.start()
        r = draft.rosters["A"]
        # 7 domestic (WK2/BAT3/BOWL2, zero AR) + 6 overseas = 13 drafted.
        r["WK"] = ["d0"]
        r["BAT"] = ["d2", "d3", "d4"]
        r["AR"] = ["o0", "o1"]
        r["BOWL"] = ["o2", "d5", "d6"]
        r["UTIL"] = ["o3", "o4"]
        r["BN"] = ["d1", "o5"]
        # Mark the 13 stuffed players unavailable (they're "already
        # drafted") via the DND list so only o_left1/o_left2 are
        # candidates.
        for pid in [p for slot in r.values() for p in slot]:
            draft.add_to_dnd("A", pid)
        # Only o_left1/o_left2 remain, both overseas and both bricking.
        with self.assertRaises(PoolExhausted):
            draft.auto_pick()
        self.assertEqual(draft.status, "live")


class TestFullDraft(unittest.TestCase):
    def test_6_team_14_round_draft(self):
        clock = FakeClock()
        pool = make_pool(120)
        roles = make_roles(pool)
        draft = Draft(six_team_config(), pool, roles, clock=clock)
        draft.start()
        self.assertEqual(draft.pick_deadline, 1000.0 + 60)

        for pick_no in range(1, 85):
            team = draft.on_clock_team_id
            expected_round, expected_team = draft.pick_no_to_round_team(pick_no)
            self.assertEqual(team, expected_team)
            # Mix manual and auto picks; manual picks choose the best
            # available player deterministically, fit-aware like a real
            # manager: while starter slots are open, take the best player
            # whose role can fill one (mirrors auto_pick's
            # starters-before-bench fill); otherwise take best available.
            if pick_no % 3 == 0:
                self.clock_advance(draft, clock)
                pick = draft.expire_pick()  # clock expiry -> auto
                self.assertTrue(pick["is_auto"])
            else:
                open_slots = draft._open_starter_slots(team)
                cands = draft._ranked_candidates(team)
                cand = None
                if open_slots:
                    for c in cands:
                        role = (draft.roles.get(c) or {}).get("role")
                        if any(s in open_slots
                               for s in ELIGIBLE_SLOTS.get(role, ())):
                            cand = c
                            break
                if cand is None:
                    cand = cands[0]
                pick = draft.manual_pick(team, cand)
                self.assertFalse(pick["is_auto"])
            self.assertEqual(pick["pick_no"], pick_no)
            self.assertEqual(pick["round_no"], expected_round)
            # P2-L8: the IL slot is NEVER filled during the draft.
            self.assertNotEqual(pick["slot"], "IL")

        self.assertEqual(draft.status, "complete")
        self.assertIsNone(draft.on_clock_team_id)
        self.assertEqual(draft.picks_made, 84)

        # 14 unique players per team.
        all_players = []
        for tid in ("t1", "t2", "t3", "t4", "t5", "t6"):
            roster = draft.rosters[tid]
            players = [p for slot in roster.values() for p in slot]
            self.assertEqual(len(players), 14, tid)
            self.assertEqual(len(set(players)), 14, tid)
            all_players.extend(players)
            # Slot caps (D7, Smit ruling 2026-09-15).
            self.assertLessEqual(len(roster["WK"]), 1)
            self.assertLessEqual(len(roster["BAT"]), 3)
            self.assertLessEqual(len(roster["AR"]), 2)
            self.assertLessEqual(len(roster["BOWL"]), 3)
            self.assertLessEqual(len(roster["UTIL"]), 2)
            self.assertLessEqual(len(roster["BN"]), 3)
            # P2-L8: no direct-to-IL picks — IL stays empty for the
            # roster service to fill post-draft on injury.
            self.assertEqual(len(roster["IL"]), 0)
            # P2-L7 D8 feasibility: every drafted roster can field a
            # D8-legal 11 (role-aware: not a flat domestic headcount —
            # the brute-force oracle decides).
            players = [pid for slot in roster for pid in roster[slot]]
            self.assertGreater(
                len(exact_legal_elevens(players, roles)), 0, tid)
        # No player drafted twice league-wide.
        self.assertEqual(len(set(all_players)), 84)

        # Event log ends with draft.completed.
        self.assertEqual(draft.event_log[-1]["type"], "draft.completed")
        types = {e["type"] for e in draft.event_log}
        self.assertIn("draft.created", types)
        self.assertIn("draft.started", types)
        self.assertIn("draft.pick", types)
        self.assertIn("pick.expired", types)
        # seq numbers are 1..N with no gaps.
        self.assertEqual([e["seq"] for e in draft.event_log],
                         list(range(1, len(draft.event_log) + 1)))

    @staticmethod
    def clock_advance(draft, clock):
        clock.advance(draft.config.pick_clock_secs + 1)


class TestJsonContract(unittest.TestCase):
    def test_to_dict_is_json_serializable_and_roundtrips(self):
        clock = FakeClock()
        pool = make_pool(60)
        roles = make_roles(pool)
        cfg = replace(six_team_config(rounds=3), enforce_d8_feasibility=False)
        draft = Draft(cfg, pool, roles, clock=clock)
        draft.add_to_dnd("t1", "p010")
        draft.set_ranks("t2", list(reversed(pool)))
        draft.start()
        for _ in range(5):
            team = draft.on_clock_team_id
            clock.advance(61)
            draft.expire_pick()

        state = draft.to_dict()
        blob = json.dumps(state)  # must be JSON-serializable
        restored = Draft.from_dict(json.loads(blob), pool=pool,
                                   roles=roles, clock=clock)
        self.assertEqual(restored.to_dict(), state)
        self.assertEqual(restored.status, "live")
        self.assertEqual(restored.on_clock_team_id, draft.on_clock_team_id)
        self.assertEqual(restored.pick_deadline, draft.pick_deadline)
        self.assertEqual(restored.picks, draft.picks)

        # Contract shape the web team can rely on.
        self.assertIn("draft", state)
        self.assertIn("picks", state)
        self.assertIn("rosters", state)
        self.assertIn("on_clock_team_id", state)
        self.assertIn("pick_deadline", state)
        self.assertIn("event_log", state)
        self.assertEqual(set(state["rosters"]["t1"].keys()),
                         {"WK", "BAT", "AR", "BOWL", "UTIL", "BN", "IL"})

    def test_roundtrip_of_completed_draft(self):
        clock = FakeClock()
        pool = make_pool(40)
        cfg = DraftConfig(teams=(("a", "A"), ("b", "B")), rounds=2,
                          pick_clock_secs=60, seed=5,
                          enforce_d8_feasibility=False)
        draft = Draft(cfg, pool, make_roles(pool), clock=clock)
        draft.start()
        for _ in range(4):
            clock.advance(61)
            draft.expire_pick()
        state = draft.to_dict()
        restored = Draft.from_dict(json.loads(json.dumps(state)),
                                   pool=pool, clock=clock)
        self.assertEqual(restored.status, "complete")
        self.assertEqual(restored.to_dict(), state)


if __name__ == "__main__":
    unittest.main(verbosity=2)
