/* Typed client for the FastAPI backend (blueprint §7).
   Base URL: NEXT_PUBLIC_API_URL (dev default http://127.0.0.1:8014/api).
   Engine endpoints that are still scaffolds return 501 with a {detail, track}
   body — the UI renders the track tag so users know which build owns it. */

import { ApiError } from "./types";
import { claimHeaders } from "./identity";
import type {
  ClaimOut,
  DndOut,
  DraftOut,
  DraftRecapOut,
  DraftPickOut,
  HealthOut,
  AdjustmentOut,
  CantCutOut,
  LeagueDetailOut,
  LeagueOut,
  LeagueSummaryOut,
  LineupOut,
  MatchupOut,
  MessageBoardOut,
  MessageOut,
  MockBotIn,
  MockDraftOut,
  NotImplementedOut,
  PlayerDetailOut,
  PlayerOut,
  PlayoffsOut,
  RanksOut,
  RosterMoveOut,
  ScoreboardOut,
  ScheduleNudgesOut,
  TeamOut,
  TradeAnalysisOut,
  TradeBlockEntryOut,
  TradeOut,
  WaiverClaimOut,
  WaiverRunResultOut,
  WatchlistEntryOut,
} from "./types";

const BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8014/api";

/** WebSocket URL for a draft room (P3-A3). Derives ws(s)://host from the API base. */
export function draftWsUrl(draftId: number | string, teamId: number | string): string {
  const u = new URL(BASE);
  u.protocol = u.protocol === "https:" ? "wss:" : "ws:";
  const basePath = u.pathname.replace(/\/api\/?$/, "");
  return `${u.protocol}//${u.host}${basePath}/api/drafts/${draftId}/ws?team_id=${teamId}`;
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new ApiError(
      res.status,
      (body as { detail?: string }).detail ?? `request failed (${res.status})`,
      (body as NotImplementedOut).track,
    );
  }
  return body as T;
}

export const api = {
  health: () => req<HealthOut>("/health"),

  // leagues
  listLeagues: () => req<LeagueSummaryOut[]>("/leagues"),
  createLeague: (name: string, commissioner_name: string) =>
    req<LeagueOut>("/leagues", { method: "POST", body: JSON.stringify({ name, commissioner_name }) }),
  getLeague: (id: number | string) => req<LeagueDetailOut>(`/leagues/${id}`),
  patchLeagueSettings: (
    id: number | string,
    patch: { pick_clock_secs?: number; trade_deadline_week?: number; waiver_run_weekday?: string },
  ) =>
    req<LeagueOut>(`/leagues/${id}/settings`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    }),
  createAdjustment: (
    id: number | string,
    body: { team_id: number; faab_delta: number; note: string },
  ) =>
    req<AdjustmentOut>(`/leagues/${id}/adjustments`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  listAdjustments: (id: number | string) =>
    req<AdjustmentOut[]>(`/leagues/${id}/adjustments`),
  getCantCut: (leagueId: number | string) => req<CantCutOut>(`/leagues/${leagueId}/cant-cut`),
  rosterMove: (leagueId: number | string, body: { team_id: number; player_id: number; action: "add" | "drop"; note: string }) =>
    req<RosterMoveOut>(`/leagues/${leagueId}/roster-moves`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  listRosterMoves: (leagueId: number | string) =>
    req<RosterMoveOut[]>(`/leagues/${leagueId}/roster-moves`),
  joinLeague: (id: number | string, invite_code: string, team_name: string, owner_name: string) =>
    req<TeamOut>(`/leagues/${id}/join`, {
      method: "POST",
      body: JSON.stringify({ invite_code, team_name, owner_name }),
    }),
  listTeams: (leagueId: number | string) => req<TeamOut[]>(`/leagues/${leagueId}/teams`),
  getPlayoffs: (leagueId: number | string) =>
    req<PlayoffsOut>(`/leagues/${leagueId}/playoffs`),
  scheduleNudges: (leagueId: number | string, week: number) =>
    req<ScheduleNudgesOut>(`/leagues/${leagueId}/schedule-nudges?week_no=${week}`),

  // players
  listPlayers: (params: { league_id: number; season?: string; role?: string; team?: string; q?: string }) => {
    const qs = new URLSearchParams(
      Object.entries(params).reduce<Record<string, string>>((acc, [k, v]) => {
        if (v !== undefined && v !== "") acc[k] = String(v);
        return acc;
      }, {}),
    );
    return req<PlayerOut[]>(`/players?${qs}`);
  },
  getPlayer: (playerId: number | string, league_id: number) =>
    req<PlayerDetailOut>(`/players/${playerId}?league_id=${league_id}`),

  // watchlist (P5-W2): per-team starred players. Reads open; writes
  // carry the acting team's claim header like other mutations.
  listWatchlist: (league_id: number, team_id: number) =>
    req<WatchlistEntryOut[]>(`/watchlist?league_id=${league_id}&team_id=${team_id}`),
  starPlayer: (body: { league_id: number; team_id: number; player_id: number }) =>
    req<WatchlistEntryOut>("/watchlist", {
      method: "POST",
      headers: claimHeaders(body.team_id),
      body: JSON.stringify(body),
    }),
  unstarPlayer: (league_id: number, team_id: number, player_id: number) =>
    req<void>(`/watchlist?league_id=${league_id}&team_id=${team_id}&player_id=${player_id}`, {
      method: "DELETE",
      headers: claimHeaders(team_id),
    }),

  // drafts
  getDraft: (id: number | string) => req<DraftOut>(`/drafts/${id}`),
  getLeagueDraft: (leagueId: number | string) =>
    req<DraftOut>(`/leagues/${leagueId}/draft`).catch((e) => {
      if (e instanceof ApiError && e.status === 404) return null;
      throw e;
    }),
  getDraftRecap: (leagueId: number | string) =>
    req<DraftRecapOut>(`/leagues/${leagueId}/draft-recap`),
  listPicks: (id: number | string) => req<DraftPickOut[]>(`/drafts/${id}/picks`),
  startDraft: (leagueId: number | string) =>
    req<DraftOut>(`/leagues/${leagueId}/draft/start`, { method: "POST" }),
  makePick: (draftId: number | string, team_id: number, player_id: number) =>
    req<DraftPickOut>(`/drafts/${draftId}/pick`, {
      method: "POST",
      body: JSON.stringify({ team_id, player_id }),
    }),
  addDnd: (draftId: number | string, team_id: number, player_id: number) =>
    req<DndOut>(`/drafts/${draftId}/dnd`, {
      method: "POST",
      body: JSON.stringify({ team_id, player_id }),
    }),
  removeDnd: (draftId: number | string, team_id: number, player_id: number) =>
    req<DndOut>(`/drafts/${draftId}/dnd`, {
      method: "DELETE",
      body: JSON.stringify({ team_id, player_id }),
    }),
  getRanks: (teamId: number | string) => req<RanksOut>(`/teams/${teamId}/ranks`),
  setRanks: (teamId: number | string, player_ids: number[]) =>
    req<RanksOut>(`/teams/${teamId}/ranks`, {
      method: "PUT",
      body: JSON.stringify({ player_ids }),
    }),

  // identity (P4-W18): claim/reset a team's claim code
  claimTeam: (teamId: number) =>
    req<ClaimOut>(`/teams/${teamId}/claim`, { method: "POST" }),
  resetClaim: (teamId: number) =>
    req<TeamOut>(`/teams/${teamId}/reset-claim`, { method: "POST" }),

  // lineups
  setLineup: (teamId: number | string, week_no: number, slots: Record<string, number[]>) =>
    req<LineupOut>(`/teams/${teamId}/lineup`, {
      method: "PUT",
      headers: claimHeaders(Number(teamId)),
      body: JSON.stringify({ week_no, slots }),
    }),
  getLineup: (teamId: number | string, week_no: number) =>
    req<LineupOut>(`/teams/${teamId}/lineup?week_no=${week_no}`),

  // waivers
  submitClaim: (body: { league_id: number; team_id: number; add_player_id: number; drop_player_id?: number; bid: number }) =>
    req<WaiverClaimOut>("/waivers/claim", {
      method: "POST",
      headers: claimHeaders(body.team_id),
      body: JSON.stringify(body),
    }),
  pendingClaims: (league_id: number, week_no: number, team_id?: number) =>
    req<WaiverClaimOut[]>(
      `/waivers/pending?league_id=${league_id}&week_no=${week_no}${team_id != null ? `&team_id=${team_id}` : ""}`
    ),
  claimsHistory: (league_id: number, week_no: number) =>
    req<WaiverClaimOut[]>(`/waivers/history?league_id=${league_id}&week_no=${week_no}`),
  runWaivers: (league_id: number, week_no: number) =>
    req<WaiverRunResultOut[]>(`/waivers/run?league_id=${league_id}&week_no=${week_no}`, {
      method: "POST",
    }),

  // trades
  proposeTrade: (body: { league_id: number; from_team_id: number; to_team_id: number; gives: number[]; receives: number[] }) =>
    req<TradeOut>("/trades", {
      method: "POST",
      headers: claimHeaders(body.from_team_id),
      body: JSON.stringify(body),
    }),
  listTrades: (league_id: number, status?: string) =>
    req<TradeOut[]>(`/trades?league_id=${league_id}${status ? `&status=${status}` : ""}`),
  tradeAccept: (tradeId: number, actorTeamId: number) =>
    req<TradeOut>(`/trades/${tradeId}/accept`, {
      method: "POST",
      headers: claimHeaders(actorTeamId),
    }),
  tradeReject: (tradeId: number, actorTeamId: number) =>
    req<TradeOut>(`/trades/${tradeId}/reject`, {
      method: "POST",
      headers: claimHeaders(actorTeamId),
    }),
  tradeVeto: (tradeId: number, teamId: number) =>
    req<TradeOut>(`/trades/${tradeId}/veto?team_id=${teamId}`, {
      method: "POST",
      headers: claimHeaders(teamId),
    }),
  // trade block (P5-W7): league-wide "on the block" board. Reads
  // open; post/remove carry the acting team's claim header and the
  // API only accepts players on that team's own roster.
  listTradeBlock: (league_id: number) =>
    req<TradeBlockEntryOut[]>(`/trade-block?league_id=${league_id}`),
  postTradeBlock: (body: { league_id: number; team_id: number; player_id: number; seeking: string }) =>
    req<TradeBlockEntryOut>("/trade-block", {
      method: "POST",
      headers: claimHeaders(body.team_id),
      body: JSON.stringify(body),
    }),
  removeTradeBlock: (league_id: number, team_id: number, player_id: number) =>
    req<void>(`/trade-block?league_id=${league_id}&team_id=${team_id}&player_id=${player_id}`, {
      method: "DELETE",
      headers: claimHeaders(team_id),
    }),
  analyzeTrade: (args: {
    league_id: number;
    from_team_id: number;
    to_team_id: number;
    gives: number[];
    receives: number[];
  }) =>
    req<TradeAnalysisOut>(
      `/trades/analyze?league_id=${args.league_id}&from_team_id=${args.from_team_id}&to_team_id=${args.to_team_id}&gives=${args.gives.join(",")}&receives=${args.receives.join(",")}`
    ),

  // mock draft (P5-L1/P5-W3): ephemeral practice draft — POST runs it
  // in memory on the server; zero writes to the live league.
  runMockDraft: (leagueId: number, body?: { bots?: MockBotIn[]; seed?: number }) =>
    req<MockDraftOut>(`/mock-draft/${leagueId}`, {
      method: "POST",
      body: JSON.stringify(body ?? {}),
    }),

  // message board (P5-W5): persistent league posts. Reads open;
  // post/delete carry the acting team's claim header (P4-W18).
  getMessageBoard: (leagueId: number, limit = 50, offset = 0) =>
    req<MessageBoardOut>(`/leagues/${leagueId}/messages?limit=${limit}&offset=${offset}`),
  postMessage: (leagueId: number, team_id: number, body: string) =>
    req<MessageOut>(`/leagues/${leagueId}/messages`, {
      method: "POST",
      headers: claimHeaders(team_id),
      body: JSON.stringify({ team_id, body }),
    }),
  deleteMessage: (leagueId: number, messageId: number, team_id: number) =>
    req<void>(`/leagues/${leagueId}/messages/${messageId}?team_id=${team_id}`, {
      method: "DELETE",
      headers: claimHeaders(team_id),
    }),

  // matchups / scoring
  listMatchups: (league_id: number, week_no: number) =>
    req<MatchupOut[]>(`/matchups?league_id=${league_id}&week_no=${week_no}`),
  scoreboard: (matchId: number | string) => req<ScoreboardOut>(`/matchups/scoreboard/${matchId}`),
  scoreMatch: (match_id: number) =>
    req<NotImplementedOut>("/admin/score-match", { method: "POST", body: JSON.stringify({ match_id }) }),
};
