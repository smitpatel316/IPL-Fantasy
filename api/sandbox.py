"""Deterministic sandbox seed: one demo league, 8 teams, and the full
canonical player universe (data/seed_players_universe.json — 129 players,
all 10 franchises) with roles/overseas flags and preseason ranks.
The pool must cover 8 teams x 14 rounds = 112 picks; the old hand-trimmed
48-player seed could never finish a draft (P4-W3). Mirrors
nba-fantasy-ai's SANDBOX_MODE: the UI shell and engine dev never need
live data. Idempotent — only seeds when the leagues table is empty."""

import json
import logging
import secrets
import string
from pathlib import Path

from .constants import (
    DRAFT_ROUNDS,
    FAAB_BUDGET,
    OVERSEAS_STARTER_CAP,
    PLAYOFF_TEAMS,
    ROSTER_SLOTS,
    SANDBOX_LEAGUE_NAME,
    SANDBOX_TEAM_COUNT,
    SCORING_TABLE_VERSION,
)

log = logging.getLogger("api.sandbox")

UNIVERSE_PATH = (Path(__file__).resolve().parent.parent
                 / "data" / "seed_players_universe.json")


def _load_universe() -> list[dict]:
    """Canonical player universe, best-first (pred desc, name tiebreak).

    Raises if the pool can no longer cover a full sandbox draft — a seed
    that cannot finish a draft must fail loudly here, not stall live.
    """
    players = json.loads(UNIVERSE_PATH.read_text())
    picks_needed = SANDBOX_TEAM_COUNT * DRAFT_ROUNDS
    if len(players) < picks_needed:
        raise RuntimeError(
            f"sandbox player universe too small: {len(players)} players in "
            f"{UNIVERSE_PATH.name}, {picks_needed} picks required "
            f"({SANDBOX_TEAM_COUNT} teams x {DRAFT_ROUNDS} rounds)")
    return sorted(players, key=lambda p: (-p["pred"], p["name"]))

MOCK_MANAGERS = [
    ("Smit", "Smit's XI"),
    ("Mansi", "Mansi's Marvels"),
    ("Aarav", "Aarav's Aces"),
    ("Diya", "Diya's Destroyers"),
    ("Kabir", "Kabir's Kings"),
    ("Anaya", "Anaya's Avengers"),
    ("Vivaan", "Vivaan's Vipers"),
    ("Ishaan", "Ishaan's Invincibles"),
]


def _invite_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(6))


def seed_if_empty(con) -> int | None:
    """Seed the sandbox league if no leagues exist. Returns league_id or None."""
    if con.execute("SELECT COUNT(*) FROM leagues").fetchone()[0] > 0:
        return None

    settings = {
        "draft_type": "snake",
        "rounds": DRAFT_ROUNDS,
        "roster_slots": dict(ROSTER_SLOTS),
        "faab_budget": FAAB_BUDGET,
        "scoring_table_version": SCORING_TABLE_VERSION,
        "overseas_cap": OVERSEAS_STARTER_CAP,
        "playoff_teams": PLAYOFF_TEAMS,
        "trade_deadline_week": 6,
        "waiver_run_weekday": "wednesday",
    }
    code = _invite_code()
    cur = con.execute(
        "INSERT INTO leagues (name, invite_code, season, settings, status)"
        " VALUES (?, ?, '2027', ?, 'setup')",
        (SANDBOX_LEAGUE_NAME, code, json.dumps(settings)),
    )
    league_id = cur.lastrowid

    # Commissioner user + teams.
    comm = con.execute(
        "INSERT INTO users (name, email) VALUES (?, ?)", (MOCK_MANAGERS[0][0], "commish@sandbox.local")
    ).lastrowid
    con.execute("UPDATE leagues SET commissioner_id = ? WHERE id = ?", (comm, league_id))
    team_ids: list[int] = []
    for i, (manager, team_name) in enumerate(MOCK_MANAGERS[:SANDBOX_TEAM_COUNT]):
        owner = con.execute(
            "INSERT INTO users (name) VALUES (?)", (manager,)
        ).lastrowid
        tid = con.execute(
            "INSERT INTO teams (league_id, owner_id, name, faab_remaining) VALUES (?, ?, ?, ?)",
            (league_id, owner, team_name, FAAB_BUDGET),
        ).lastrowid
        team_ids.append(tid)

    # Player universe + roles + preseason ranks (rank = universe order,
    # best predicted first). Every team shares the default board for now.
    universe = _load_universe()
    for rank, p in enumerate(universe, start=1):
        pid = con.execute(
            "INSERT INTO players (name, season) VALUES (?, '2027')", (p["name"],)
        ).lastrowid
        con.execute(
            "INSERT INTO player_roles (player_id, season, role, is_overseas, ipl_team_code, source)"
            " VALUES (?, '2027', ?, ?, ?, 'sandbox')",
            (pid, p["role"], 1 if p["is_overseas"] else 0, p["team"]),
        )
        for tid in team_ids:
            con.execute(
                "INSERT OR IGNORE INTO pre_draft_ranks (team_id, player_id, rank) VALUES (?, ?, ?)",
                (tid, pid, rank),
            )

    # No matchups are seeded here: the real weeks 1-6 H2H schedule is
    # generated at draft completion (services._generate_schedule). Seeding
    # a parallel week-1 set here doubled week-1 matchups in the demo league.
    n = len(team_ids)

    con.commit()
    log.info(f"sandbox seeded: league {league_id} ({SANDBOX_LEAGUE_NAME}), {n} teams, {len(universe)} players")
    return league_id
