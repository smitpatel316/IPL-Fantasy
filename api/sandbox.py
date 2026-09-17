"""Deterministic sandbox seed: one demo league, 8 teams, 48 players
(the current IPL 2026 squads of 4 franchises x 12, trimmed to the
fantasy-relevant core) with roles/overseas flags and preseason ranks.
Mirrors nba-fantasy-ai's SANDBOX_MODE: the UI shell and engine dev never need
live data. Idempotent — only seeds when the leagues table is empty."""

import json
import logging
import secrets
import string

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

# 4 mock franchises (team-agnostic per blueprint §10 risk table — never hardcode 10).
MOCK_FRANCHISES = [
    ("MI", "Mumbai Indians"),
    ("CSK", "Chennai Super Kings"),
    ("RCB", "Royal Challengers Bengaluru"),
    ("KKR", "Kolkata Knight Riders"),
]

# (name, role, is_overseas) x12 per franchise — the current IPL 2026 squads
# (post Dec-2025 mini-auction), trimmed to 12 fantasy-relevant players each.
# Refreshed 2026-09-16; retired players (Pollard, Ashwin, Russell) removed and
# team assignments corrected (de Kock KKR->MI, Curran/Deshpande CSK->RR, ...).
MOCK_SQUADS: dict[str, list[tuple[str, str, bool]]] = {
    "MI": [
        ("R Sharma", "BAT", False), ("R Rickelton", "WK", True),
        ("S Yadav", "BAT", False), ("T Varma", "BAT", False),
        ("H Pandya", "AR", False), ("M Santner", "AR", True),
        ("J Bumrah", "BOWL", False), ("T Boult", "BOWL", True),
        ("D Chahar", "BOWL", False), ("Q de Kock", "WK", True),
        ("W Jacks", "BAT", True), ("S Thakur", "AR", False),
    ],
    "CSK": [
        ("R Gaikwad", "BAT", False), ("S Samson", "WK", False),
        ("MS Dhoni", "WK", False), ("S Dube", "AR", False),
        ("D Brevis", "BAT", True), ("J Overton", "AR", True),
        ("N Ahmad", "BOWL", True), ("K Ahmed", "BOWL", False),
        ("M Henry", "BOWL", True), ("A Hosein", "BOWL", True),
        ("M Short", "AR", True), ("R Chahar", "BOWL", False),
    ],
    "RCB": [
        ("V Kohli", "BAT", False), ("R Patidar", "BAT", False),
        ("D Padikkal", "BAT", False), ("P Salt", "WK", True),
        ("J Sharma", "WK", False), ("K Pandya", "AR", False),
        ("T David", "BAT", True), ("R Shepherd", "AR", True),
        ("J Hazlewood", "BOWL", True), ("B Kumar", "BOWL", False),
        ("J Bethell", "AR", True), ("V Iyer", "AR", False),
    ],
    "KKR": [
        ("A Rahane", "BAT", False), ("A Raghuvanshi", "BAT", False),
        ("R Singh", "BAT", False), ("S Narine", "AR", True),
        ("V Chakravarthy", "BOWL", False), ("C Green", "AR", True),
        ("M Pathirana", "BOWL", True), ("M Rahman", "BOWL", True),
        ("R Ravindra", "AR", True), ("H Rana", "BOWL", False),
        ("R Powell", "AR", True), ("F Allen", "WK", True),
    ],
}

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

    # Player universe + roles + preseason ranks (rank = insertion order).
    rank = 1
    for fcode, _fname in MOCK_FRANCHISES:
        for name, role, overseas in MOCK_SQUADS[fcode]:
            pid = con.execute(
                "INSERT INTO players (name, season) VALUES (?, '2027')", (name,)
            ).lastrowid
            con.execute(
                "INSERT INTO player_roles (player_id, season, role, is_overseas, ipl_team_code, source)"
                " VALUES (?, '2027', ?, ?, ?, 'sandbox')",
                (pid, role, 1 if overseas else 0, fcode),
            )
            # League-wide preseason rank: every team shares the default board for now.
            for tid in team_ids:
                con.execute(
                    "INSERT OR IGNORE INTO pre_draft_ranks (team_id, player_id, rank) VALUES (?, ?, ?)",
                    (tid, pid, rank),
                )
            rank += 1

    # No matchups are seeded here: the real weeks 1-6 H2H schedule is
    # generated at draft completion (services._generate_schedule). Seeding
    # a parallel week-1 set here doubled week-1 matchups in the demo league.
    n = len(team_ids)

    con.commit()
    log.info(f"sandbox seeded: league {league_id} ({SANDBOX_LEAGUE_NAME}), {n} teams, 48 players")
    return league_id
