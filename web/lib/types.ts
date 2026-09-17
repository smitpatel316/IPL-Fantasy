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
  roster_slots: Record<string, number>;
  faab_budget: number;
  scoring_table_version: string;
  overseas_cap: number;
  playoff_teams: number;
  trade_deadline_week: number;
  waiver_run_weekday: string;
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
}

export interface LeagueDetailOut extends LeagueOut {
  standings: TeamStandingOut[];
}

export interface TeamOut {
  id: number;
  league_id: number;
  name: string;
  owner_name: string | null;
  faab_remaining: number;
}

export type PlayerRole = "WK" | "BAT" | "AR" | "BOWL";

export interface PlayerOut {
  id: number;
  name: string;
  season: string;
  role: PlayerRole | null;
  is_overseas: boolean;
  ipl_team_code: string | null;
  preseason_rank: number | null;
  owned_by_team_id: number | null;
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

/** Full draft-room snapshot broadcast over the WebSocket (P3-A3). */
export interface DraftRoomState {
  type: "state";
  event?: "pick" | "clock_expired" | "dnd_updated";
  pick?: DraftRoomPick;
  dnd_updated?: DndOut;
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

export interface LineupOut {
  team_id: number;
  week_no: number;
  slots: Record<string, number[]>;
  overseas_starters: number;
  valid: boolean;
}

export interface WaiverClaimOut {
  id: number;
  week_no: number;
  team_id: number;
  add_player_id: number;
  drop_player_id: number | null;
  bid: number;
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
