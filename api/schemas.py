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


class LeagueDetailOut(LeagueOut):
    standings: list["TeamStandingOut"]


class TeamStandingOut(BaseModel):
    team_id: int
    team_name: str
    owner_name: Optional[str]
    wins: int = 0
    losses: int = 0
    ties: int = 0
    points_for: float = 0.0
    faab_remaining: int


class JoinLeagueIn(BaseModel):
    invite_code: str
    team_name: str = Field(min_length=1, max_length=80)
    owner_name: str = Field(min_length=1, max_length=80)


class TeamOut(BaseModel):
    id: int
    league_id: int
    name: str
    owner_name: Optional[str]
    faab_remaining: int


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
    bid: int
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
