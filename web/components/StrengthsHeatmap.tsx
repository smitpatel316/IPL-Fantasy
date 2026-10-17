"use client";

/* P5-W33: league strengths heatmap — role-by-role roster value for
   every team. Values and shades are computed server-side (GET
   /leagues/{id}/strengths): starter rank value per team x role
   using the P5-W9 convention (value = pool + 1 - consensus rank),
   shade = cell vs the league average at that role with pinned
   thresholds (>=1.50 -> 2, >=1.15 -> 1, <=0.50 -> -2, <=0.85 -> -1,
   else 0). The total column is identical to the power-rankings
   roster_value for the same DB state. Read-only for all teams. */

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ApiError, type StrengthsOut } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Grid3x3 } from "lucide-react";

const ROLES = ["WK", "BAT", "AR", "BOWL"] as const;

// Shade -> cell styling. Green above the league average at the
// role, red below it; intensity follows the server-pinned shade.
const SHADE_STYLE: Record<number, string> = {
  2: "bg-pitch-green/40 text-white",
  1: "bg-pitch-green/15 text-emerald-200",
  0: "bg-slate-800/60 text-zinc-300",
  [-1]: "bg-brick-red/15 text-red-200",
  [-2]: "bg-brick-red/40 text-white",
};

const SHADE_LABEL: Record<number, string> = {
  2: "well above league average",
  1: "above league average",
  0: "near league average",
  [-1]: "below league average",
  [-2]: "well below league average",
};

export function StrengthsHeatmap({ leagueId }: { leagueId: number }) {
  const [data, setData] = useState<StrengthsOut | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    let cancelled = false;
    api
      .getStrengths(leagueId)
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch((e) => {
        if (!cancelled)
          setErr(e instanceof ApiError ? e.message : "strengths load failed");
      });
    return () => {
      cancelled = true;
    };
  }, [leagueId]);

  if (err) return null; // a quiet extra — never break the league page
  if (!data) return null;

  if (!data.drafted || data.rows.length === 0) {
    return (
      <section
        aria-label="Team strengths"
        className="mb-5 rounded-xl border border-dashed border-slate-800 px-5 py-4"
      >
        <h2 className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-zinc-300">
          <Grid3x3 className="h-4 w-4 text-trophy-gold" /> Team strengths
        </h2>
        <p className="mt-1 text-sm text-zinc-500">
          Strengths land when the draft completes — every team gets a
          role-by-role roster-value heatmap (WK / BAT / AR / BOWL) shaded
          against the league average, so you can scout trade partners at a
          glance.
        </p>
      </section>
    );
  }

  return (
    <section
      aria-label="Team strengths"
      className="mb-5 rounded-xl border border-slate-800 bg-midnight-soft p-5"
    >
      <h2 className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-zinc-300">
        <Grid3x3 className="h-4 w-4 text-trophy-gold" /> Team strengths
        <span className="text-[11px] font-medium normal-case tracking-normal text-zinc-500">
          starter roster value by role, shaded vs the league average at
          that role — total matches the power-rankings roster value
        </span>
      </h2>

      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-[540px] text-sm">
          <thead>
            <tr className="text-left text-[11px] uppercase tracking-wider text-zinc-500">
              <th className="px-2 py-2 font-semibold">Team</th>
              {ROLES.map((role) => (
                <th key={role} className="px-2 py-2 text-center font-semibold">
                  {role}
                  <span className="block text-[10px] font-medium normal-case text-zinc-600">
                    avg {data.averages[role] ?? 0}
                  </span>
                </th>
              ))}
              <th className="px-2 py-2 text-right font-semibold">Total</th>
            </tr>
          </thead>
          <tbody>
            {data.rows.map((row) => (
              <tr key={row.team_id} className="border-t border-slate-800/60">
                <td className="max-w-[180px] truncate px-2 py-2 font-semibold text-zinc-100">
                  {row.team_name}
                </td>
                {ROLES.map((role) => {
                  const cell =
                    row.cells.find((c) => c.role === role) ??
                    { role, value: 0, shade: 0 };
                  return (
                    <td key={role} className="px-1.5 py-1.5 text-center">
                      <span
                        title={`${row.team_name} ${role}: ${cell.value} — ${SHADE_LABEL[cell.shade] ?? SHADE_LABEL[0]}`}
                        className={cn(
                          "block rounded-md px-2 py-1.5 font-semibold tabular-nums",
                          SHADE_STYLE[cell.shade] ?? SHADE_STYLE[0],
                        )}
                      >
                        {cell.value}
                      </span>
                    </td>
                  );
                })}
                <td className="px-2 py-2 text-right font-bold tabular-nums text-white">
                  {row.total}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-zinc-600">
        <span>
          <span className="mr-1 inline-block h-2.5 w-2.5 rounded-sm bg-pitch-green/40" />
          Well above average (≥1.5×)
        </span>
        <span>
          <span className="mr-1 inline-block h-2.5 w-2.5 rounded-sm bg-pitch-green/15" />
          Above average (≥1.15×)
        </span>
        <span>
          <span className="mr-1 inline-block h-2.5 w-2.5 rounded-sm bg-slate-800" />
          Near average
        </span>
        <span>
          <span className="mr-1 inline-block h-2.5 w-2.5 rounded-sm bg-brick-red/15" />
          Below average (≤0.85×)
        </span>
        <span>
          <span className="mr-1 inline-block h-2.5 w-2.5 rounded-sm bg-brick-red/40" />
          Well below average (≤0.5×)
        </span>
      </p>
      <p className="mt-2 text-[11px] text-zinc-600">
        Read-only scouting view — values are preseason-rank value only, no
        scoring model. A UTIL starter counts under his real role.
      </p>
    </section>
  );
}
