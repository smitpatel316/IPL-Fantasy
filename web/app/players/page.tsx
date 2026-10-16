"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useLeague } from "@/lib/league-context";
import { ApiError, type PlayerOut, type TeamOut } from "@/lib/types";
import { PageHeader, ErrorBox } from "@/components/ui";
import { useWatchlist, WatchToggle } from "@/components/Watchlist";
import { AvailabilityDot, AvailabilityLegend } from "@/components/AvailabilityDot";
import { GameCountBadge, ScheduleWeekPicker, useScheduleBadges } from "@/components/ScheduleBadges";
import { cn } from "@/lib/utils";
import { Plane, Search, Star, Users } from "lucide-react";

const ROLES = ["", "WK", "BAT", "AR", "BOWL"];
const ROLE_BADGE: Record<string, string> = {
  WK: "bg-yellow-400/10 text-yellow-300",
  BAT: "bg-blue-400/10 text-blue-300",
  AR: "bg-purple-400/10 text-purple-300",
  BOWL: "bg-emerald-400/10 text-emerald-300",
};

export default function PlayersPage() {
  const { leagueId } = useLeague();
  const [players, setPlayers] = useState<PlayerOut[]>([]);
  const [teams, setTeams] = useState<TeamOut[]>([]);
  const [teamId, setTeamId] = useState<number | null>(null);
  const [err, setErr] = useState("");
  const [q, setQ] = useState("");
  const [role, setRole] = useState("");
  const [loading, setLoading] = useState(false);

  // P5-W2: the watchlist is scoped to the managing-as team (P4-W18).
  const watch = useWatchlist(leagueId, teamId);
  const sched = useScheduleBadges(leagueId, 1);

  async function load(overrides?: { role?: string; q?: string }) {
    const roleArg = overrides?.role ?? role;
    const qArg = overrides?.q ?? q;
    setLoading(true);
    setErr("");
    try {
      const [ps, ts] = await Promise.all([
        api.listPlayers({ league_id: leagueId, role: roleArg || undefined, q: qArg || undefined }),
        api.listTeams(leagueId).catch(() => [] as TeamOut[]),
      ]);
      setPlayers(ps);
      setTeams(ts);
      setTeamId((prev) => (ts.some((t) => t.id === prev) ? prev : (ts[0]?.id ?? null)));
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "load failed");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [leagueId]);

  const teamName = useMemo(() => new Map(teams.map((t) => [t.id, t.name])), [teams]);
  const freeAgents = useMemo(() => players.filter((p) => !p.owned_by_team_id).length, [players]);

  const input =
    "rounded-lg border border-slate-700 bg-midnight px-3 py-2 text-sm text-white placeholder:text-zinc-600 focus:border-trophy-gold focus:outline-none";

  return (
    <div>
      <PageHeader title="Players" sub="Draft universe · roles, IPL teams, preseason ranks, ownership" />

      <form
        className="mb-4 rounded-xl border border-slate-800 bg-midnight-soft p-4"
        onSubmit={(e) => {
          e.preventDefault();
          load();
        }}
      >
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative min-w-0 flex-1 basis-48">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-zinc-500" />
            <input
              className={cn(input, "w-full pl-8")}
              placeholder="Search name…"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
          </div>
          <div className="flex gap-1.5">
            {ROLES.map((r) => (
              <button
                key={r}
                type="button"
                onClick={() => {
                  setRole(r);
                  // Refetch immediately — the highlighted pill must never
                  // disagree with the rows on screen (P4-W11).
                  load({ role: r });
                }}
                className={cn(
                  "rounded-md px-2.5 py-2 text-xs font-semibold transition",
                  role === r ? "bg-trophy-gold text-midnight" : "bg-slate-800 text-zinc-400 hover:text-white",
                )}
              >
                {r || "All"}
              </button>
            ))}
          </div>
          <button
            type="submit"
            className="rounded-lg bg-trophy-gold px-5 py-2 text-sm font-bold text-midnight transition hover:brightness-110"
          >
            Filter
          </button>
        </div>
        <p className="mt-3 flex items-center gap-1.5 text-xs text-zinc-500">
          <Users className="h-3.5 w-3.5" />
          {loading ? "Loading…" : `${players.length} players · ${freeAgents} free agents`}
        </p>
      </form>

      {err && <div className="mb-4"><ErrorBox message={err} onRetry={load} /></div>}

      <AvailabilityLegend className="mb-4" />

      {/* P5-W2: per-team watchlist, scoped to the managing-as identity. */}
      <section className="mb-6 rounded-xl border border-slate-800 bg-midnight-soft p-4 sm:p-5">
        <div className="mb-3 flex flex-wrap items-center gap-3">
          <h2 className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-zinc-300">
            <Star className="h-4 w-4 fill-trophy-gold text-trophy-gold" /> Watched
          </h2>
          <div className="ml-auto flex flex-wrap items-center gap-3">
            <ScheduleWeekPicker weeks={sched.weeks} week={sched.week} setWeek={sched.setWeek} />
            <label className="flex items-center gap-2 text-xs font-medium text-slate-400">
              Managing as
              <select
                className={input}
                value={teamId ?? ""}
                onChange={(e) => setTeamId(Number(e.target.value))}
              >
                {teams.map((t) => (
                  <option key={t.id} value={t.id}>{t.name}</option>
                ))}
              </select>
            </label>
          </div>
        </div>
        {watch.error && <p className="mb-3 text-xs text-brick-red">{watch.error}</p>}
        {watch.entries.length === 0 ? (
          <p className="text-sm text-zinc-500">
            No players watched yet — tap the star on any player below (or on the waiver wire) and
            they&apos;ll show up here with their ownership, average points, and schedule.
          </p>
        ) : (
          <ul className="divide-y divide-slate-800/60">
            {watch.entries.map((p) => (
              <li key={p.watch_id} className="flex flex-wrap items-center gap-x-3 gap-y-1.5 py-2.5">
                <WatchToggle watched onToggle={() => watch.toggle(p.id)} playerName={p.name} />
                <AvailabilityDot availability={p.availability} />
                <Link href={`/players/${p.id}`} className="font-medium text-white hover:text-trophy-gold hover:underline">
                  {p.name}
                </Link>
                {p.role && (
                  <span className={cn("rounded px-1.5 py-0.5 text-xs font-bold", ROLE_BADGE[p.role])}>{p.role}</span>
                )}
                {p.ipl_team_code && sched.map.size > 0 && (
                  <GameCountBadge code={p.ipl_team_code} games={sched.map.get(p.ipl_team_code) ?? 0} />
                )}
                <span className="text-xs text-zinc-500">
                  {p.owned_by_team_id
                    ? (teamName.get(p.owned_by_team_id) ?? `Team ${p.owned_by_team_id}`)
                    : "Free agent"}
                </span>
                <span className="ml-auto flex items-center gap-4 text-sm tabular-nums">
                  <span className="text-zinc-300">
                    {p.avg_points != null ? `${p.avg_points.toFixed(1)} avg` : "— avg"}
                  </span>
                  <span className="text-zinc-400">
                    {p.ownership_pct != null ? `${p.ownership_pct.toFixed(0)}% owned` : "—"}
                  </span>
                </span>
              </li>
            ))}
          </ul>
        )}
        {sched.range && watch.entries.length > 0 && (
          <p className="mt-2 text-[11px] text-slate-500">
            Schedule badges: games in fantasy week {sched.week} ({sched.range}).
          </p>
        )}
      </section>

      {/* Desktop table */}
      <div className="hidden overflow-hidden rounded-xl border border-slate-800 md:block">
        <table className="w-full text-sm">
          <thead className="bg-midnight-soft">
            <tr className="text-left text-[11px] uppercase tracking-wider text-zinc-500">
              <th className="px-2 py-3 font-semibold"><span className="sr-only">Watch</span></th>
              <th className="px-4 py-3 font-semibold">#</th>
              <th className="px-4 py-3 font-semibold">Player</th>
              <th className="px-4 py-3 font-semibold">Role</th>
              <th className="px-4 py-3 font-semibold">IPL</th>
              <th className="px-4 py-3 font-semibold">OS</th>
              <th className="px-4 py-3 font-semibold">Owner</th>
              <th className="px-4 py-3 text-right font-semibold">Avg pts</th>
              <th className="px-4 py-3 text-right font-semibold">Own %</th>
            </tr>
          </thead>
          <tbody>
            {players.map((p) => (
              <tr key={p.id} className="border-t border-slate-800/60 transition hover:bg-slate-800/30">
                <td className="px-2 py-2.5">
                  <WatchToggle
                    watched={watch.watchedIds.has(p.id)}
                    onToggle={() => watch.toggle(p.id)}
                    playerName={p.name}
                  />
                </td>
                <td className="px-4 py-2.5 tabular-nums text-zinc-500">{p.preseason_rank ?? "–"}</td>
                <td className="px-4 py-2.5 font-medium text-white">
                  <span className="inline-flex items-center gap-2">
                    <AvailabilityDot availability={p.availability} />
                    <Link href={`/players/${p.id}`} className="hover:text-trophy-gold hover:underline">
                      {p.name}
                    </Link>
                  </span>
                </td>
                <td className="px-4 py-2.5">
                  {p.role ? (
                    <span className={cn("rounded px-1.5 py-0.5 text-xs font-bold", ROLE_BADGE[p.role])}>
                      {p.role}
                    </span>
                  ) : (
                    <span className="text-zinc-600">–</span>
                  )}
                </td>
                <td className="px-4 py-2.5">
                  <span className="rounded bg-slate-800 px-1.5 py-0.5 text-xs font-semibold text-zinc-300">
                    {p.ipl_team_code ?? "–"}
                  </span>
                </td>
                <td className="px-4 py-2.5 text-zinc-400">
                  {p.is_overseas ? <Plane className="h-3.5 w-3.5" aria-label="Overseas" /> : ""}
                </td>
                <td className="px-4 py-2.5">
                  {p.owned_by_team_id ? (
                    <span className="text-zinc-400">{teamName.get(p.owned_by_team_id) ?? `Team ${p.owned_by_team_id}`}</span>
                  ) : (
                    <span className="rounded bg-pitch-green/15 px-1.5 py-0.5 text-xs font-bold text-pitch-green">FA</span>
                  )}
                </td>
                <td className="px-4 py-2.5 text-right tabular-nums text-zinc-300">
                  {p.avg_points != null ? p.avg_points.toFixed(1) : "–"}
                </td>
                <td className="px-4 py-2.5 text-right tabular-nums text-zinc-400">
                  {p.ownership_pct != null ? `${p.ownership_pct.toFixed(0)}%` : "–"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!loading && players.length === 0 && !err && (
          <p className="p-8 text-center text-sm text-zinc-600">No players match.</p>
        )}
      </div>

      {/* Mobile cards */}
      <div className="space-y-2 md:hidden">
        {players.map((p) => (
          <Link
            key={p.id}
            href={`/players/${p.id}`}
            className="flex items-center gap-3 rounded-xl border border-slate-800 bg-midnight-soft px-3.5 py-3"
          >
            <span className="w-8 shrink-0 tabular-nums text-xs text-zinc-500">{p.preseason_rank ?? "–"}</span>
            <div className="min-w-0 flex-1">
              <p className="flex items-center gap-1.5 truncate text-sm font-medium text-white">
                <AvailabilityDot availability={p.availability} />
                {p.name}
                {p.is_overseas && <Plane className="ml-1.5 inline h-3 w-3 text-zinc-500" />}
              </p>
              <p className="mt-1 flex items-center gap-1.5 text-[11px] text-zinc-500">
                {p.role && (
                  <span className={cn("rounded px-1 py-px text-[10px] font-bold", ROLE_BADGE[p.role])}>{p.role}</span>
                )}
                <span className="font-semibold">{p.ipl_team_code ?? ""}</span>
                {p.avg_points != null && <span>· {p.avg_points.toFixed(1)} avg</span>}
              </p>
            </div>
            {p.owned_by_team_id ? (
              <span className="shrink-0 text-xs text-zinc-500">{teamName.get(p.owned_by_team_id) ?? `T${p.owned_by_team_id}`}</span>
            ) : (
              <span className="shrink-0 rounded bg-pitch-green/15 px-1.5 py-0.5 text-xs font-bold text-pitch-green">FA</span>
            )}
            <WatchToggle
              watched={watch.watchedIds.has(p.id)}
              onToggle={() => watch.toggle(p.id)}
              playerName={p.name}
            />
          </Link>
        ))}
        {!loading && players.length === 0 && !err && (
          <p className="rounded-xl border border-slate-800 p-8 text-center text-sm text-zinc-600">No players match.</p>
        )}
      </div>
    </div>
  );
}
