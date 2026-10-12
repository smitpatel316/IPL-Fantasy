"""Pydantic v2 contracts for the v1 API surface (blueprint §7).
League-core builds against these — field renames are breaking changes; discuss first."""

from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------- generic ----------
class HealthOut(BaseModel):
    status: str = "ok"
    version: str
    sandbox: bool
    scoring_table: str


class NotImplementedOut(BaseModel):
    detail: str = "not implemented in scaffold"
    track: str  # e.g. "P2-L1" — which league-core item owns it


# ---------- leagues ----------
class LeagueCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    commissioner_name: str = Field(min_length=1, max_length=80)
    season: str = "2027"


class LeagueOut(BaseModel):
    id: int
    name: str
    invite_code: str
    season: str
    status: str
    settings: dict[str, Any]


class LeagueSummaryOut(BaseModel):
    id: int
    name: str
    season: str
    status: str
    team_count: int


class LeagueDetailOut(LeagueOut):
    standings: list["TeamStandingOut"]
    # P4-W21: the week the league is currently playing (last final + 1,
    # capped at TOTAL_WEEKS) — drives the dashboard "my matchup" strip.
    current_week: int = 1


class TeamStandingOut(BaseModel):
    team_id: int
    team_name: str
    owner_name: Optional[str]
    wins: int = 0
    losses: int = 0
    ties: int = 0
    points_for: float = 0.0
    faab_remaining: int
    claimed: bool = False  # P4-W18: a claim code is set for this team


class JoinLeagueIn(BaseModel):
    invite_code: str
    team_name: str = Field(min_length=1, max_length=80)
    owner_name: str = Field(min_length=1, max_length=80)


class LeagueSettingsPatch(BaseModel):
    """Commissioner-editable settings (P4-W15). Only keys that stay
    meaningful after league creation are patchable; structural choices
    (rounds, roster slots, scoring table) are creation-time decisions."""
    pick_clock_secs: Optional[int] = Field(default=None, ge=0, le=600)
    trade_deadline_week: Optional[int] = Field(default=None, ge=1, le=8)
    waiver_run_weekday: Optional[str] = Field(
        default=None,
        pattern="^(monday|tuesday|wednesday|thursday|friday|saturday|sunday)$",
    )


class AdjustmentCreate(BaseModel):
    team_id: int
    faab_delta: int = Field(ge=-1000, le=1000)
    note: str = Field(min_length=1, max_length=200)


class AdjustmentOut(BaseModel):
    id: int
    league_id: int
    team_id: int
    team_name: str
    kind: str
    faab_delta: int
    faab_after: int
    note: str
    created_at: str


class TeamOut(BaseModel):
    id: int
    league_id: int
    name: str
    owner_name: Optional[str]
    faab_remaining: int
    claimed: bool = False
    # Only ever populated on the join + claim responses (the moment the
    # owner receives their code) — never on list/read endpoints.
    claim_code: Optional[str] = None


class ClaimOut(BaseModel):
    team_id: int
    claim_code: str


# ---------- players ----------
class PlayerOut(BaseModel):
    id: int
    name: str
    season: str
    role: Optional[str]  # WK | BAT | AR | BOWL
    is_overseas: bool = False
    ipl_team_code: Optional[str]
    preseason_rank: Optional[int]
    owned_by_team_id: Optional[int]  # None = free agent
    # P4-W19: None until scoring lands (no player_match_stats rows yet).
    avg_points: Optional[float] = None
    # Share of leagues (0-100) in which the player is rostered.
    ownership_pct: Optional[float] = None


class PlayerOwnerOut(BaseModel):
    league_id: int
    league_name: str
    team_id: int
    team_name: str


class PlayerMatchLogOut(BaseModel):
    match_id: int
    week_no: Optional[int]
    match_date_ist: Optional[str]
    home_code: Optional[str]
    away_code: Optional[str]
    fantasy_points: int
    breakdown: dict = {}


class PlayerDetailOut(PlayerOut):
    owners: list[PlayerOwnerOut] = []  # across every league
    matches_played: int = 0
    total_points: int = 0
    match_log: list[PlayerMatchLogOut] = []


# ---------- drafts ----------
class DraftOut(BaseModel):
    id: int
    league_id: int
    rounds: int
    status: str  # scheduled | live | complete
    current_pick_no: int  # 1-indexed pick number (engine convention)
    draft_order: list[int]
    on_clock_team_id: Optional[int] = None  # None when draft complete


class DraftPickOut(BaseModel):
    pick_no: int
    round_no: int
    team_id: int
    player_id: Optional[int]
    is_auto: bool


class PickCreate(BaseModel):
    team_id: int
    player_id: int


class DndIn(BaseModel):
    team_id: int
    player_id: int


class DndOut(BaseModel):
    draft_id: int
    team_id: int
    dnd: list[int]


class RanksIn(BaseModel):
    player_ids: list[int]


class RanksOut(BaseModel):
    team_id: int
    player_ids: list[int]


# ---------- lineups ----------
class LineupSet(BaseModel):
    week_no: int = Field(ge=1, le=8)
    slots: dict[str, list[int]]  # {"WK": [pid], "BAT": [pid,...], ...}


class LineupOut(BaseModel):
    team_id: int
    week_no: int
    slots: dict[str, list[int]]
    overseas_starters: int
    valid: bool
    # Set on GET when no lineup is saved for week_no yet: the slots are
    # carried over from this earlier week's saved lineup (P4-W5).
    carried_over_from_week: Optional[int] = None


# ---------- waivers ----------
class WaiverClaimCreate(BaseModel):
    league_id: int
    team_id: int
    add_player_id: int
    drop_player_id: Optional[int] = None
    bid: int = Field(ge=0)


class WaiverClaimOut(BaseModel):
    id: int
    week_no: int
    team_id: int
    add_player_id: int
    drop_player_id: Optional[int]
    bid: Optional[int]  # null = sealed rival bid (blind FAAB, D6)
    status: str  # pending | won | lost


class WaiverRunResultOut(BaseModel):
    player_id: int
    winner_team_id: Optional[int]
    amount: Optional[int]
    drop_player_id: Optional[int]
    forfeited_by: list[int] = []


# ---------- trades ----------
class TradeCreate(BaseModel):
    league_id: int
    from_team_id: int
    to_team_id: int
    gives: list[int]
    receives: list[int]


class TradeOut(BaseModel):
    id: int
    league_id: int
    from_team_id: int
    to_team_id: int
    gives: list[int]
    receives: list[int]
    status: str  # proposed | accepted | rejected | vetoed | expired
    review_deadline: Optional[str]
    # History detail (P4-W1): veto votes cast + lifecycle timestamps (ISO UTC).
    veto_count: int = 0
    proposed_at: Optional[str] = None
    accepted_at: Optional[str] = None
    vetoed_at: Optional[str] = None
    executed_at: Optional[str] = None


# ---------- matchups / scoring ----------
class MatchupOut(BaseModel):
    id: int
    week_no: int
    team_a_id: int
    team_b_id: int
    team_a_name: str
    team_b_name: str
    score_a: float
    score_b: float
    status: str  # scheduled | live | final


class PlayoffSeedOut(BaseModel):
    seed: int
    team_id: int
    team_name: str
    wins: int
    losses: int
    ties: int
    points_for: float


class PlayoffGameOut(BaseModel):
    label: str  # "Semifinal 1" | "Semifinal 2" | "Final" | "Third-place game"
    week_no: int
    team_a_id: Optional[int] = None
    team_a_label: str  # team name, or "Winner of Semifinal 1" while undecided
    team_b_id: Optional[int] = None
    team_b_label: str
    score_a: Optional[float] = None
    score_b: Optional[float] = None
    status: str  # projected | scheduled | final
    winner_team_id: Optional[int] = None


class PlayoffsOut(BaseModel):
    league_id: int
    # regular_season | semifinals | final | complete
    stage: str
    seeds_final: bool  # False while the regular season is still running
    seeds: list[PlayoffSeedOut]
    semifinals: list[PlayoffGameOut]
    final: Optional[PlayoffGameOut] = None
    third_place: Optional[PlayoffGameOut] = None
    champion_team_id: Optional[int] = None
    champion_team_name: Optional[str] = None


class PlayerScoreOut(BaseModel):
    player_name: str
    fantasy_points: int
    breakdown: dict[str, Any]


class ScoreboardOut(BaseModel):
    match_id: int
    status: str
    scores: list[PlayerScoreOut]


class ScoreMatchIn(BaseModel):
    match_id: int


class TeamGameCount(BaseModel):
    ipl_team_code: str
    games: int


class ScheduleNudgesOut(BaseModel):
    league_id: int
    season: str
    week_no: int
    week_start: Optional[str] = None
    week_end: Optional[str] = None
    source: str = ""
    weeks_available: list[int] = []
    games: list[TeamGameCount] = []
