/* TS mirrors of api/schemas.py. Field renames are breaking — keep in sync. */

export interface HealthOut {
  status: string;
  version: string;
  sandbox: boolean;
  scoring_table: string;
}

export interface NotImplementedOut {
  detail: string;
  track: string; // e.g. "P2-L1"
}

export interface LeagueSettings {
  draft_type: string;
  rounds: number;
  pick_clock_secs?: number;
  roster_slots: Record<string, number>;
  faab_budget: number;
  scoring_table_version: string;
  overseas_cap: number;
  playoff_teams: number;
  trade_deadline_week: number;
  waiver_run_weekday: string;
}

export interface AdjustmentOut {
  id: number;
  league_id: number;
  team_id: number;
  team_name: string;
  kind: string;
  faab_delta: number;
  faab_after: number;
  note: string;
  created_at: string;
}

export interface LeagueOut {
  id: number;
  name: string;
  invite_code: string;
  season: string;
  status: string;
  settings: LeagueSettings;
}

export interface TeamStandingOut {
  team_id: number;
  team_name: string;
  owner_name: string | null;
  wins: number;
  losses: number;
  ties: number;
  points_for: number;
  faab_remaining: number;
  claimed: boolean;
}

export interface LeagueSummaryOut {
  id: number;
  name: string;
  season: string;
  status: string;
  team_count: number;
}

export interface LeagueDetailOut extends LeagueOut {
  standings: TeamStandingOut[];
  current_week: number;
}

export interface RosterMoveOut {
  id: number;
  league_id: number;
  team_id: number;
  team_name: string;
  kind: "roster_add" | "roster_drop";
  player_id: number;
  player_name: string;
  note: string;
  created_at: string;
}

export interface TeamOut {
  id: number;
  league_id: number;
  name: string;
  owner_name: string | null;
  faab_remaining: number;
  claimed: boolean;
  claim_code?: string | null; // only on join + claim responses
}

export interface ClaimOut {
  team_id: number;
  claim_code: string;
}

export type PlayerRole = "WK" | "BAT" | "AR" | "BOWL";

/** P5-W6: availability dot state from the curated registry status. */
export type Availability = "active" | "out" | "retired";

export interface PlayerOut {
  id: number;
  name: string;
  season: string;
  role: PlayerRole | null;
  is_overseas: boolean;
  ipl_team_code: string | null;
  preseason_rank: number | null;
  owned_by_team_id: number | null;
  availability: Availability;
  avg_points: number | null;
  ownership_pct: number | null;
}

/** P5-W7: one trade-block listing — the player being shopped, the
 * shopping team, and the manager's seeking note. */
export interface TradeBlockEntryOut {
  id: number;
  league_id: number;
  team_id: number;
  team_name: string;
  player_id: number;
  name: string;
  season: string;
  role: PlayerRole | null;
  is_overseas: boolean;
  ipl_team_code: string | null;
  preseason_rank: number | null;
  availability: Availability;
  seeking: string;
  created_at: string;
  updated_at: string;
}

/** P5-W8: one league-activity entry. `amount` is set ONLY for a
 * winning waiver bid (public post-run); losing bids never carry one. */
export interface ActivityEntryOut {
  id: string;
  kind: string;
  text: string;
  team_id: number | null;
  team_name: string | null;
  player_id: number | null;
  player_name: string | null;
  amount: number | null;
  occurred_at: string;
}

export interface ActivityOut {
  league_id: number;
  total: number;
  entries: ActivityEntryOut[];
}

/** P5-W9: power rankings. basis is "roster_value" pre-season
 * (honest roster-value ranking) and "record_blend" once weeks
 * finalize; movement is null until two final weeks exist. */
export interface PowerRankEntryOut {
  rank: number;
  team_id: number;
  team_name: string;
  roster_value: number;
  wins: number;
  losses: number;
  ties: number;
  points_for: number;
  power_score: number;
  movement: number | null;
}

export interface PowerRankingsOut {
  league_id: number;
  basis: "roster_value" | "record_blend";
  through_week: number;
  entries: PowerRankEntryOut[];
}

/** P5-W10: one season-start checklist item, derived server-side
 * from live DB state (never a stored flag). */
export interface ReadinessItemOut {
  key: string;
  label: string;
  done: boolean;
  detail: string;
  fix_href: string;
}

export interface ReadinessOut {
  league_id: number;
  ready_count: number;
  total_count: number;
  items: ReadinessItemOut[];
}

/** P5-W12: all-teams roster view — one team's roster grouped by
 * slot, with its D8 overseas-starter count and FAAB remaining. */
export interface RosterPlayerOut {
  id: number;
  name: string;
  role: PlayerRole | null;
  is_overseas: boolean;
  ipl_team_code: string | null;
  availability: Availability;
}

export interface RosterTeamOut {
  team_id: number;
  team_name: string;
  faab_remaining: number;
  overseas_starters: number;
  roster_size: number;
  slots: Record<string, RosterPlayerOut[]>;
}

export interface RostersOut {
  league_id: number;
  teams: RosterTeamOut[];
}

/** P5-W2: a watched player — PlayerOut plus the watchlist row. */
export interface WatchlistEntryOut extends PlayerOut {
  watch_id: number;
  league_id: number;
  team_id: number;
  created_at: string;
}

/** P5-W14: one column of the player-compare table. */
export interface PlayerCompareEntryOut extends PlayerOut {
  games_next_3_weeks: number | null;
}

export interface PlayerCompareOut {
  league_id: number;
  current_week: number;
  weeks: number[];
  players: PlayerCompareEntryOut[];
}

export interface PlayerOwnerOut {
  league_id: number;
  league_name: string;
  team_id: number;
  team_name: string;
}

export interface PlayerMatchLogOut {
  match_id: number;
  week_no: number | null;
  match_date_ist: string | null;
  home_code: string | null;
  away_code: string | null;
  fantasy_points: number;
  breakdown: Record<string, number>;
}

export interface PlayerDetailOut extends PlayerOut {
  owners: PlayerOwnerOut[];
  matches_played: number;
  total_points: number;
  match_log: PlayerMatchLogOut[];
}

export interface DraftOut {
  id: number;
  league_id: number;
  rounds: number;
  status: string;
  current_pick_no: number; // 1-indexed (engine convention)
  draft_order: number[];
  on_clock_team_id: number | null;
}

export interface DndOut {
  draft_id: number;
  team_id: number;
  dnd: number[];
}

export interface DraftRoomTeam {
  id: number;
  name: string;
}

export interface DraftRoomPick {
  pick_no: number;
  round_no: number;
  team_id: number;
  player_id: number | null;
  is_auto: boolean;
  slot?: string;
}

/** One draft-room chat message (P4-W20). */
export interface ChatMessage {
  seq: number;
  team_id: number;
  team_name: string;
  text: string;
  at: number; // epoch seconds
}

/** Full draft-room snapshot broadcast over the WebSocket (P3-A3). */
export interface DraftRoomState {
  type: "state";
  event?: "pick" | "clock_expired" | "dnd_updated";
  pick?: DraftRoomPick;
  dnd_updated?: DndOut;
  chat?: ChatMessage[];
  draft: {
    id: number;
    league_id: number;
    status: string;
    rounds: number;
    teams: DraftRoomTeam[];
    draft_order: number[];
    seed: number | null;
    pick_clock_secs: number;
  };
  current_pick_no: number;
  total_picks: number;
  on_clock_team_id: number | null;
  pick_deadline: number | null; // epoch seconds
  picks: DraftRoomPick[];
  rosters: Record<string, Record<string, number[]>>;
  dnd: Record<string, number[]>;
}

export interface DraftPickOut {
  pick_no: number;
  round_no: number;
  team_id: number;
  player_id: number | null;
  is_auto: boolean;
}

export interface RanksOut {
  team_id: number;
  player_ids: number[];
}

export interface LineupOut {
  team_id: number;
  week_no: number;
  slots: Record<string, number[]>;
  overseas_starters: number;
  valid: boolean;
  carried_over_from_week: number | null;
  locked: boolean;
  lock_at: string | null;
  /** P5-W6: availability per player in slots, keyed by player id. */
  player_availability: Record<string, Availability>;
}

export interface LineupSuggestionOut extends LineupOut {
  /** P5-W13: honest basis copy for the Suggested XI. */
  basis: string;
}

/** P5-W16: one recommended waiver add for the managing-as team. */
export interface WaiverRecommendationOut {
  player_id: number;
  name: string;
  role: string | null;
  ipl_team_code: string | null;
  is_overseas: boolean;
  availability: Availability;
  preseason_rank: number;
  games_next_3_weeks: number | null;
  upgrade: number;
  score: number;
  drop_player_id: number | null;
  drop_player_name: string | null;
  reason: string;
}

export interface WaiverRecommendationsOut {
  league_id: number;
  team_id: number;
  current_week: number;
  weeks: number[];
  basis: string;
  recommendations: WaiverRecommendationOut[];
}

export interface WaiverRunResultOut {
  player_id: number;
  winner_team_id: number | null;
  amount: number | null;
  drop_player_id: number | null;
  forfeited_by: number[];
}

export interface CantCutOut {
  player_ids: number[];
  source: "custom" | "preseason_top_n" | "off";
  top_n: number;
}

export interface WaiverClaimOut {
  id: number;
  week_no: number;
  team_id: number;
  add_player_id: number;
  drop_player_id: number | null;
  bid: number | null; // null = sealed rival bid (blind FAAB)
  status: string;
}

export interface TradeOut {
  id: number;
  league_id: number;
  from_team_id: number;
  to_team_id: number;
  gives: number[];
  receives: number[];
  status: string;
  review_deadline: string | null;
  veto_count: number;
  proposed_at: string | null;
  accepted_at: string | null;
  vetoed_at: string | null;
  executed_at: string | null;
}

// P5-W1 trade analyzer (read-only projection from pre_draft_ranks + fixture game counts)
export interface TradeSideAnalysisOut {
  team_id: number;
  rank_delta: number | null; // + = incoming rank value better than outgoing (NOT a points projection)
  ranked_players: number;
  unranked_players: number;
  net_games_next_3w: number | null; // + = incoming players play more games
}

export interface TradeAnalysisOut {
  league_id: number;
  from_team_id: number;
  to_team_id: number;
  gives: number[];
  receives: number[];
  weeks: number[];
  sides: TradeSideAnalysisOut[];
  summary: string;
  basis: string;
}

/** P5-L1/P5-W3: ephemeral practice (mock) draft result. */
export interface MockBotIn {
  name: string;
  difficulty: "casual" | "sharp";
}

export interface MockPickOut {
  pick_no: number;
  round_no: number;
  team_name: string;
  difficulty: string;
  player_id: number;
  player_name: string;
  slot: string;
}

export interface MockTeamOut {
  name: string;
  difficulty: string;
  avg_consensus_rank: number;
  roster: Record<string, string[]>; // slot -> player names
}

export interface MockDraftOut {
  league_id: number;
  seed: number;
  rounds: number;
  draft_order: string[];
  teams: MockTeamOut[];
  picks: MockPickOut[];
  schedule_weighted: boolean;
}

/** P5-W4: draft recap + grades (deterministic, from draft + ranks). */
export interface RecapPickOut {
  player_id: number;
  player_name: string;
  team_id: number;
  team_name: string;
  pick_no: number;
  consensus_rank: number;
  delta: number; // pick_no - consensus_rank; + = steal, - = reach
}

export interface RecapTeamOut {
  team_id: number;
  team_name: string;
  grade: string;
  projected_value: number;
  expected_value: number;
  value_ratio: number;
  picks_made: number;
  unranked_picks: number;
  biggest_steal: RecapPickOut | null;
  biggest_reach: RecapPickOut | null;
}

export interface DraftRecapOut {
  league_id: number;
  status: string; // no_draft | scheduled | live | complete
  draft_id: number | null;
  teams: RecapTeamOut[];
  headline_biggest_steal: RecapPickOut | null;
  headline_best_pick: RecapPickOut | null;
  basis: string;
}

/** P5-W5: league message board. */
export interface MessageOut {
  id: number;
  league_id: number;
  team_id: number;
  team_name: string;
  body: string;
  created_at: string;
}

export interface MessageBoardOut {
  league_id: number;
  commissioner_team_id: number | null;
  total: number;
  messages: MessageOut[];
}

export interface MatchupOut {
  id: number;
  week_no: number;
  team_a_id: number;
  team_b_id: number;
  team_a_name: string;
  team_b_name: string;
  score_a: number;
  score_b: number;
  status: string;
}

export interface PlayoffSeedOut {
  seed: number;
  team_id: number;
  team_name: string;
  wins: number;
  losses: number;
  ties: number;
  points_for: number;
}

export interface PlayoffGameOut {
  label: string;
  week_no: number;
  team_a_id: number | null;
  team_a_label: string;
  team_b_id: number | null;
  team_b_label: string;
  score_a: number | null;
  score_b: number | null;
  status: string; // projected | scheduled | final
  winner_team_id: number | null;
}

export interface PlayoffsOut {
  league_id: number;
  stage: string; // regular_season | semifinals | final | complete
  seeds_final: boolean;
  seeds: PlayoffSeedOut[];
  semifinals: PlayoffGameOut[];
  final: PlayoffGameOut | null;
  third_place: PlayoffGameOut | null;
  champion_team_id: number | null;
  champion_team_name: string | null;
}

export interface PlayerScoreOut {
  player_name: string;
  fantasy_points: number;
  breakdown: Record<string, unknown>;
}

export interface ScoreboardOut {
  match_id: number;
  status: string;
  scores: PlayerScoreOut[];
}

export interface TeamGameCount {
  ipl_team_code: string;
  games: number;
}

/** P5-W15: one row of the schedule matrix (games_by_week[0] = week 1). */
export interface ScheduleMatrixRowOut {
  ipl_team_code: string;
  games_by_week: number[];
  total: number;
}

export interface ScheduleMatrixOut {
  league_id: number;
  season: string;
  source: string;
  weeks_available: number[];
  rows: ScheduleMatrixRowOut[];
}

export interface ScheduleNudgesOut {
  league_id: number;
  season: string;
  week_no: number;
  week_start: string | null;
  week_end: string | null;
  source: string;
  weeks_available: number[];
  games: TeamGameCount[];
}

export class ApiError extends Error {
  status: number;
  track?: string;
  constructor(status: number, message: string, track?: string) {
    super(message);
    this.status = status;
    this.track = track;
  }
}
