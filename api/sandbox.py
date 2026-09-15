"""Deterministic sandbox seed: one demo league, 8 teams, 48 mock players
(4 mock IPL franchises x 12) with roles/overseas flags and preseason ranks.
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

# (name, role, is_overseas) x12 per franchise — a plausible T20 squad shape.
MOCK_SQUADS: dict[str, list[tuple[str, str, bool]]] = {
    "MI": [
        ("R Sharma", "BAT", False), ("I Kishan", "WK", False),
        ("S Yadav", "BAT", False), ("T Varma", "BAT", False),
        ("H Pandya", "AR", False), ("K Pollard", "AR", True),
        ("J Bumrah", "BOWL", False), ("T Boult", "BOWL", True),
        ("R Khan", "BOWL", True), ("D Santner", "AR", True),
        ("N Dhir", "BAT", False), ("A Madhwal", "BOWL", False),
    ],
    "CSK": [
        ("R Gaikwad", "BAT", False), ("D Conway", "WK", True),
        ("S Dube", "BAT", False), ("R Jadeja", "AR", False),
        ("M Ali", "AR", True), ("MS Dhoni", "WK", False),
        ("D Chahar", "BOWL", False), ("M Pathirana", "BOWL", True),
        ("R Ashwin", "AR", False), ("N Ahmad", "BOWL", True),
        ("S Curran", "AR", True), ("T Deshpande", "BOWL", False),
    ],
    "RCB": [
        ("V Kohli", "BAT", False), ("P Salt", "WK", True),
        ("R Patidar", "BAT", False), ("L Livingstone", "AR", True),
        ("K Pandya", "AR", False), ("T David", "BAT", True),
        ("J Hazlewood", "BOWL", True), ("B Kumar", "BOWL", False),
        ("Y Dayal", "BOWL", False), ("S Sharma", "BOWL", False),
        ("R Singh", "BAT", False), ("M Bhandage", "AR", False),
    ],
    "KKR": [
        ("Q de Kock", "WK", True), ("A Raghuvanshi", "BAT", False),
        ("A Russell", "AR", True), ("M Singh", "BAT", False),
        ("S Narine", "AR", True), ("R Rinku", "BAT", False),
        ("V Chakravarthy", "BOWL", False), ("H Rana", "BOWL", False),
        ("S Iyer", "AR", False), ("M Starc", "BOWL", True),
        ("M Pandey", "BAT", False), ("V Arora", "BOWL", False),
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
        "roster_slots": {"WK": 1, "BAT": 3, "AR": 2, "BOWL": 3, "UTIL": 1, "BN": 4, "IL": 1},
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

    # Week-1 round-robin matchups (team i vs team n-1-i).
    n = len(team_ids)
    for i in range(n // 2):
        con.execute(
            "INSERT INTO matchups (league_id, week_no, team_a_id, team_b_id, status)"
            " VALUES (?, 1, ?, ?, 'scheduled')",
            (league_id, team_ids[i], team_ids[n - 1 - i]),
        )

    con.commit()
    log.info(f"sandbox seeded: league {league_id} ({SANDBOX_LEAGUE_NAME}), {n} teams, 48 players")
    return league_id
