"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { clearTeamClaim, getTeamClaim, setTeamClaim } from "@/lib/identity";
import { ApiError, type LeagueDetailOut } from "@/lib/types";
import { PageHeader, ErrorBox } from "@/components/ui";
import { cn } from "@/lib/utils";
import { Trophy, Settings2, ArrowRight, Crown, KeyRound } from "lucide-react";

export default function LeaguePage({ params }: { params: Promise<{ id: string }> }) {
  const [id, setId] = useState<string | null>(null);
  const [league, setLeague] = useState<LeagueDetailOut | null>(null);
  const [err, setErr] = useState("");
  // P4-W18: team ids this browser holds claim codes for.
  const [mine, setMine] = useState<Set<number>>(new Set());
  const [claimMsg, setClaimMsg] = useState("");

  useEffect(() => {
    params.then((p) => setId(p.id));
  }, [params]);

  async function refresh(lid: string) {
    const l = await api.getLeague(lid);
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
    </div>
  );
}
