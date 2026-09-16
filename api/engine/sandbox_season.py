"""IPL Fantasy — P2-L7 sandbox season driver.

Full season end-to-end, entirely offline on deterministic mock data:

  draft (P2-L1: 6 teams x 14-round snake, starters-before-bench fill)
    -> weekly lineups (P2-L2: cap-aware greedy fill, D7 slots, D8 cap)
    -> regular season (P2-L5: weeks 1-6 H2H, standings)
    -> playoffs (P2-L6: weeks 7-8 bracket + consolation, placements 1-6)

Everything is seeded: the same seed always produces the same season.
Mock player weekly scores derive from draft-pool rank (ADP proxy), so
draft quality flows through to standings — the chain is genuinely
exercised, not just wired.

Run:  python3 sandbox_season.py [seed]
"""

from __future__ import annotations

import itertools
import random
import sys

from .draft_engine import Draft, DraftConfig
from .matchup_scheduler import (
    REGULAR_SEASON_WEEKS,
    ScheduleConfig,
    Season,
)
from .playoff_engine import PlayoffBracket, PlayoffConfig
from .roster_service import LineupService

NUM_TEAMS = 6
DRAFT_ROUNDS = 14
POOL_SIZE = 120
OVERSEAS_FRACTION = 0.25


# ---------------------------------------------------------------------------
# Mock universe
# ---------------------------------------------------------------------------

def build_mock_pool(seed: int, n: int = POOL_SIZE):
    """Deterministic mock draft pool.

    Returns (pool, roles, adp_index, player_base) where pool is ordered
    best-first (the ADP proxy), roles maps pid -> {"role",
    "is_overseas"}, adp_index maps pid -> 0-based rank, and player_base
    maps pid -> expected weekly fantasy points.
    """
    rng = random.Random(seed)
    # Role mix: enough of every role for 6 x 14 rosters with depth.
    role_mix = (["WK"] * 10 + ["BAT"] * 42 + ["AR"] * 24 + ["BOWL"] * 44)
    assert len(role_mix) == n
    pool, roles, adp_index, player_base = [], {}, {}, {}
    for i, role in enumerate(role_mix):
        pid = f"m{i + 1:03d}"
        pool.append(pid)
        roles[pid] = {
            "role": role,
            "is_overseas": rng.random() < OVERSEAS_FRACTION,
        }
        adp_index[pid] = i
        # Best ADP ~120 pts/wk, tail ~25 pts/wk, plus small noise.
        player_base[pid] = max(0.0, 120.0 - 0.8 * i + rng.uniform(-5.0, 5.0))
    return pool, roles, adp_index, player_base


def solve_best_d8_lineup(roster, roles, adp_index):
    """Exact best-ADP D8-legal 11 from a 14-man roster.

    Enumerates every 11-subset (C(14,11) = 364), keeps those with at most
    4 overseas starters (>= 7 domestic) that admit a WK1/BAT3/AR2/BOWL3/
    UTIL2 assignment, and returns the player->slot assignment with the
    lowest total ADP (ties broken by player id for determinism).

    The draft guardrail guarantees at least one legal eleven exists, so
    finding none is a loud internal error, never a silent fudge.
    """
    slots = (["WK"] + ["BAT"] * 3 + ["AR"] * 2 + ["BOWL"] * 3
             + ["UTIL"] * 2)
    slot_roles = {"WK": ("WK",), "BAT": ("BAT",), "AR": ("AR",),
                  "BOWL": ("BOWL",), "UTIL": ("BAT", "AR", "BOWL")}

    def assignable(eleven):
        """Backtracking slot assignment; returns dict or None."""
        players = sorted(eleven)
        assignment = {}

        def dfs(i):
            if i == len(slots):
                return True
            slot = slots[i]
            allowed = slot_roles[slot]
            for p in players:
                if p in assignment or roles[p]["role"] not in allowed:
                    continue
                assignment[p] = slot
                if dfs(i + 1):
                    return True
                del assignment[p]
            return False

        return dict(assignment) if dfs(0) else None

    best = None
    best_key = None
    for eleven in itertools.combinations(sorted(roster), 11):
        overseas = sum(1 for p in eleven if roles[p]["is_overseas"])
        if overseas > 4:
            continue
        assignment = assignable(eleven)
        if assignment is None:
            continue
        total_adp = sum(adp_index[p] for p in eleven)
        key = (total_adp, eleven)
        if best_key is None or key < best_key:
            best_key = key
            best = assignment
    if best is None:
        raise AssertionError(
            "roster cannot field a D8-legal lineup "
            "(draft guardrail should have prevented this)")
    full = {p: best.get(p, "BN") for p in roster}
    starters = [p for p, s in full.items() if s != "BN"]
    assert len(starters) == 11, "lineup must have 11 starters"
    assert sum(1 for p in starters if roles[p]["is_overseas"]) <= 4, \
        "D8 overseas cap violated"
    return full


def build_weekly_assignments(roster, roles, adp_index):
    """Cap-aware lineup fill (D7 slots, D8 max 4 overseas starters).

    Delegates to the exact best-ADP solver: the D8-legal 11 with the
    lowest total ADP, ties broken deterministically. Replaces the old
    greedy+repair heuristic (which could miss legal lineups when the
    domestic players' roles didn't line up with the greedy picks).
    """
    return solve_best_d8_lineup(roster, roles, adp_index)


# ---------------------------------------------------------------------------
# Season run
# ---------------------------------------------------------------------------

def run_sandbox_season(seed: int = 7, verbose: bool = True) -> dict:
    """Run one full mock season. Returns a summary dict."""
    rng = random.Random(seed)
    pool, roles, adp_index, player_base = build_mock_pool(seed)
    teams = tuple((f"t{i}", f"Team {i}") for i in range(1, NUM_TEAMS + 1))
    team_ids = [t[0] for t in teams]
    names = dict(teams)

    # -- draft -----------------------------------------------------------
    draft = Draft(DraftConfig(teams=teams, rounds=DRAFT_ROUNDS, seed=seed),
                  pool=pool, roles=roles)
    draft.start()
    while draft.status != Draft.STATUS_COMPLETE:
        draft.auto_pick()
    assert draft.picks_made == NUM_TEAMS * DRAFT_ROUNDS
    rosters = {
        tid: [pid for slot in ("WK", "BAT", "AR", "BOWL", "UTIL", "BN")
              for pid in draft.rosters[tid][slot]]
        for tid in team_ids
    }
    assert all(len(r) == 14 for r in rosters.values())
    # IL is never draft-filled (Smit's IL rule).
    assert all(len(draft.rosters[tid].get("IL", [])) == 0 for tid in team_ids)

    # -- weekly lineups (P2-L2) ------------------------------------------
    lineups = LineupService(rosters, roles)
    weekly_starters: dict[int, dict] = {}
    for week in REGULAR_SEASON_WEEKS:
        weekly_starters[week] = {}
        for tid in team_ids:
            assignments = build_weekly_assignments(rosters[tid], roles,
                                                   adp_index)
            lineups.set_lineup(tid, week, assignments,
                               lock_deadline=10 ** 12, now=1_000_000.0)
            weekly_starters[week][tid] = lineups.get_starters(tid, week)
            assert len(weekly_starters[week][tid]) == 11

    # -- regular season (P2-L5) ------------------------------------------
    season = Season(ScheduleConfig(teams=teams, seed=seed))
    for week in REGULAR_SEASON_WEEKS:
        totals = {}
        for tid in team_ids:
            total = 0.0
            for pid in sorted(weekly_starters[week][tid]):  # fixed order
                total += max(0.0, rng.gauss(player_base[pid], 12.0))
            totals[tid] = round(total, 1)
        season.record_week(week, totals)
    standings = season.standings()
    assert len(standings) == NUM_TEAMS
    assert all(r["W"] + r["L"] + r["T"] == 6 for r in standings)
    seeds = season.playoff_seeds()
    assert len(seeds) == 4

    # -- playoffs (P2-L6) -------------------------------------------------
    consolation = tuple(r["team_id"] for r in standings[4:6])
    bracket = PlayoffBracket(
        PlayoffConfig(seeds=tuple(seeds), consolation=consolation,
                      team_names=tuple(teams)))
    week7_totals = {}
    for tid in team_ids:
        week7_totals[tid] = round(
            sum(max(0.0, rng.gauss(player_base[pid], 12.0))
                for pid in sorted(weekly_starters[6][tid])), 1)
    bracket.record_week(7, week7_totals)
    final_pairings = bracket.final_pairings()
    week8_teams = {t for pair in final_pairings for t in pair}
    week8_totals = {}
    for tid in sorted(week8_teams):
        week8_totals[tid] = round(
            sum(max(0.0, rng.gauss(player_base[pid], 12.0))
                for pid in sorted(weekly_starters[6][tid])), 1)
    bracket.record_week(8, week8_totals)
    placements = bracket.placements()

    summary = {
        "seed": seed,
        "draft_picks": draft.picks_made,
        "standings": [(r["team_id"], r["W"], r["L"], r["T"],
                       round(r["points_for"], 1)) for r in standings],
        "seeds": seeds,
        "champion": bracket.champion(),
        "placements": placements,
    }
    if verbose:
        print(f"=== sandbox season (seed {seed}) ===")
        print(f"draft: {draft.picks_made} picks, "
              f"{NUM_TEAMS} teams x {DRAFT_ROUNDS} rounds, IL empty")
        print("regular-season standings (team W-L-T PF):")
        for tid, w, l, t, pf in summary["standings"]:
            print(f"  {names[tid]:8s} {w}-{l}-{t}  PF {pf}")
        print(f"playoff seeds: {seeds}")
        print(f"champion: {names[summary['champion']]} "
              f"({summary['champion']})")
        print("placements:", {k: names[v]
                              for k, v in placements.items()})
    return summary


if __name__ == "__main__":
    run_sandbox_season(int(sys.argv[1]) if len(sys.argv) > 1 else 7)
