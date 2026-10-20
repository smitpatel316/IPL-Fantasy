/* Typed client for the FastAPI backend (blueprint §7).
   Base URL: NEXT_PUBLIC_API_URL (dev default http://127.0.0.1:8014/api).
   Engine endpoints that are still scaffolds return 501 with a {detail, track}
   body — the UI renders the track tag so users know which build owns it. */

import { ApiError } from "./types";
import { claimHeaders } from "./identity";
import type {
  ActivityOut,
  NotificationsOut,
  ClaimOut,
  DndOut,
  DraftOut,
  DraftRecapOut,
  LeagueRecordsOut,
  DraftPickOut,
  HealthOut,
  AdjustmentOut,
  CantCutOut,
  LeagueDetailOut,
  LeagueOut,
  LeagueSummaryOut,
  LineupOut,
  LineupSuggestionOut,
  MatchupOut,
  WaiverOrderOut,
  MatchupPreviewOut,
  MessageBoardOut,
  MessageOut,
  PollOut,
  PollsOut,
  MockBotIn,
  MockDraftOut,
  NotImplementedOut,
  PlayerCompareOut,
  PlayerDetailOut,
  PlayerOut,
  PlayoffsOut,
  PlayoffPictureOut,
  PowerRankingsOut,
  StrengthsOut,
  RanksOut,
  ReadinessOut,
  RostersOut,
  RosterHealthOut,
  RosterMoveOut,
  ScoreboardOut,
  ScheduleMatrixOut,
  CheatSheetOut,
  KeyDatesOut,
  TeamLedgerOut,
  AvailabilityReportOut,
  ScheduleNudgesOut,
  TeamOut,
  TradeAnalysisOut,
  TradeFinderOut,
  MyLeagueTeamOut,
  TradeBlockEntryOut,
  TradeOut,
  WaiverClaimOut,
  WaiverRecommendationsOut,
  WaiverRunResultOut,
  PlayerNoteOut,
  WatchlistEntryOut,
  WeeklyRecapOut,
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

  // P5-W45: this browser's claimed teams and the leagues they live in.
  myLeagues: (teamIds: number[]) =>
    teamIds.length === 0
      ? Promise.resolve([] as MyLeagueTeamOut[])
      : req<MyLeagueTeamOut[]>(`/leagues/my-leagues?team_ids=${teamIds.join(",")}`),
  createLeague: (name: string, commissioner_name: string) =>
    req<LeagueOut>("/leagues", { method: "POST", body: JSON.stringify({ name, commissioner_name }) }),
  getLeague: (id: number | string) => req<LeagueDetailOut>(`/leagues/${id}`),
  // P5-W47: waiver-wire tiebreak order.
  waiverOrder: (leagueId: number | string) =>
    req<WaiverOrderOut>(`/leagues/${leagueId}/waivers/order`),
  // P5-W48: weekly recap.
  getRecap: (leagueId: number | string, weekNo: number | string) =>
    req<WeeklyRecapOut>(`/leagues/${leagueId}/recap/${weekNo}`),
  getActivity: (leagueId: number, limit = 50, offset = 0) =>
    req<ActivityOut>(`/leagues/${leagueId}/activity?limit=${limit}&offset=${offset}`),
  getLedger: (leagueId: number, teamId: number) =>
    req<TeamLedgerOut>(`/leagues/${leagueId}/teams/${teamId}/ledger`, {
      headers: claimHeaders(teamId),
    }),
  // P5-W43: commissioner full-league export. Fetched with the
  // commissioner's claim headers (a plain <a> link would 403) and saved
  // via blob URL so the browser downloads the JSON snapshot.
  exportLeagueJson: async (leagueId: number, commissionerTeamId: number): Promise<void> => {
    const res = await fetch(
      `${BASE}/leagues/${leagueId}/export.json?team_id=${commissionerTeamId}`,
      { headers: claimHeaders(commissionerTeamId) },
    );
    if (!res.ok) {
      throw new ApiError(res.status, "league export failed");
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `ipl-league-${leagueId}-export.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  },
  // P5-W40: ledger CSV export. Fetched with claim headers (a plain
  // <a> link would 403 for claimed teams) and saved via blob URL so
  // the browser downloads it instead of rendering it.
  exportLedgerCsv: async (leagueId: number, teamId: number): Promise<void> => {
    const res = await fetch(
      `${BASE}/leagues/${leagueId}/teams/${teamId}/ledger.csv`,
      { headers: claimHeaders(teamId) },
    );
    if (!res.ok) {
      throw new ApiError(res.status, "ledger CSV export failed");
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `ledger-team-${teamId}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  },
  getNotifications: (leagueId: number, teamId: number) =>
    req<NotificationsOut>(`/leagues/${leagueId}/notifications?team_id=${teamId}`, {
      headers: claimHeaders(teamId),
    }),
  markNotificationsRead: (leagueId: number, teamId: number) =>
    req<NotificationsOut>(`/leagues/${leagueId}/notifications/read?team_id=${teamId}`, {
      method: "POST",
      headers: claimHeaders(teamId),
    }),
  patchLeagueSettings: (
    id: number | string,
    patch: { pick_clock_secs?: number; trade_deadline_week?: number; waiver_run_weekday?: string; draft_order?: number[]; draft_scheduled_at?: string },
    teamId?: number,
  ) =>
    req<LeagueOut>(`/leagues/${id}/settings${teamId != null ? `?team_id=${teamId}` : ""}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
      ...(teamId != null ? { headers: claimHeaders(teamId) } : {}),
    commissionerTeamId: number,
    patch: { pick_clock_secs?: number; trade_deadline_week?: number; waiver_run_weekday?: string; draft_order?: number[] },
  ) =>
    // P5-W52: the settings endpoint is server-gated on the
    // commissioner's team (P4-W18 claim gate) — the acting team rides
    // in the body and its claim code rides in the headers.
    req<LeagueOut>(`/leagues/${id}/settings`, {
      method: "PATCH",
      headers: claimHeaders(commissionerTeamId),
      body: JSON.stringify({ commissioner_team_id: commissionerTeamId, ...patch }),
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
  rosterMove: (
    leagueId: number | string,
    commissionerTeamId: number,
    body: { team_id: number; player_id: number; action: "add" | "drop"; note: string },
  ) =>
    // P5-W54: roster fiat is server-gated on the commissioner's team
    // (P4-W18 claim gate) — the acting team rides in the body and its
    // claim code rides in the headers.
    req<RosterMoveOut>(`/leagues/${leagueId}/roster-moves`, {
      method: "POST",
      headers: claimHeaders(commissionerTeamId),
      body: JSON.stringify({ commissioner_team_id: commissionerTeamId, ...body }),
    }),
  listRosterMoves: (leagueId: number | string) =>
    req<RosterMoveOut[]>(`/leagues/${leagueId}/roster-moves`),
  joinLeague: (id: number | string, invite_code: string, team_name: string, owner_name: string) =>
    req<TeamOut>(`/leagues/${id}/join`, {
      method: "POST",
      body: JSON.stringify({ invite_code, team_name, owner_name }),
    }),
  listTeams: (leagueId: number | string) => req<TeamOut[]>(`/leagues/${leagueId}/teams`),
  getPowerRankings: (leagueId: number | string) =>
    req<PowerRankingsOut>(`/leagues/${leagueId}/power-rankings`),
  getStrengths: (leagueId: number | string) =>
    req<StrengthsOut>(`/leagues/${leagueId}/strengths`),
  getReadiness: (leagueId: number | string) =>
    req<ReadinessOut>(`/leagues/${leagueId}/readiness`),
  getRosters: (leagueId: number | string) =>
    req<RostersOut>(`/leagues/${leagueId}/rosters`),
  getRosterHealth: (leagueId: number, teamId: number) =>
    req<RosterHealthOut>(`/leagues/${leagueId}/roster-health?team_id=${teamId}`, {
      headers: claimHeaders(teamId),
    }),
  getPlayoffs: (leagueId: number | string) =>
    req<PlayoffsOut>(`/leagues/${leagueId}/playoffs`),
  getPlayoffPicture: (leagueId: number | string) =>
    req<PlayoffPictureOut>(`/leagues/${leagueId}/playoff-picture`),
  scheduleNudges: (leagueId: number | string, week: number) =>
    req<ScheduleNudgesOut>(`/leagues/${leagueId}/schedule-nudges?week_no=${week}`),
  // P5-W15: the full IPL-team x week game-count matrix in one read.
  scheduleMatrix: (leagueId: number | string) =>
    req<ScheduleMatrixOut>(`/leagues/${leagueId}/schedule-matrix`),
  // P5-W25: tiered draft cheat sheet + its CSV download URL.
  cheatSheet: (leagueId: number | string) =>
    req<CheatSheetOut>(`/leagues/${leagueId}/cheat-sheet`),
  cheatSheetCsvUrl: (leagueId: number | string) =>
    `${BASE}/leagues/${leagueId}/cheat-sheet.csv`,
  // P5-W27: key dates & deadlines calendar.
  keyDates: (leagueId: number | string) =>
    req<KeyDatesOut>(`/leagues/${leagueId}/key-dates`),
  // P5-W35: .ics download of the same key-dates projection.
  keyDatesIcsUrl: (leagueId: number | string) =>
    `${BASE}/leagues/${leagueId}/key-dates.ics`,
  // P5-W29: league-wide availability / injury report.
  availabilityReport: (leagueId: number | string) =>
    req<AvailabilityReportOut>(`/leagues/${leagueId}/availability-report`),

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
  // P5-W14: side-by-side compare for 2-3 players (values match the
  // detail endpoint exactly, plus games over the next 3 weeks).
  comparePlayers: (league_id: number, ids: number[]) =>
    req<PlayerCompareOut>(`/players/compare?league_id=${league_id}&ids=${ids.join(",")}`),

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

  // player notes (P5-W17): PRIVATE per-team notes. Every call carries
  // the team's claim header — the API 403s reads and writes for a
  // claimed team without its code, so notes never leak across teams.
  listPlayerNotes: (league_id: number, team_id: number) =>
    req<PlayerNoteOut[]>(`/player-notes?league_id=${league_id}&team_id=${team_id}`, {
      headers: claimHeaders(team_id),
    }),
  putPlayerNote: (body: { league_id: number; team_id: number; player_id: number; note: string }) =>
    req<PlayerNoteOut>("/player-notes", {
      method: "PUT",
      headers: claimHeaders(body.team_id),
      body: JSON.stringify(body),
    }),
  deletePlayerNote: (league_id: number, team_id: number, player_id: number) =>
    req<void>(`/player-notes?league_id=${league_id}&team_id=${team_id}&player_id=${player_id}`, {
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
  // P5-W46: league records book.
  getRecords: (leagueId: number | string) =>
    req<LeagueRecordsOut>(`/leagues/${leagueId}/records`),
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
  // P5-W31: ranks CSV export download URL + import (raw CSV text body,
  // claim header attached like other team mutations).
  ranksCsvUrl: (teamId: number | string) =>
    `${BASE}/teams/${teamId}/ranks.csv`,
  importRanksCsv: async (teamId: number, csvText: string): Promise<RanksOut> => {
    const res = await fetch(`${BASE}/teams/${teamId}/ranks/import`, {
      method: "POST",
      headers: { "Content-Type": "text/csv", ...claimHeaders(teamId) },
      body: csvText,
    });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new ApiError(
        res.status,
        (body as { detail?: string }).detail ?? `request failed (${res.status})`,
      );
    }
    return body as RanksOut;
  },

  // identity (P4-W18): claim/reset a team's claim code
  claimTeam: (teamId: number) =>
    req<ClaimOut>(`/teams/${teamId}/claim`, { method: "POST" }),
  resetClaim: (teamId: number) =>
    req<TeamOut>(`/teams/${teamId}/reset-claim`, { method: "POST" }),
  // P5-W23: rename own team — claim header attached like other
  // team mutations; the API 403s a claimed team without its code.
  renameTeam: (teamId: number, name: string) =>
    req<TeamOut>(`/teams/${teamId}`, {
      method: "PATCH",
      headers: claimHeaders(teamId),
      body: JSON.stringify({ name }),
    }),

  // lineups
  setLineup: (teamId: number | string, week_no: number, slots: Record<string, number[]>) =>
    req<LineupOut>(`/teams/${teamId}/lineup`, {
      method: "PUT",
      headers: claimHeaders(Number(teamId)),
      body: JSON.stringify({ week_no, slots }),
    }),
  getLineup: (teamId: number | string, week_no: number) =>
    req<LineupOut>(`/teams/${teamId}/lineup?week_no=${week_no}`),
  // P5-W42: commissioner lineup management — the commissioner's team sets
  // another team's lineup. The claim header goes through the commissioner's
  // team (the P4-W18 gate) and the audit note is mandatory server-side.
  commissionerSetLineup: (
    teamId: number | string,
    commissionerTeamId: number | string,
    body: { week_no: number; slots: Record<string, number[]>; note: string },
  ) =>
    req<LineupOut>(`/teams/${teamId}/lineup/commissioner`, {
      method: "PUT",
      headers: claimHeaders(Number(commissionerTeamId)),
      body: JSON.stringify({
        commissioner_team_id: Number(commissionerTeamId),
        ...body,
      }),
    }),
  // P5-W13: Suggested XI — read-only solver projection; saving still
  // goes through setLineup so lock/IL/D8 validation applies unchanged.
  getLineupSuggestion: (teamId: number | string, week_no: number) =>
    req<LineupSuggestionOut>(`/teams/${teamId}/lineup/suggestion?week_no=${week_no}`),

  // waivers
  submitClaim: (body: { league_id: number; team_id: number; add_player_id: number; drop_player_id?: number; bid: number }) =>
    req<WaiverClaimOut>("/waivers/claim", {
      method: "POST",
      headers: claimHeaders(body.team_id),
      body: JSON.stringify(body),
    }),
  // P5-W16: recommended adds for one team (D6-safe projection).
  waiverRecommendations: (league_id: number, team_id: number) =>
    req<WaiverRecommendationsOut>(`/waivers/recommendations?league_id=${league_id}&team_id=${team_id}`),
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
  // P5-W36: counter a pending incoming trade — creates a NEW trade
  // back to the original proposer via the existing propose path.
  counterTrade: (
    tradeId: number,
    body: { from_team_id: number; gives: number[]; receives: number[] },
  ) =>
    req<TradeOut>(`/trades/${tradeId}/counter`, {
      method: "POST",
      headers: claimHeaders(body.from_team_id),
      body: JSON.stringify(body),
    }),
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
  // P5-W18: read-only partner suggestions for the managing-as team.
  tradeFinder: (league_id: number, team_id: number) =>
    req<TradeFinderOut>(`/trades/finder?league_id=${league_id}&team_id=${team_id}`),

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
  // P5-W39: pinned commissioner announcements. Pin/unpin restricted
  // server-side to the commissioner's team (403 otherwise).
  pinMessage: (leagueId: number, messageId: number, team_id: number) =>
    req<MessageOut>(`/leagues/${leagueId}/messages/${messageId}/pin?team_id=${team_id}`, {
      method: "POST",
      headers: claimHeaders(team_id),
    }),
  unpinMessage: (leagueId: number, messageId: number, team_id: number) =>
    req<MessageOut>(`/leagues/${leagueId}/messages/${messageId}/unpin?team_id=${team_id}`, {
      method: "POST",
      headers: claimHeaders(team_id),
    }),

  // polls (P5-W24): advisory league votes. Reads open (team_id only
  // marks the viewer's own vote); create/vote/close carry the acting
  // team's claim header (P4-W18).
  getPolls: (leagueId: number, teamId?: number | null) =>
    req<PollsOut>(
      `/leagues/${leagueId}/polls${teamId != null ? `?team_id=${teamId}` : ""}`,
    ),
  createPoll: (leagueId: number, team_id: number, question: string, options: string[]) =>
    req<PollOut>(`/leagues/${leagueId}/polls`, {
      method: "POST",
      headers: claimHeaders(team_id),
      body: JSON.stringify({ team_id, question, options }),
    }),
  votePoll: (leagueId: number, pollId: number, team_id: number, option_id: number) =>
    req<PollOut>(`/leagues/${leagueId}/polls/${pollId}/vote`, {
      method: "POST",
      headers: claimHeaders(team_id),
      body: JSON.stringify({ team_id, option_id }),
    }),
  closePoll: (leagueId: number, pollId: number, team_id: number) =>
    req<PollOut>(`/leagues/${leagueId}/polls/${pollId}/close?team_id=${team_id}`, {
      method: "POST",
      headers: claimHeaders(team_id),
    }),

  // matchups / scoring
  listMatchups: (league_id: number, week_no: number) =>
    req<MatchupOut[]>(`/matchups?league_id=${league_id}&week_no=${week_no}`),
  // P5-W26: descriptive preview for the week's not-yet-final matchups.
  matchupPreview: (league_id: number | string, week_no: number) =>
    req<MatchupPreviewOut>(`/leagues/${league_id}/matchups/preview?week_no=${week_no}`),
  scoreboard: (matchId: number | string) => req<ScoreboardOut>(`/matchups/scoreboard/${matchId}`),
  scoreMatch: (match_id: number) =>
    req<NotImplementedOut>("/admin/score-match", { method: "POST", body: JSON.stringify({ match_id }) }),
};
