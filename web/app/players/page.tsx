"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ApiError, type PlayerOut } from "@/lib/types";
import { PageHeader, ErrorBox } from "@/components/ui";
import { cn } from "@/lib/utils";

const ROLES = ["", "WK", "BAT", "AR", "BOWL"];
const ROLE_COLOR: Record<string, string> = {
  WK: "text-yellow-300 bg-yellow-300/10",
  BAT: "text-blue-300 bg-blue-300/10",
  AR: "text-purple-300 bg-purple-300/10",
  BOWL: "text-green-300 bg-green-300/10",
};

export default function PlayersPage() {
  const [players, setPlayers] = useState<PlayerOut[]>([]);
  const [err, setErr] = useState("");
  const [q, setQ] = useState("");
  const [role, setRole] = useState("");
  const [loading, setLoading] = useState(false);

  async function load() {
    setLoading(true);
    setErr("");
    try {
      setPlayers(await api.listPlayers({ league_id: 1, role: role || undefined, q: q || undefined }));
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

  const input =
    "rounded-md border border-slate-700 bg-midnight px-3 py-2 text-sm text-white placeholder:text-slate-500 focus:border-ipl-blue-bright focus:outline-none";

  return (
    <div>
      <PageHeader title="Players" sub="Draft universe · roles, IPL teams, preseason ranks, ownership" />
      <form
        className="mb-4 flex flex-wrap gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          load();
        }}
      >
        <input className={cn(input, "w-56")} placeholder="Search name…" value={q} onChange={(e) => setQ(e.target.value)} />
        <select className={input} value={role} onChange={(e) => setRole(e.target.value)}>
          {ROLES.map((r) => (
            <option key={r} value={r}>{r || "All roles"}</option>
          ))}
        </select>
        <button className="rounded-md bg-ipl-blue px-4 py-2 text-sm font-semibold text-white hover:bg-ipl-blue-bright">
          Filter
        </button>
      </form>
      {err && <ErrorBox message={err} onRetry={load} />}
      <div className="overflow-hidden rounded-xl border border-slate-800">
        <table className="w-full text-sm">
          <thead className="bg-midnight-soft">
            <tr className="text-left text-xs uppercase text-slate-500">
              <th className="px-4 py-2">#</th>
              <th className="px-4 py-2">Player</th>
              <th className="px-4 py-2">Role</th>
              <th className="px-4 py-2">IPL</th>
              <th className="px-4 py-2">OS</th>
              <th className="px-4 py-2">Owner</th>
            </tr>
          </thead>
          <tbody>
            {players.map((p) => (
              <tr key={p.id} className="border-t border-slate-800/60 hover:bg-slate-800/30">
                <td className="px-4 py-2 text-slate-500">{p.preseason_rank ?? "–"}</td>
                <td className="px-4 py-2 font-medium text-white">{p.name}</td>
                <td className="px-4 py-2">
                  {p.role && (
                    <span className={cn("rounded px-1.5 py-0.5 text-xs font-semibold", ROLE_COLOR[p.role])}>
                      {p.role}
                    </span>
                  )}
                </td>
                <td className="px-4 py-2 text-slate-400">{p.ipl_team_code}</td>
                <td className="px-4 py-2 text-slate-400">{p.is_overseas ? "✈" : ""}</td>
                <td className="px-4 py-2 text-slate-400">
                  {p.owned_by_team_id ? `Team ${p.owned_by_team_id}` : <span className="text-pitch-green">FA</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!loading && players.length === 0 && !err && (
          <p className="p-6 text-center text-sm text-slate-500">No players match.</p>
        )}
      </div>
    </div>
  );
}
