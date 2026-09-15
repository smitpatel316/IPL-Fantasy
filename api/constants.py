"""League-wide constants. D1–D11 are the constitution (DECISIONS.md, locked 2026-09-15);
these values encode them. Changing any of them needs Smit (chair)."""

# D7 — roster slots. Chair ruling 2026-09-15: 11 starters via a second UTIL slot
# (WK×1, BAT×3, AR×2, BOWL×3, UTIL×2; BN×3, IL×1 = 15 total). STARTER_SLOTS
# drives validation.
ROSTER_SLOTS: dict[str, int] = {
    "WK": 1,
    "BAT": 3,
    "AR": 2,
    "BOWL": 3,
    "UTIL": 2,
    "BN": 3,
    "IL": 1,
}
STARTER_SLOTS = ["WK", "BAT", "AR", "BOWL", "UTIL"]
BENCH_SLOTS = ["BN"]
IL_SLOTS = ["IL"]

ROSTER_SIZE = sum(ROSTER_SLOTS.values())  # 15

# A player's role may fill these lineup slots (UTIL is the flex).
SLOT_ELIGIBILITY: dict[str, list[str]] = {
    "WK": ["WK"],
    "BAT": ["BAT"],
    "AR": ["AR"],
    "BOWL": ["BOWL"],
    "UTIL": ["WK", "BAT", "AR", "BOWL"],
    "BN": ["WK", "BAT", "AR", "BOWL"],
    "IL": ["WK", "BAT", "AR", "BOWL"],
}

# D8 — max 4 overseas players among starters (mirrors IPL playing conditions 1.2.5/1.2.6).
OVERSEAS_STARTER_CAP = 4

# D6 — weekly blind FAAB, $100 season budget.
FAAB_BUDGET = 100

# D2/D7 — snake draft, 15 rounds (one per roster spot).
DRAFT_ROUNDS = 15

# D4/D9 — fantasy weeks 1–6 regular season, 7–8 playoffs (top 4).
REGULAR_SEASON_WEEKS = [1, 2, 3, 4, 5, 6]
PLAYOFF_WEEKS = [7, 8]
PLAYOFF_TEAMS = 4
TOTAL_WEEKS = 8

# D3 — Dream11-official T20 table, no captain/VC multipliers.
# Versioned: if Dream11 tweaks the table for 2027, bump and keep history.
SCORING_TABLE_VERSION = "dream11-t20-2026-v1"

# Draft universe roles (season-scoped via player_roles).
PLAYER_ROLES = ["WK", "BAT", "AR", "BOWL"]

# Sandbox mode: deterministic mock league/data for UI + engine development
# without any live provider. Mirrors nba-fantasy-ai's SANDBOX_MODE pattern.
SANDBOX_LEAGUE_NAME = "Sandbox Premier League"
SANDBOX_TEAM_COUNT = 8
