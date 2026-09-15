/* Typed client for the FastAPI backend (blueprint §7).
   Base URL: NEXT_PUBLIC_API_URL (dev default http://127.0.0.1:8014/api).
   Engine endpoints (draft pick, waivers, trades, scoring) return 501 with a
   {detail, track} body until league-core wires them — the UI renders the
   track tag so users know which build owns it. */

import { ApiError } from "./types";
import type {
  DraftOut,
  DraftPickOut,
  HealthOut,
  LeagueDetailOut,
  LeagueOut,
  LineupOut,
  MatchupOut,
  NotImplementedOut,
  PlayerOut,
  ScoreboardOut,
  TeamOut,
  TradeOut,
  WaiverClaimOut,
} from "./types";

const BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8014/api";

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
  createLeague: (name: string, commissioner_name: string) =>
    req<LeagueOut>("/leagues", { method: "POST", body: JSON.stringify({ name, commissioner_name }) }),
  getLeague: (id: number | string) => req<LeagueDetailOut>(`/leagues/${id}`),
  joinLeague: (id: number | string, invite_code: string, team_name: string, owner_name: string) =>
    req<TeamOut>(`/leagues/${id}/join`, {
      method: "POST",
      body: JSON.stringify({ invite_code, team_name, owner_name }),
    }),
  listTeams: (leagueId: number | string) => req<TeamOut[]>(`/leagues/${leagueId}/teams`),

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

  // drafts
  getDraft: (id: number | string) => req<DraftOut>(`/drafts/${id}`),
  listPicks: (id: number | string) => req<DraftPickOut[]>(`/drafts/${id}/picks`),
  startDraft: (leagueId: number | string) =>
    req<NotImplementedOut>(`/drafts/leagues/${leagueId}/draft/start`, { method: "POST" }),
  makePick: (draftId: number | string, team_id: number, player_id: number) =>
    req<NotImplementedOut>(`/drafts/${draftId}/pick`, {
      method: "POST",
      body: JSON.stringify({ team_id, player_id }),
    }),

  // lineups
  setLineup: (teamId: number | string, week_no: number, slots: Record<string, number[]>) =>
    req<LineupOut>(`/teams/${teamId}/lineup`, {
      method: "PUT",
      body: JSON.stringify({ week_no, slots }),
    }),
  getLineup: (teamId: number | string, week_no: number) =>
    req<LineupOut>(`/teams/${teamId}/lineup?week_no=${week_no}`),

  // waivers
  submitClaim: (body: { league_id: number; team_id: number; add_player_id: number; drop_player_id?: number; bid: number }) =>
    req<NotImplementedOut>("/waivers/claim", { method: "POST", body: JSON.stringify(body) }),
  pendingClaims: (league_id: number, week_no: number) =>
    req<WaiverClaimOut[]>(`/waivers/pending?league_id=${league_id}&week_no=${week_no}`),

  // trades
  proposeTrade: (body: { league_id: number; from_team_id: number; to_team_id: number; gives: number[]; receives: number[] }) =>
    req<NotImplementedOut>("/trades", { method: "POST", body: JSON.stringify(body) }),
  listTrades: (league_id: number, status?: string) =>
    req<TradeOut[]>(`/trades?league_id=${league_id}${status ? `&status=${status}` : ""}`),
  tradeAction: (tradeId: number, action: "accept" | "reject" | "veto") =>
    req<NotImplementedOut>(`/trades/${tradeId}/${action}`, { method: "POST" }),

  // matchups / scoring
  listMatchups: (league_id: number, week_no: number) =>
    req<MatchupOut[]>(`/matchups?league_id=${league_id}&week_no=${week_no}`),
  scoreboard: (matchId: number | string) => req<ScoreboardOut>(`/matchups/scoreboard/${matchId}`),
  scoreMatch: (match_id: number) =>
    req<NotImplementedOut>("/admin/score-match", { method: "POST", body: JSON.stringify({ match_id }) }),
};
