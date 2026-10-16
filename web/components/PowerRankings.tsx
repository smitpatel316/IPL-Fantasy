"use client";

/* P5-W9: power rankings — deterministic list computed server-side.
   Pre-season it is honestly a roster-value ranking (from preseason
   ranks); once weeks finalize it blends record with points-for.
   The basis copy always says which one is on screen. */

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ApiError, type PowerRankingsOut } from "@/lib/types";
import { cn } from "@/lib/utils";
import { ArrowDown, ArrowUp, Minus, Zap } from "lucide-react";

export function PowerRankings({ leagueId }: { leagueId: number }) {
  const [data, setData] = useState<PowerRankingsOut | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    let cancelled = false;
    api
      .getPowerRankings(leagueId)
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch((e) => {
        if (!cancelled)
          setErr(e instanceof ApiError ? e.message : "power rankings load failed");
      });
    return () => {
      cancelled = true;
    };
  }, [leagueId]);

  if (err) return null; // a quiet extra — never break the league page
  if (!data || data.entries.length === 0) return null;

  const preseason = data.basis === "roster_value";

  return (
    <section
      aria-label="Power rankings"
      className="mb-5 rounded-xl border border-slate-800 bg-midnight-soft p-5"
    >
      <h2 className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-zinc-300">
        <Zap className="h-4 w-4 text-trophy-gold" /> Power rankings
        <span className="text-[11px] font-medium normal-case tracking-normal text-zinc-500">
          {preseason
            ? "pre-season — ranked by starter roster value from preseason ranks (no games yet, no invented points)"
            : `through week ${data.through_week} — record blended with points-for`}
        </span>
      </h2>
      <ul className="mt-4 divide-y divide-slate-800/60">
        {data.entries.map((e) => (
          <li key={e.team_id} className="flex items-center gap-3 py-2.5">
            <span className="w-6 shrink-0 text-sm font-bold text-zinc-400">{e.rank}</span>
            <span className="min-w-0 flex-1 truncate text-sm font-semibold text-zinc-100">
              {e.team_name}
            </span>
            {e.movement != null &&
              (e.movement > 0 ? (
                <span className="flex items-center gap-0.5 text-xs font-semibold text-pitch-green">
                  <ArrowUp className="h-3.5 w-3.5" /> {e.movement}
                </span>
              ) : e.movement < 0 ? (
                <span className="flex items-center gap-0.5 text-xs font-semibold text-brick-red">
                  <ArrowDown className="h-3.5 w-3.5" /> {Math.abs(e.movement)}
                </span>
              ) : (
                <span className="flex items-center gap-0.5 text-xs text-zinc-500">
                  <Minus className="h-3.5 w-3.5" /> 0
                </span>
              ))}
            <span className={cn("shrink-0 text-xs tabular-nums text-zinc-400")}>
              {preseason
                ? `roster value ${e.roster_value}`
                : `${e.wins}–${e.losses}${e.ties ? `–${e.ties}` : ""} · ${e.points_for.toFixed(1)} PF`}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
