"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { ApiError, type LeagueDetailOut, type MatchupOut } from "@/lib/types";
import { PageHeader, ErrorBox } from "@/components/ui";
import { cn } from "@/lib/utils";
import { Trophy, Settings2, ArrowRight, Crown, Swords } from "lucide-react";

export default function LeaguePage({ params }: { params: Promise<{ id: string }> }) {
  const [id, setId] = useState<string | null>(null);
  const [league, setLeague] = useState<LeagueDetailOut | null>(null);
  const [err, setErr] = useState("");
  // P4-W21: "my matchup" strip state.
  const [myTeamId, setMyTeamId] = useState<number | null>(null);
  const [myMatchup, setMyMatchup] = useState<MatchupOut | null>(null);

  useEffect(() => {
    params.then((p) => setId(p.id));
  }, [params]);

  useEffect(() => {
    if (!id) return;
    api
      .getLeague(id)
      .then(setLeague)
      .catch((e) => setErr(e instanceof ApiError ? e.message : "load failed"));
  }, [id]);

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
                  <td className="px-2 py-3 font-semibold text-white">{s.team_name}</td>
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
                </div>
                <span className="shrink-0 text-sm font-bold tabular-nums text-trophy-gold">${s.faab_remaining}</span>
              </li>
            ))}
          </ul>
          <p className="border-t border-slate-800 px-5 py-3 text-[11px] text-zinc-600">
            <Crown className="mr-1 inline h-3 w-3 text-trophy-gold/70" />
            Top {playoffTeams} make the fantasy playoffs (weeks 7–8).
          </p>
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
    </div>
  );
}
