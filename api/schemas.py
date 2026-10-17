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
class RosterMoveCreate(BaseModel):
    team_id: int
    player_id: int
    action: str = Field(pattern="^(add|drop)$")
    note: str = Field(min_length=1, max_length=200)


class RosterMoveOut(BaseModel):
    id: int
    league_id: int
    team_id: int
    team_name: str
    kind: str  # roster_add | roster_drop
    player_id: int
    player_name: str
    note: str
    created_at: str


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
    # P5-W6: availability dot state from the curated player_roles.status
    # (active | out | retired) until the live poller lands.
    availability: str = "active"
    # P4-W19: None until scoring lands (no player_match_stats rows yet).
    avg_points: Optional[float] = None
    # Share of leagues (0-100) in which the player is rostered.
    ownership_pct: Optional[float] = None


class PlayerCompareEntryOut(PlayerOut):
    # P5-W14: games for the player's IPL team over the next 3 fantasy
    # weeks (from the schedule-nudges table); None when no fixture has
    # been imported for those weeks.
    games_next_3_weeks: Optional[int] = None


class PlayerCompareOut(BaseModel):
    league_id: int
    current_week: int
    weeks: list[int] = []  # the fantasy weeks games_next_3_weeks covers
    players: list[PlayerCompareEntryOut] = []


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


# ---------- mock draft (P5-L1) ----------
class MockBotIn(BaseModel):
    name: str
    difficulty: str  # "casual" | "sharp" (locked ladder, engine-validated)


class MockDraftIn(BaseModel):
    bots: list[MockBotIn] = []  # empty -> 8 default bots (sharp/casual alternating)
    seed: Optional[int] = None  # None -> 42 (deterministic default)


class MockPickOut(BaseModel):
    pick_no: int
    round_no: int
    team_name: str
    difficulty: str
    player_id: int
    player_name: str
    slot: str


class MockTeamOut(BaseModel):
    name: str
    difficulty: str
    avg_consensus_rank: float
    roster: dict[str, list[str]]  # slot -> player names


class MockDraftOut(BaseModel):
    league_id: int
    seed: int
    rounds: int
    draft_order: list[str]
    teams: list[MockTeamOut]
    picks: list[MockPickOut]
    schedule_weighted: bool  # False when no fixture data existed (honest no-data)


# ---------- draft recap + grades (P5-W4) ----------
class RecapPickOut(BaseModel):
    player_id: int
    player_name: str
    team_id: int
    team_name: str
    pick_no: int
    consensus_rank: int
    delta: int  # pick_no - consensus_rank; + = steal, - = reach


class RecapTeamOut(BaseModel):
    team_id: int
    team_name: str
    grade: str  # A-F, from value_ratio bands (see routers/leagues.py)
    projected_value: int
    expected_value: int
    value_ratio: float
    picks_made: int
    unranked_picks: int
    biggest_steal: Optional[RecapPickOut] = None
    biggest_reach: Optional[RecapPickOut] = None


class DraftRecapOut(BaseModel):
    league_id: int
    status: str  # no_draft | scheduled | live | complete
    draft_id: Optional[int] = None
    teams: list[RecapTeamOut] = []
    headline_biggest_steal: Optional[RecapPickOut] = None
    headline_best_pick: Optional[RecapPickOut] = None
    basis: str = ""


# ---------- league message board (P5-W5) ----------
class MessageCreate(BaseModel):
    team_id: int
    body: str = Field(min_length=1, max_length=500)


class MessageOut(BaseModel):
    id: int
    league_id: int
    team_id: int
    team_name: str
    body: str
    created_at: str


class MessageBoardOut(BaseModel):
    league_id: int
    commissioner_team_id: Optional[int] = None
    total: int
    messages: list[MessageOut] = []


# ---------- league activity feed (P5-W8) ----------
class ActivityEntryOut(BaseModel):
    """One projected league event. `amount` is set ONLY for a winning
    waiver bid (public once the run executes, D6); it is None for
    every other kind — losing bids never carry an amount."""
    id: str  # stable, source-prefixed: pick- / waiver- / trade- / adj-
    kind: str  # draft_pick | waiver_won | waiver_lost | trade_executed
    #          | trade_vetoed | commissioner_faab | commissioner_roster_*
    text: str
    team_id: Optional[int] = None
    team_name: Optional[str] = None
    player_id: Optional[int] = None
    player_name: Optional[str] = None
    amount: Optional[int] = None
    occurred_at: str


class ActivityOut(BaseModel):
    league_id: int
    total: int
    entries: list[ActivityEntryOut] = []
# ---------- team notifications inbox (P5-W20) ----------
class NotificationEntryOut(BaseModel):
    """One 'for you' event. `amount` is set ONLY for the team's own
    WON waiver claim (its own bid, public post-run, D6); never for a
    lost claim and never for another team's claim."""
    id: str
    kind: str  # trade_proposed|trade_accepted|trade_executed|trade_vetoed
    #          | trade_rejected|trade_expired|waiver_won|waiver_lost
    #          | commissioner_faab|commissioner_roster_add|commissioner_roster_drop
    text: str
    amount: Optional[int] = None
    occurred_at: str
    read: bool = False


class NotificationsOut(BaseModel):
    league_id: int
    team_id: int
    total: int
    unread_count: int
    entries: list[NotificationEntryOut] = []
# ---------- power rankings (P5-W9) ----------
class PowerRankEntryOut(BaseModel):
    rank: int
    team_id: int
    team_name: str
    roster_value: int
    wins: int = 0
    losses: int = 0
    ties: int = 0
    points_for: float = 0.0
    power_score: float
    # Rank change vs the previous computed week (positive = climbed);
    # None until two final weeks exist.
    movement: Optional[int] = None


class PowerRankingsOut(BaseModel):
    league_id: int
    basis: str  # roster_value (pre-season) | record_blend
    through_week: int  # last final week included; 0 = none yet
    entries: list[PowerRankEntryOut] = []
# ---------- season-start readiness (P5-W10) ----------
class ReadinessItemOut(BaseModel):
    key: str
    label: str
    done: bool
    detail: str
    fix_href: str


class ReadinessOut(BaseModel):
    league_id: int
    ready_count: int
    total_count: int
    items: list[ReadinessItemOut] = []
# ---------- all-teams rosters (P5-W12) ----------
class RosterPlayerOut(BaseModel):
    id: int
    name: str
    role: Optional[str]
    is_overseas: bool = False
    ipl_team_code: Optional[str]
    availability: str = "active"


class RosterTeamOut(BaseModel):
    team_id: int
    team_name: str
    faab_remaining: int
    overseas_starters: int
    roster_size: int
    slots: dict[str, list[RosterPlayerOut]] = {}


class RostersOut(BaseModel):
    league_id: int
    teams: list[RosterTeamOut] = []


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
    # D5 weekly lock state for this week (P4-W8): lock_at is the week's
    # first-ball instant (ISO, UTC) when known.
    locked: bool = False
    lock_at: Optional[str] = None
    # P5-W6: availability (active | out | retired) for every player in
    # slots, keyed by player_id — the lineup page dots each slot from
    # this map (players not in it default to 'active').
    player_availability: dict[int, str] = {}


class LineupSuggestionOut(LineupOut):
    # P5-W13: honest basis copy for the Suggested XI — the suggestion is
    # the exact best-ADP D8-legal solver over preseason ranks; there is
    # no scoring/projection model behind it.
    basis: str = (
        "Best XI by preseason rank — the exact D8-legal solver over this"
        " roster's pre-draft ranks. No scoring model."
    )
# ---------- player notes (P5-W17) ----------
class PlayerNoteOut(BaseModel):
    id: int
    league_id: int
    team_id: int
    player_id: int
    player_name: str
    note: str
    updated_at: str


class PlayerNoteUpsert(BaseModel):
    league_id: int
    team_id: int
    player_id: int
    note: str


# ---------- watchlist (P5-W2) ----------
class WatchlistCreate(BaseModel):
    league_id: int
    team_id: int
    player_id: int


class WatchlistEntryOut(PlayerOut):
    """A watched player, shaped like PlayerOut (same ownership/avg
    derivation as the players list — numbers always agree) plus the
    watchlist row id + when it was starred."""
    watch_id: int
    league_id: int
    team_id: int
    created_at: str


# ---------- trade block (P5-W7) ----------
class TradeBlockCreate(BaseModel):
    league_id: int
    team_id: int
    player_id: int
    seeking: str = Field(default="", max_length=200)


class TradeBlockEntryOut(BaseModel):
    """One "on the block" listing: the player, the shopping team, and
    the manager's seeking note. Player fields mirror PlayerOut."""
    id: int  # listing id
    league_id: int
    team_id: int
    team_name: str
    player_id: int
    name: str
    season: str
    role: Optional[str]
    is_overseas: bool = False
    ipl_team_code: Optional[str]
    preseason_rank: Optional[int] = None
    availability: str = "active"
    seeking: str = ""
    created_at: str
    updated_at: str


# ---------- waivers ----------
class WaiverClaimCreate(BaseModel):
    league_id: int
    team_id: int
    add_player_id: int
    drop_player_id: Optional[int] = None
    bid: int = Field(ge=0)


class WaiverRecommendationOut(BaseModel):
    # P5-W16: one recommended add for the requesting team. upgrade is
    # rank value gained over the suggested drop piece (weakest rank -
    # FA rank, value = pool-rank convention as in the draft recap);
    # score = upgrade + games_next_3_weeks (1 per game) when the
    # fixture exists, else upgrade alone.
    player_id: int
    name: str
    role: Optional[str] = None
    ipl_team_code: Optional[str] = None
    is_overseas: bool = False
    availability: str = "active"
    preseason_rank: int
    games_next_3_weeks: Optional[int] = None
    upgrade: int
    score: int
    drop_player_id: Optional[int] = None  # None = open roster spot
    drop_player_name: Optional[str] = None
    reason: str


class WaiverRecommendationsOut(BaseModel):
    league_id: int
    team_id: int
    current_week: int
    weeks: list[int] = []
    basis: str
    recommendations: list[WaiverRecommendationOut] = []


class WaiverClaimOut(BaseModel):
    id: int
    week_no: int
    team_id: int
    add_player_id: int
    drop_player_id: Optional[int]
    bid: Optional[int]  # null = sealed rival bid (blind FAAB, D6)
    status: str  # pending | won | lost


class CantCutOut(BaseModel):
    player_ids: list[int]
    source: str  # custom | preseason_top_n | off
    top_n: int


class CantCutIn(BaseModel):
    # Fields actually sent are written; player_ids=null clears the
    # custom list (back to the top-N default), [] turns the list off.
    player_ids: Optional[list[int]] = None
    top_n: Optional[int] = None


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


class TradeSideAnalysis(BaseModel):
    """One side's read-only projection (P5-W1)."""

    team_id: int
    # Rank-implied value swing: sum(preseason rank of outgoing) minus
    # sum(preseason rank of incoming). Lower rank = better, so a positive
    # delta means the team trades UP in rank value. Rank-based only —
    # no scoring model exists yet, so this is NOT a points projection.
    rank_delta: Optional[int] = None
    ranked_players: int = 0
    unranked_players: int = 0
    # Schedule luck: (games incoming players play) - (games outgoing players
    # play) over the next 3 fantasy weeks, from the P3-A6 game-count table.
    net_games_next_3w: Optional[int] = None


class TradeFinderPlayerOut(BaseModel):
    player_id: int
    name: str
    role: Optional[str] = None
    preseason_rank: Optional[int] = None


class TradeFinderSuggestionOut(BaseModel):
    partner_team_id: int
    partner_team_name: str
    give: TradeFinderPlayerOut  # the requesting team's surplus player
    receive: TradeFinderPlayerOut  # the partner's surplus player
    give_role: str
    receive_role: str
    on_trade_block: bool = False  # partner listed the receive player
    reason: str


class TradeFinderOut(BaseModel):
    league_id: int
    team_id: int
    basis: str
    suggestions: list[TradeFinderSuggestionOut] = []


class TradeAnalysisOut(BaseModel):
    """Read-only trade impact projection (P5-W1)."""

    league_id: int
    from_team_id: int
    to_team_id: int
    gives: list[int]
    receives: list[int]
    weeks: list[int]
    sides: list[TradeSideAnalysis]
    summary: str
    basis: str


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


class ScheduleMatrixRowOut(BaseModel):
    ipl_team_code: str
    games_by_week: list[int] = []  # index 0 = fantasy week 1
    total: int = 0


class ScheduleMatrixOut(BaseModel):
    # P5-W15: the whole schedule-nudges table at once — one row per IPL
    # team, one cell per fantasy week (0 = bye week that week).
    league_id: int
    season: str
    source: str = ""
    weeks_available: list[int] = []
    rows: list[ScheduleMatrixRowOut] = []


class ScheduleNudgesOut(BaseModel):
    league_id: int
    season: str
    week_no: int
    week_start: Optional[str] = None
    week_end: Optional[str] = None
    source: str = ""
    weeks_available: list[int] = []
    games: list[TeamGameCount] = []
