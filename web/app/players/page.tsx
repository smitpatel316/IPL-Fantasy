"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { ApiError, type PlayerOut, type TeamOut } from "@/lib/types";
import { PageHeader, ErrorBox } from "@/components/ui";
import { cn } from "@/lib/utils";
import { Plane, Search, Users } from "lucide-react";

const ROLES = ["", "WK", "BAT", "AR", "BOWL"];
const ROLE_BADGE: Record<string, string> = {
  WK: "bg-yellow-400/10 text-yellow-300",
  BAT: "bg-blue-400/10 text-blue-300",
  AR: "bg-purple-400/10 text-purple-300",
  BOWL: "bg-emerald-400/10 text-emerald-300",
};

export default function PlayersPage() {
  const [players, setPlayers] = useState<PlayerOut[]>([]);
  const [teams, setTeams] = useState<TeamOut[]>([]);
  const [err, setErr] = useState("");
  const [q, setQ] = useState("");
  const [role, setRole] = useState("");
  const [loading, setLoading] = useState(false);

  async function load() {
    setLoading(true);
    setErr("");
    try {
      const [ps, ts] = await Promise.all([
        api.listPlayers({ league_id: 1, role: role || undefined, q: q || undefined }),
        api.listTeams(1).catch(() => [] as TeamOut[]),
      ]);
      setPlayers(ps);
      setTeams(ts);
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "load failed");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
                onClick={() => setRole(r)}
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

      {/* Desktop table */}
      <div className="hidden overflow-hidden rounded-xl border border-slate-800 md:block">
        <table className="w-full text-sm">
          <thead className="bg-midnight-soft">
            <tr className="text-left text-[11px] uppercase tracking-wider text-zinc-500">
              <th className="px-4 py-3 font-semibold">#</th>
              <th className="px-4 py-3 font-semibold">Player</th>
              <th className="px-4 py-3 font-semibold">Role</th>
              <th className="px-4 py-3 font-semibold">IPL</th>
              <th className="px-4 py-3 font-semibold">OS</th>
              <th className="px-4 py-3 font-semibold">Owner</th>
            </tr>
          </thead>
          <tbody>
            {players.map((p) => (
              <tr key={p.id} className="border-t border-slate-800/60 transition hover:bg-slate-800/30">
                <td className="px-4 py-2.5 tabular-nums text-zinc-500">{p.preseason_rank ?? "–"}</td>
                <td className="px-4 py-2.5 font-medium text-white">{p.name}</td>
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
          <div key={p.id} className="flex items-center gap-3 rounded-xl border border-slate-800 bg-midnight-soft px-3.5 py-3">
            <span className="w-8 shrink-0 tabular-nums text-xs text-zinc-500">{p.preseason_rank ?? "–"}</span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-white">
                {p.name}
                {p.is_overseas && <Plane className="ml-1.5 inline h-3 w-3 text-zinc-500" />}
              </p>
              <p className="mt-1 flex items-center gap-1.5 text-[11px] text-zinc-500">
                {p.role && (
                  <span className={cn("rounded px-1 py-px text-[10px] font-bold", ROLE_BADGE[p.role])}>{p.role}</span>
                )}
                <span className="font-semibold">{p.ipl_team_code ?? ""}</span>
              </p>
            </div>
            {p.owned_by_team_id ? (
              <span className="shrink-0 text-xs text-zinc-500">{teamName.get(p.owned_by_team_id) ?? `T${p.owned_by_team_id}`}</span>
            ) : (
              <span className="shrink-0 rounded bg-pitch-green/15 px-1.5 py-0.5 text-xs font-bold text-pitch-green">FA</span>
            )}
          </div>
        ))}
        {!loading && players.length === 0 && !err && (
          <p className="rounded-xl border border-slate-800 p-8 text-center text-sm text-zinc-600">No players match.</p>
        )}
      </div>
    </div>
  );
}
