"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ApiError, type MatchupOut } from "@/lib/types";
import { PageHeader, ErrorBox } from "@/components/ui";
import { cn } from "@/lib/utils";

export default function MatchupPage() {
  const [matchups, setMatchups] = useState<MatchupOut[]>([]);
  const [week, setWeek] = useState(1);
  const [err, setErr] = useState("");

  useEffect(() => {
    api
      .listMatchups(1, week)
      .then(setMatchups)
      .catch((e) => setErr(e instanceof ApiError ? e.message : "load failed"));
  }, [week]);

  return (
    <div>
      <PageHeader title="Matchups" sub="Weekly head-to-head · Mon–Sun periods (D4)" />
      <div className="mb-4">
        <select
          className="rounded-md border border-slate-700 bg-midnight px-3 py-2 text-sm"
          value={week}
          onChange={(e) => setWeek(Number(e.target.value))}
        >
          {[1, 2, 3, 4, 5, 6, 7, 8].map((w) => (
            <option key={w} value={w}>Week {w}{w >= 7 ? " (playoff)" : ""}</option>
          ))}
        </select>
      </div>
      {err && <div className="mb-4"><ErrorBox message={err} /></div>}
      <div className="grid gap-4 md:grid-cols-2">
        {matchups.map((m) => {
          const aWin = m.score_a > m.score_b;
          return (
            <div key={m.id} className="rounded-xl border border-slate-800 bg-midnight-soft p-5">
              <div className="flex items-center justify-between">
                <span className={cn("font-semibold", aWin ? "text-pitch-green" : "text-white")}>{m.team_a_name}</span>
                <span className="text-2xl font-bold text-white">{m.score_a.toFixed(1)}</span>
              </div>
              <div className="my-2 border-t border-slate-800" />
              <div className="flex items-center justify-between">
                <span className={cn("font-semibold", !aWin && m.score_b > 0 ? "text-pitch-green" : "text-white")}>{m.team_b_name}</span>
                <span className="text-2xl font-bold text-white">{m.score_b.toFixed(1)}</span>
              </div>
              <p className="mt-3 text-xs uppercase tracking-wide text-slate-500">{m.status}</p>
            </div>
          );
        })}
      </div>
      {matchups.length === 0 && !err && (
        <p className="text-sm text-slate-500">No matchups scheduled for week {week} yet.</p>
      )}
    </div>
  );
}
