"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useLeague } from "@/lib/league-context";
import { clearTeamClaim, getTeamClaim, setTeamClaim } from "@/lib/identity";
import { ApiError, type AdjustmentOut, type DraftRecapOut, type LeagueDetailOut, type MatchupOut, type PlayerOut, type RosterMoveOut } from "@/lib/types";
import { PageHeader, ErrorBox } from "@/components/ui";
import { MessageBoard } from "@/components/MessageBoard";
import { ActivityFeed } from "@/components/ActivityFeed";
import { PowerRankings } from "@/components/PowerRankings";
import { ReadinessChecklist } from "@/components/ReadinessChecklist";
import { AllRosters } from "@/components/AllRosters";
import { cn } from "@/lib/utils";
import { Trophy, Settings2, ArrowRight, Crown, KeyRound, Swords, UserCog, Dices, GraduationCap } from "lucide-react";

export default function LeaguePage({ params }: { params: Promise<{ id: string }> }) {
  const [id, setId] = useState<string | null>(null);
  const [league, setLeague] = useState<LeagueDetailOut | null>(null);
  const [err, setErr] = useState("");
  const { setLeagueId } = useLeague();
  // P4-W18: team ids this browser holds claim codes for.
  const [mine, setMine] = useState<Set<number>>(new Set());
  const [claimMsg, setClaimMsg] = useState("");
  // P4-W21: "my matchup" strip state.
  const [myTeamId, setMyTeamId] = useState<number | null>(null);
  const [myMatchup, setMyMatchup] = useState<MatchupOut | null>(null);
  // P5-W4: draft recap + grades (null until loaded / on error).
  const [recap, setRecap] = useState<DraftRecapOut | null>(null);
  // P4-W25: commissioner roster-fiat section state.
  const [players, setPlayers] = useState<PlayerOut[]>([]);
  const [moves, setMoves] = useState<RosterMoveOut[]>([]);
  const [rmTeam, setRmTeam] = useState<number | "">("");
  const [rmPlayer, setRmPlayer] = useState<number | "">("");
  const [rmAction, setRmAction] = useState<"add" | "drop">("add");
  const [rmNote, setRmNote] = useState("");
  const [rmMsg, setRmMsg] = useState("");

  useEffect(() => {
    params.then((p) => {
      setId(p.id);
      // Viewing a league makes it the current league for every tab (P4-W7).
      const n = Number(p.id);
      if (Number.isFinite(n) && n > 0) setLeagueId(n);
    });
  }, [params, setLeagueId]);

  async function refresh(lid?: string) {
    const target = lid ?? id;
    if (!target) return;
    const l = await api.getLeague(target);
    setLeague(l);
    setMine(new Set(l.standings.filter((s) => getTeamClaim(s.team_id)).map((s) => s.team_id)));
  }

  useEffect(() => {
    if (!id) return;
    refresh(id).catch((e) => setErr(e instanceof ApiError ? e.message : "load failed"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function doClaim(teamId: number) {
    setClaimMsg("");
    try {
      const r = await api.claimTeam(teamId);
      setTeamClaim(teamId, r.claim_code);
      setClaimMsg("Team claimed — this browser can now act for it. Keep the code safe; the commissioner can reset it if lost.");
      if (id) await refresh(id);
    } catch (e) {
      setClaimMsg(e instanceof ApiError ? e.message : "claim failed");
    }
  }

  async function doRelease(teamId: number) {
    setClaimMsg("");
    try {
      await api.resetClaim(teamId);
      clearTeamClaim(teamId);
      if (id) await refresh(id);
    } catch (e) {
      setClaimMsg(e instanceof ApiError ? e.message : "release failed");
    }
  }

  function claimControl(s: { team_id: number; claimed: boolean }) {
    if (mine.has(s.team_id))
      return (
        <span className="mt-0.5 flex items-center gap-2 text-[11px]">
          <span className="font-bold text-trophy-gold">Yours</span>
          <button type="button" onClick={() => doRelease(s.team_id)} className="text-zinc-500 underline hover:text-zinc-300">
            release
          </button>
        </span>
      );
    if (s.claimed) return <span className="mt-0.5 block text-[11px] text-zinc-600">Claimed</span>;
    return (
      <button
        type="button"
        onClick={() => doClaim(s.team_id)}
        className="mt-0.5 flex items-center gap-1 text-[11px] font-semibold text-pitch-green hover:underline"
      >
        <KeyRound className="h-3 w-3" /> Claim this team
      </button>
    );
  }

  // Resolve "my team": the page picker (persisted per league), else a
  // team this browser has claimed (P4-W18 storage), else the first team.
  useEffect(() => {
    if (!league || myTeamId !== null) return;
    let pick: number | null = null;
    try {
      const stored = window.localStorage.getItem(`ipl-my-team-${league.id}`);
      if (stored && league.standings.some((s) => s.team_id === Number(stored))) pick = Number(stored);
      if (pick === null) {
        const claimed = league.standings.find((s) => window.localStorage.getItem(`ipl-claim-${s.team_id}`));
        pick = claimed?.team_id ?? league.standings[0]?.team_id ?? null;
      }
    } catch {
      pick = league.standings[0]?.team_id ?? null;
    }
    setMyTeamId(pick);
  }, [league, myTeamId]);

  useEffect(() => {
    if (!league) return;
    api.getDraftRecap(league.id).then(setRecap).catch(() => setRecap(null));
  }, [league]);

  useEffect(() => {
    if (!league || myTeamId === null) return;
    api
      .listMatchups(league.id, league.current_week)
      .then((ms) => setMyMatchup(ms.find((m) => m.team_a_id === myTeamId || m.team_b_id === myTeamId) ?? null))
      .catch(() => setMyMatchup(null));
  }, [league, myTeamId]);

  function chooseTeam(teamId: number) {
    setMyTeamId(teamId);
    try {
      window.localStorage.setItem(`ipl-my-team-${league?.id}`, String(teamId));
    } catch {
      /* ignore */
    }
  }

  async function loadMoves(lid: string) {
    const [ps, ms] = await Promise.all([
      api.listPlayers({ league_id: Number(lid) }).catch(() => [] as PlayerOut[]),
      api.listRosterMoves(lid).catch(() => [] as RosterMoveOut[]),
    ]);
    setPlayers(ps);
    setMoves(ms);
  }

  useEffect(() => {
    if (!id) return;
    loadMoves(id);
  }, [id]);

  async function submitMove(e: React.FormEvent) {
    e.preventDefault();
    if (!id || rmTeam === "" || rmPlayer === "" || !rmNote.trim()) return;
    setRmMsg("");
    try {
      await api.rosterMove(id, {
        team_id: rmTeam, player_id: rmPlayer, action: rmAction, note: rmNote.trim(),
      });
      setRmMsg("Move recorded in the audit log.");
      setRmNote("");
      await loadMoves(id);
    } catch (e) {
      setRmMsg(e instanceof ApiError ? e.message : "move failed");
    }
  }

  const rmPlayerOptions =
    rmAction === "add"
      ? players.filter((p) => p.owned_by_team_id == null)
      : players.filter((p) => p.owned_by_team_id === rmTeam);

  if (err) return <div className="pt-8"><ErrorBox message={err} /></div>;
  if (!league)
    return (
      <div className="space-y-3 pt-8" aria-label="Loading">
        {[0, 1, 2].map((i) => (
          <div key={i} className="h-14 animate-pulse rounded-xl bg-midnight-soft" />
        ))}
      </div>
    );

  const playoffTeams = league.settings.playoff_teams || 4;

  return (
    <div>
      <PageHeader
        title={league.name}
        sub={`Season ${league.season} · invite code ${league.invite_code} · ${league.status}`}
      />

      {/* P5-W11: onboarding nudge — only when the visitor's selected
          team is still unclaimed. */}
      {myTeamId != null &&
        league.standings.find((s) => s.team_id === myTeamId)?.claimed === false && (
          <section
            aria-label="Get started"
            className="mb-5 flex flex-wrap items-center gap-3 rounded-xl border border-trophy-gold/30 bg-trophy-gold/5 px-5 py-4"
          >
            <p className="text-sm text-zinc-300">
              <strong className="text-white">New here?</strong> Your team is still
              unclaimed — claim it below so only you can manage it, then read the
              how-to-play guide for the draft, FAAB, and playoff rules.
            </p>
            <Link
              href="/help"
              className="ml-auto flex items-center gap-1.5 rounded-md bg-trophy-gold px-3 py-1.5 text-sm font-bold text-midnight transition hover:bg-trophy-gold/90"
            >
              How to play <ArrowRight className="h-4 w-4" />
            </Link>
          </section>
        )}

      {/* P5-W3: practice-draft entry — ephemeral mock drafts vs bots. */}
      <section
        aria-label="Practice draft"
        className="mb-5 flex flex-wrap items-center gap-3 rounded-xl border border-slate-800 bg-midnight-soft px-5 py-4"
      >
        <h2 className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-zinc-300">
          <Dices className="h-4 w-4 text-trophy-gold" /> Practice draft
        </h2>
        <p className="text-sm text-zinc-400">
          Run a mock draft against sharp and casual bots — your live league is never touched.
        </p>
        <Link
          href="/mock-draft"
          className="ml-auto flex items-center gap-1.5 rounded-md bg-trophy-gold px-3 py-1.5 text-sm font-bold text-midnight transition hover:bg-trophy-gold/90"
        >
          Start a mock <ArrowRight className="h-4 w-4" />
        </Link>
      </section>

      {/* P4-W21: my-matchup strip for the current week */}
      {myMatchup && (
        <section
          aria-label="My matchup"
          className="mb-5 rounded-xl border border-trophy-gold/30 bg-midnight-soft px-5 py-4"
        >
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <h2 className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-zinc-300">
              <Swords className="h-4 w-4 text-trophy-gold" /> Week {league.current_week} · Your matchup
            </h2>
            <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[11px] font-bold uppercase text-zinc-300">
              {myMatchup.status}
            </span>
            <span className="ml-auto flex items-center gap-2">
              <label htmlFor="my-team-picker" className="text-[11px] uppercase tracking-wider text-zinc-500">
                My team
              </label>
              <select
                id="my-team-picker"
                value={myTeamId ?? ""}
                onChange={(e) => chooseTeam(Number(e.target.value))}
                className="rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-zinc-200 focus:border-trophy-gold focus:outline-none"
              >
                {league.standings.map((s) => (
                  <option key={s.team_id} value={s.team_id}>
                    {s.team_name}
                  </option>
                ))}
              </select>
            </span>
          </div>
          <div className="flex items-center gap-3 text-base sm:text-lg">
            <span
              className={cn(
                "min-w-0 flex-1 truncate text-right font-semibold",
                myMatchup.status === "final" && myMatchup.score_a > myMatchup.score_b ? "text-white" : "text-zinc-300",
                myMatchup.team_a_id === myTeamId && "text-trophy-gold",
              )}
            >
              {myMatchup.team_a_name}
            </span>
            <span className="shrink-0 font-mono font-bold tabular-nums text-white">
              {myMatchup.score_a.toFixed(1)} – {myMatchup.score_b.toFixed(1)}
            </span>
            <span
              className={cn(
                "min-w-0 flex-1 truncate font-semibold",
                myMatchup.status === "final" && myMatchup.score_b > myMatchup.score_a ? "text-white" : "text-zinc-300",
                myMatchup.team_b_id === myTeamId && "text-trophy-gold",
              )}
            >
              {myMatchup.team_b_name}
            </span>
          </div>
          <p className="mt-2 text-right">
            <Link href="/matchup" className="text-xs font-semibold text-pitch-green hover:underline">
              View all matchups →
            </Link>
          </p>
        </section>
      )}

      {/* P5-W4: draft recap + grades */}
      {recap && <DraftRecapSection recap={recap} />}

      {/* P5-W8: league activity feed */}
      {league && <ActivityFeed leagueId={league.id} />}
      {/* P5-W9: power rankings */}
      {league && <PowerRankings leagueId={league.id} />}
      {/* P5-W10: season-start checklist */}
      {league && <ReadinessChecklist leagueId={league.id} />}
      {/* P5-W12: all-teams roster view */}
      {league && <AllRosters leagueId={league.id} />}

      {/* P5-W5: persistent league message board */}
      {league && (
        <MessageBoard
          leagueId={league.id}
          myTeamId={myTeamId}
          myTeamName={
            league.standings.find((s) => s.team_id === myTeamId)?.team_name ?? null
          }
        />
      )}

      <div className="grid gap-5 lg:grid-cols-3">
        {/* Standings */}
        <section className="overflow-hidden rounded-xl border border-slate-800 bg-midnight-soft lg:col-span-2">
          <h2 className="flex items-center gap-2 border-b border-slate-800 px-5 py-4 text-sm font-bold uppercase tracking-wider text-zinc-300">
            <Trophy className="h-4 w-4 text-trophy-gold" /> Standings
          </h2>
          {/* Desktop */}
          <table className="hidden w-full text-sm sm:table">
            <thead>
              <tr className="text-left text-[11px] uppercase tracking-wider text-zinc-500">
                <th className="px-5 py-2.5 font-semibold">#</th>
                <th className="px-2 py-2.5 font-semibold">Team</th>
                <th className="hidden px-2 py-2.5 font-semibold md:table-cell">Manager</th>
                <th className="px-2 py-2.5 text-center font-semibold">W–L</th>
                <th className="px-2 py-2.5 text-right font-semibold">PF</th>
                <th className="px-5 py-2.5 text-right font-semibold">FAAB</th>
              </tr>
            </thead>
            <tbody>
              {league.standings.map((s, i) => (
                <tr
                  key={s.team_id}
                  className={cn(
                    "border-t border-slate-800/60 transition hover:bg-slate-800/30",
                    i === playoffTeams && "border-t-2 border-t-trophy-gold/40",
                  )}
                >
                  <td className="px-5 py-3">
                    <span className={cn(
                      "flex h-6 w-6 items-center justify-center rounded-md text-[11px] font-extrabold",
                      i < playoffTeams ? "bg-trophy-gold/15 text-trophy-gold" : "bg-slate-800 text-zinc-500",
                    )}>
                      {i + 1}
                    </span>
                  </td>
                  <td className="px-2 py-3 font-semibold text-white">
                    {s.team_name}
                    {claimControl(s)}
                  </td>
                  <td className="hidden px-2 py-3 text-zinc-400 md:table-cell">{s.owner_name ?? "—"}</td>
                  <td className="px-2 py-3 text-center tabular-nums">
                    <span className="font-semibold text-pitch-green">{s.wins}</span>
                    <span className="text-zinc-600">–</span>
                    <span className="font-semibold text-brick-red">{s.losses}</span>
                    {s.ties > 0 && <span className="text-zinc-500">–{s.ties}</span>}
                  </td>
                  <td className="px-2 py-3 text-right tabular-nums text-zinc-300">{s.points_for.toFixed(1)}</td>
                  <td className="px-5 py-3 text-right tabular-nums font-semibold text-trophy-gold">${s.faab_remaining}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {/* Mobile cards */}
          <ul className="divide-y divide-slate-800/60 sm:hidden">
            {league.standings.map((s, i) => (
              <li key={s.team_id} className="flex items-center gap-3 px-4 py-3">
                <span className={cn(
                  "flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-xs font-extrabold",
                  i < playoffTeams ? "bg-trophy-gold/15 text-trophy-gold" : "bg-slate-800 text-zinc-500",
                )}>
                  {i + 1}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-semibold text-white">{s.team_name}</p>
                  <p className="text-[11px] tabular-nums text-zinc-500">
                    <span className="text-pitch-green">{s.wins}W</span>–<span className="text-brick-red">{s.losses}L</span>
                    {" · "}{s.points_for.toFixed(0)} PF
                  </p>
                  {claimControl(s)}
                </div>
                <span className="shrink-0 text-sm font-bold tabular-nums text-trophy-gold">${s.faab_remaining}</span>
              </li>
            ))}
          </ul>
          <p className="border-t border-slate-800 px-5 py-3 text-[11px] text-zinc-600">
            <Crown className="mr-1 inline h-3 w-3 text-trophy-gold/70" />
            Top {playoffTeams} make the fantasy playoffs (weeks 7–8).
            {" "}Claim your team to lock its lineups, bids and trades to this browser.
          </p>
          {claimMsg && <p className="border-t border-slate-800 px-5 py-2 text-[11px] text-pitch-green">{claimMsg}</p>}
        </section>

        {/* Side column */}
        <div className="space-y-4">
          <section className="rounded-xl border border-slate-800 bg-midnight-soft p-5">
            <h2 className="mb-3 flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-zinc-300">
              <Settings2 className="h-4 w-4 text-zinc-500" /> League settings
            </h2>
            <dl className="space-y-2 text-sm">
              {[
                ["Draft", `${league.settings.draft_type} · ${league.settings.rounds} rounds`],
                ["Scoring", league.settings.scoring_table_version],
                ["Overseas cap", `${league.settings.overseas_cap} starters`],
                ["FAAB budget", `$${league.settings.faab_budget}`],
                ["Playoffs", `Top ${league.settings.playoff_teams} · weeks 7–8`],
                ["Trade deadline", `End of week ${league.settings.trade_deadline_week}`],
              ].map(([k, v]) => (
                <div key={k} className="flex items-baseline justify-between gap-4">
                  <dt className="shrink-0 text-zinc-500">{k}</dt>
                  <dd className="text-right font-medium text-zinc-200">{v}</dd>
                </div>
              ))}
            </dl>
          </section>
          <Link
            href={`/draft-room/${league.id}`}
            className="group flex items-center justify-center gap-2 rounded-xl bg-trophy-gold p-5 text-center text-sm font-bold text-midnight transition hover:brightness-110"
          >
            Enter draft room
            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
          </Link>
        </div>
      </div>

      <CommissionerTools league={league} onChanged={refresh} />
      {/* P4-W25: commissioner roster fiat (audited) */}
      <section className="mt-5 rounded-xl border border-slate-800 bg-midnight-soft p-5">
        <h2 className="mb-1 flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-zinc-300">
          <UserCog className="h-4 w-4 text-zinc-500" /> Commissioner — roster moves
        </h2>
        <p className="mb-4 text-xs text-zinc-500">
          Add or drop a player by fiat. Adds respect league-wide ownership and the 15-man cap;
          drops also clear the player from saved lineups. Every move needs an audit note.
        </p>
        <form onSubmit={submitMove} className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <select
            aria-label="Team"
            value={rmTeam}
            onChange={(e) => setRmTeam(Number(e.target.value))}
            className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white focus:border-trophy-gold focus:outline-none"
          >
            <option value="">Team…</option>
            {league.standings.map((s) => (
              <option key={s.team_id} value={s.team_id}>
                {s.team_name}
              </option>
            ))}
          </select>
          <select
            aria-label="Action"
            value={rmAction}
            onChange={(e) => setRmAction(e.target.value as "add" | "drop")}
            className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white focus:border-trophy-gold focus:outline-none"
          >
            <option value="add">Add player</option>
            <option value="drop">Drop player</option>
          </select>
          <select
            aria-label="Player"
            value={rmPlayer}
            onChange={(e) => setRmPlayer(Number(e.target.value))}
            className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white focus:border-trophy-gold focus:outline-none"
          >
            <option value="">Player…</option>
            {rmPlayerOptions.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} ({p.role ?? "—"}, {p.ipl_team_code ?? "—"})
              </option>
            ))}
          </select>
          <input
            aria-label="Audit note"
            value={rmNote}
            onChange={(e) => setRmNote(e.target.value)}
            maxLength={200}
            placeholder="Audit note (required)"
            className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white placeholder:text-zinc-600 focus:border-trophy-gold focus:outline-none"
          />
          <button
            type="submit"
            disabled={rmTeam === "" || rmPlayer === "" || !rmNote.trim()}
            className="rounded-lg bg-trophy-gold px-3 py-2 text-sm font-bold text-midnight transition hover:brightness-110 disabled:opacity-50"
          >
            Record move
          </button>
        </form>
        {rmMsg && <p className="mt-2 text-xs text-pitch-green">{rmMsg}</p>}
        {moves.length > 0 && (
          <ul className="mt-4 space-y-1.5 border-t border-slate-800 pt-3 text-sm">
            {moves.map((m) => (
              <li key={m.id} className="flex flex-wrap items-baseline gap-x-2 text-zinc-400">
                <span className={m.kind === "roster_add" ? "font-bold text-pitch-green" : "font-bold text-brick-red"}>
                  {m.kind === "roster_add" ? "ADD" : "DROP"}
                </span>
                <span className="text-zinc-200">{m.player_name}</span>
                <span>→ {m.team_name}</span>
                <span className="text-xs text-zinc-600">
                  {m.created_at} · “{m.note}”
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

const WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"];

/** Commissioner tools (P4-W15): settings edit + audited FAAB adjustments.
 *  Ungated until team identity lands (P4-W18) — every change is written
 *  to the league's audit log below. */
function CommissionerTools({
  league,
  onChanged,
}: {
  league: LeagueDetailOut;
  onChanged: () => void;
}) {
  const [clock, setClock] = useState(String(league.settings.pick_clock_secs ?? 90));
  const [deadline, setDeadline] = useState(String(league.settings.trade_deadline_week ?? 6));
  const [weekday, setWeekday] = useState(String(league.settings.waiver_run_weekday ?? "wednesday"));
  const [adjTeam, setAdjTeam] = useState("");
  const [adjDelta, setAdjDelta] = useState("");
  const [adjNote, setAdjNote] = useState("");
  const [adjustments, setAdjustments] = useState<AdjustmentOut[]>([]);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.listAdjustments(league.id).then(setAdjustments).catch(() => {});
  }, [league.id]);

  const input =
    "rounded-lg border border-slate-700 bg-midnight px-3 py-2 text-sm text-white placeholder:text-zinc-600 focus:border-trophy-gold focus:outline-none";

  async function saveSettings(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    setMsg("");
    setBusy(true);
    try {
      await api.patchLeagueSettings(league.id, {
        pick_clock_secs: Number(clock),
        trade_deadline_week: Number(deadline),
        waiver_run_weekday: weekday,
      });
      setMsg("Settings saved.");
      onChanged();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "settings save failed");
    } finally {
      setBusy(false);
    }
  }

  async function submitAdjustment(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    setMsg("");
    const teamId = Number(adjTeam || league.standings[0]?.team_id);
    const delta = Number(adjDelta);
    if (!teamId || !Number.isFinite(delta) || adjNote.trim() === "") {
      setErr("Pick a team, a FAAB delta, and an audit note.");
      return;
    }
    setBusy(true);
    try {
      const adj = await api.createAdjustment(league.id, {
        team_id: teamId,
        faab_delta: delta,
        note: adjNote.trim(),
      });
      setAdjustments((prev) => [adj, ...prev]);
      setAdjDelta("");
      setAdjNote("");
      setMsg(`FAAB adjusted — ${adj.team_name} now has $${adj.faab_after}.`);
      onChanged();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "adjustment failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="mt-6 rounded-xl border border-slate-800 bg-midnight-soft p-5">
      <h2 className="mb-1 flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-zinc-300">
        <Settings2 className="h-4 w-4 text-zinc-500" /> Commissioner tools
      </h2>
      <p className="mb-4 text-xs text-zinc-500">
        Settings edits and manual FAAB adjustments. Every adjustment is written to the audit
        log with its note.
      </p>
      {err && (
        <div className="mb-3">
          <ErrorBox message={err} />
        </div>
      )}
      {msg && <p className="mb-3 text-sm text-pitch-green">{msg}</p>}

      <div className="grid gap-6 lg:grid-cols-2">
        <form onSubmit={saveSettings} className="space-y-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-400">League settings</h3>
          <label className="block text-xs text-zinc-500">
            Pick clock (seconds, applies to future drafts)
            <input type="number" min={0} max={600} className={cn(input, "mt-1 w-full")} value={clock} onChange={(e) => setClock(e.target.value)} />
          </label>
          <label className="block text-xs text-zinc-500">
            Trade deadline (end of week)
            <input type="number" min={1} max={8} className={cn(input, "mt-1 w-full")} value={deadline} onChange={(e) => setDeadline(e.target.value)} />
          </label>
          <label className="block text-xs text-zinc-500">
            Waiver run day
            <select className={cn(input, "mt-1 w-full")} value={weekday} onChange={(e) => setWeekday(e.target.value)}>
              {WEEKDAYS.map((d) => (
                <option key={d} value={d}>
                  {d[0].toUpperCase() + d.slice(1)}
                </option>
              ))}
            </select>
          </label>
          <button type="submit" disabled={busy} className="rounded-lg bg-trophy-gold px-4 py-2 text-sm font-bold text-midnight transition hover:brightness-110 disabled:opacity-50">
            Save settings
          </button>
        </form>

        <form onSubmit={submitAdjustment} className="space-y-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-400">FAAB adjustment</h3>
          <label className="block text-xs text-zinc-500">
            Team
            <select className={cn(input, "mt-1 w-full")} value={adjTeam} onChange={(e) => setAdjTeam(e.target.value)}>
              {league.standings.map((s) => (
                <option key={s.team_id} value={s.team_id}>
                  {s.team_name} (${s.faab_remaining})
                </option>
              ))}
            </select>
          </label>
          <label className="block text-xs text-zinc-500">
            Delta (e.g. 10 to grant, -5 to dock)
            <input type="number" className={cn(input, "mt-1 w-full")} value={adjDelta} onChange={(e) => setAdjDelta(e.target.value)} placeholder="0" />
          </label>
          <label className="block text-xs text-zinc-500">
            Audit note (required)
            <input className={cn(input, "mt-1 w-full")} value={adjNote} onChange={(e) => setAdjNote(e.target.value)} placeholder="Why is this being adjusted?" maxLength={200} />
          </label>
          <button type="submit" disabled={busy} className="rounded-lg bg-slate-800 px-4 py-2 text-sm font-bold text-white transition hover:bg-slate-700 disabled:opacity-50">
            Apply adjustment
          </button>
        </form>
      </div>

      {adjustments.length > 0 && (
        <div className="mt-6">
          <h3 className="mb-2 text-xs font-bold uppercase tracking-wider text-zinc-400">Audit log</h3>
          <ul className="space-y-1.5 text-sm">
            {adjustments.map((a) => (
              <li key={a.id} className="flex flex-wrap items-baseline gap-x-3 rounded-lg bg-slate-800/50 px-3 py-2">
                <span className="font-semibold text-white">{a.team_name}</span>
                <span className={a.faab_delta >= 0 ? "text-pitch-green" : "text-brick-red"}>
                  {a.faab_delta >= 0 ? "+" : ""}${a.faab_delta} → ${a.faab_after}
                </span>
                <span className="text-zinc-400">{a.note}</span>
                <span className="ml-auto text-xs text-zinc-600">{a.created_at}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

/** P5-W4: draft recap + grades — deterministic grades from the
 * completed draft vs consensus pre-draft ranks (server-computed at
 * GET /leagues/{id}/draft-recap). Pre-draft this is the honest empty
 * state; grades land when the draft completes. */
const GRADE_STYLE: Record<string, string> = {
  A: "bg-pitch-green/15 text-pitch-green",
  B: "bg-emerald-900/40 text-emerald-300",
  C: "bg-slate-800 text-zinc-300",
  D: "bg-amber-950/50 text-amber-300",
  F: "bg-red-950/50 text-red-300",
};

function DraftRecapSection({ recap }: { recap: DraftRecapOut }) {
  if (recap.status !== "complete") {
    return (
      <section
        aria-label="Draft recap"
        className="mb-5 rounded-xl border border-dashed border-slate-800 px-5 py-4"
      >
        <h2 className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-zinc-300">
          <GraduationCap className="h-4 w-4 text-trophy-gold" /> Draft recap
        </h2>
        <p className="mt-1 text-sm text-zinc-500">
          Grades land when the draft completes — every team gets a grade, its biggest
          steal, and its biggest reach, all from consensus pre-draft ranks.
        </p>
      </section>
    );
  }
  const steal = recap.headline_biggest_steal;
  const best = recap.headline_best_pick;
  return (
    <section
      aria-label="Draft recap"
      className="mb-5 rounded-xl border border-slate-800 bg-midnight-soft p-5"
    >
      <h2 className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-zinc-300">
        <GraduationCap className="h-4 w-4 text-trophy-gold" /> Draft recap &amp; grades
      </h2>
      {(steal || best) && (
        <p className="mt-2 text-sm text-zinc-400">
          {best && (
            <>
              Best pick: <span className="font-semibold text-white">{best.player_name}</span>{" "}
              (consensus #{best.consensus_rank}) to {best.team_name} at pick #{best.pick_no}.{" "}
            </>
          )}
          {steal && (
            <>
              Biggest steal: <span className="font-semibold text-white">{steal.player_name}</span>{" "}
              (ranked #{steal.consensus_rank}, taken #{steal.pick_no}) by {steal.team_name}.
            </>
          )}
        </p>
      )}
      <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {recap.teams.map((t) => (
          <div key={t.team_id} className="rounded-lg border border-slate-800 bg-slate-900/40 p-3.5">
            <div className="flex items-center justify-between gap-2">
              <h3 className="truncate font-semibold text-white">{t.team_name}</h3>
              <span
                className={cn(
                  "rounded-md px-2 py-0.5 text-lg font-black leading-none",
                  GRADE_STYLE[t.grade] ?? GRADE_STYLE.C,
                )}
              >
                {t.grade}
              </span>
            </div>
            <p className="mt-1.5 text-xs text-zinc-500">
              Drafted value {t.projected_value} vs {t.expected_value} expected (
              {t.value_ratio.toFixed(2)}×) · {t.picks_made} picks
              {t.unranked_picks > 0 && <> · {t.unranked_picks} unranked</>}
            </p>
            {t.biggest_steal && (
              <p className="mt-2 text-xs text-zinc-400">
                Steal: <span className="text-zinc-200">{t.biggest_steal.player_name}</span>{" "}
                (#{t.biggest_steal.consensus_rank} at pick {t.biggest_steal.pick_no})
              </p>
            )}
            {t.biggest_reach && (
              <p className="mt-1 text-xs text-zinc-400">
                Reach: <span className="text-zinc-200">{t.biggest_reach.player_name}</span>{" "}
                (#{t.biggest_reach.consensus_rank} at pick {t.biggest_reach.pick_no})
              </p>
            )}
          </div>
        ))}
      </div>
      <p className="mt-3 text-[11px] text-slate-500">{recap.basis}</p>
    </section>
  );
}
