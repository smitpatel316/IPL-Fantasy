"""P5-L1: mock-draft engine orchestration.

Runs ephemeral practice drafts on top of the existing draft engine
(Draft / auto_pick / d8_reachable). Every bot team gets its own
pre-draft rank board injected via Draft.set_ranks; all picks go through
Draft.auto_pick, so the D8-reachability guardrail still applies to every
bot pick and mock rosters are D8-legal by construction.

The bot difficulty ladder is a locked product call (Atlas, P5-L1):
exactly two levels exist — "casual" and "sharp". Do NOT add a third
level here; a new difficulty needs an Atlas ruling note, not a silent
build. Neither difficulty touches engine invariants or D-decisions:
bots are orchestration (rank boards), not rules.

Difficulties:
  casual — a rank-list board with seeded Gaussian noise added, i.e. a
           manager who roughly follows the consensus list but reaches
           and slides. Noise is deterministic per (seed, team index).
  sharp  — the true consensus board, plus schedule-nudge weighting:
           players on IPL teams with above-average games over the
           weighted weeks (defaults to weeks 1-3 game counts from
           api/schedule_games) get a small rank boost, capturing the
           schedule-luck skill P3-A6 ships to real managers. Falls back
           to pure ranks when no schedule data is available (honest
           no-data behavior, same as the nudge badges).

Nothing here touches a database; the API seam (routers/mock_draft.py)
feeds the universe from read-only league queries.
"""

import math
import random

from .draft_engine import Draft, DraftConfig, DraftError

# The locked two-level ladder. Do not extend without an Atlas ruling.
BOT_DIFFICULTIES = ("casual", "sharp")
CASUAL = "casual"
SHARP = "sharp"

#: Std-dev of the casual bot's rank noise, in rank slots.
CASUAL_NOISE_STD = 18.0
#: Weeks whose game counts feed the sharp bot's schedule weighting.
SHARP_WEIGHT_WEEKS = (1, 2, 3)
#: Rank boost per game above the league-mean (in rank slots). A player
#: on a team playing 2 extra games early jumps ~5 slots.
SCHEDULE_BOOST_PER_GAME = 2.5


def bot_ranks(pool: list, difficulty: str, rng: random.Random,
              schedule_boost: dict | None = None) -> list:
    """Build a bot's pre-draft rank board.

    pool: player_ids best-first (the consensus ADP proxy). schedule_boost:
    player_id -> rank-slot boost (positive = pick earlier). Returns a new
    ordering; the input pool order is untouched.
    """
    if difficulty not in BOT_DIFFICULTIES:
        raise DraftError(
            f"unknown bot difficulty {difficulty!r} "
            f"(locked ladder: {', '.join(BOT_DIFFICULTIES)})"
        )
    boost = schedule_boost or {}
    if difficulty == SHARP:
        scored = [(rank - boost.get(pid, 0.0), pid)
                  for rank, pid in enumerate(pool)]
        scored.sort(key=lambda t: (t[0], t[1]))
        return [pid for _, pid in scored]
    # casual: seeded Gaussian noise on the consensus board.
    scored = [(rank + rng.gauss(0.0, CASUAL_NOISE_STD), pid)
              for rank, pid in enumerate(pool)]
    scored.sort(key=lambda t: (t[0], t[1]))
    return [pid for _, pid in scored]


def schedule_boost_map(pool: list, ipl_team_of: dict, games_per_team: dict,
                       weeks: tuple = SHARP_WEIGHT_WEEKS) -> dict:
    """player_id -> rank-slot boost from early-week schedule density.

    players on IPL teams with more games than the mean over `weeks` get
    a positive boost (picked earlier); below-mean teams get a negative
    one. Returns {} when games data is absent (honest no-data fallback).
    """
    if not games_per_team:
        return {}
    teams = set(ipl_team_of.values()) & set(games_per_team)
    if not teams:
        return {}
    mean_games = sum(games_per_team[t] for t in teams) / len(teams)
    return {
        pid: SCHEDULE_BOOST_PER_GAME * (games_per_team.get(ipl_team_of.get(pid), mean_games) - mean_games)
        for pid in pool
    }


def run_mock_draft(pool: list, roles: dict, teams: list[tuple],
                   difficulties: dict, rounds: int = 14, seed: int = 42,
                   ipl_team_of: dict | None = None,
                   games_per_team: dict | None = None) -> dict:
    """Run a full ephemeral mock draft. Returns a pick/rosters report.

    teams: [(team_key, team_name), ...] — keys are opaque (the API uses
    0..n-1; names are bot labels). difficulties: team_key -> "casual" |
    "sharp". ipl_team_of: player_id -> ipl_team_code (for sharp
    schedule weighting); games_per_team: ipl_team_code -> total games
    over the weighted weeks.
    """
    n = len(teams)
    if not 2 <= n <= 10:
        raise DraftError(f"mock draft needs 2-10 teams, got {n}")
    if len(pool) < n * rounds:
        raise DraftError(
            f"mock-draft pool too small: {len(pool)} players, "
            f"{n * rounds} picks required ({n} teams x {rounds} rounds)")
    for key, _ in teams:
        if difficulties.get(key) not in BOT_DIFFICULTIES:
            raise DraftError(
                f"team {key!r} has invalid difficulty "
                f"{difficulties.get(key)!r} (locked ladder: "
                f"{', '.join(BOT_DIFFICULTIES)})")

    boost = schedule_boost_map(pool, ipl_team_of or {},
                               games_per_team or {})
    rng = random.Random(seed)
    config = DraftConfig(teams=tuple(teams), rounds=rounds, seed=seed,
                         pick_clock_secs=0)
    draft = Draft(config=config, pool=pool, roles=roles)
    for key, _ in teams:
        draft.set_ranks(key, bot_ranks(pool, difficulties[key],
                                       random.Random(rng.randrange(2 ** 31)),
                                       schedule_boost=boost))
    draft.start()
    while draft.status == Draft.STATUS_LIVE:
        draft.auto_pick()

    # Per-team average consensus rank (lower = better board execution),
    # the acceptance-criteria divergence signal.
    rank_of = {pid: i for i, pid in enumerate(pool)}
    avg_rank = {}
    for key, _ in teams:
        drafted = [pid for slot in draft.rosters[key].values()
                   for pid in slot]
        avg_rank[key] = (sum(rank_of[pid] for pid in drafted) / len(drafted)
                         if drafted else math.nan)

    return {
        "seed": seed,
        "rounds": rounds,
        "teams": [{"key": key, "name": name,
                   "difficulty": difficulties[key]}
                  for key, name in teams],
        "draft_order": list(draft.draft_order),
        "picks": [
            {"pick_no": p["pick_no"], "round_no": p["round_no"],
             "team_key": p["team_id"], "player_id": p["player_id"],
             "slot": p["slot"]}
            for p in draft.picks
        ],
        "rosters": {
            key: {slot: list(pids) for slot, pids in draft.rosters[key].items()}
            for key, _ in teams
        },
        "avg_consensus_rank": avg_rank,
    }
