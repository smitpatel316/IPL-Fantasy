"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useLeague } from "@/lib/league-context";
import { ApiError, type ScheduleMatrixOut } from "@/lib/types";
import { PageHeader, ErrorBox } from "@/components/ui";
import { cn } from "@/lib/utils";
import { CalendarDays } from "lucide-react";

/**
 * P5-W15: schedule matrix — IPL team x fantasy week game counts, the
 * whole-picture view behind the per-player schedule badges (P3-A6).
 * 0-game weeks are byes; 3+ game weeks are double/triple rounds
 * (blueprint §12 "double-game-round framing").
 */
export default function SchedulePage() {
  const { leagueId } = useLeague();
  const [matrix, setMatrix] = useState<ScheduleMatrixOut | null>(null);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    setErr("");
    api
      .scheduleMatrix(leagueId)
      .then(setMatrix)
      .catch((e) => setErr(e instanceof ApiError ? e.message : "load failed"))
      .finally(() => setLoading(false));
  }, [leagueId]);

  const weeks = matrix?.rows[0]?.games_by_week.length ?? 8;

  return (
    <div>
      <PageHeader
        title="Schedule matrix"
        sub="Games per IPL team in every fantasy week — spot the bye weeks and the double-game rounds before you draft or bid"
      />
      {err && <div className="mb-4"><ErrorBox message={err} /></div>}
      {loading && <p className="text-sm text-zinc-500">Loading…</p>}
      {matrix && matrix.rows.length === 0 && (
        <p className="rounded-xl border border-slate-800 bg-midnight-soft p-8 text-center text-sm text-zinc-500">
          No fixture imported yet for the {matrix.season} season — the matrix fills in
          when the season fixture lands.
        </p>
      )}
      {matrix && matrix.rows.length > 0 && (
        <section className="overflow-hidden rounded-xl border border-slate-800">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[36rem] text-sm">
              <thead className="bg-midnight-soft">
                <tr className="text-left text-[11px] uppercase tracking-wider text-zinc-500">
                  <th className="px-4 py-3 font-semibold">IPL team</th>
                  {Array.from({ length: weeks }).map((_, i) => (
                    <th key={i} className="px-3 py-3 text-center font-semibold">
                      W{i + 1}
                      {i + 1 >= 7 && <span className="ml-1 text-[10px] text-gold-ink">PO</span>}
                    </th>
                  ))}
                  <th className="px-4 py-3 text-right font-semibold">Total</th>
                </tr>
              </thead>
              <tbody>
                {matrix.rows.map((row) => (
                  <tr key={row.ipl_team_code} className="border-t border-slate-800/60">
                    <td className="px-4 py-2.5">
                      <span className="rounded bg-slate-800 px-1.5 py-0.5 text-xs font-bold text-zinc-200">
                        {row.ipl_team_code}
                      </span>
                    </td>
                    {row.games_by_week.map((games, i) => (
                      <td key={i} className="px-3 py-2.5 text-center tabular-nums">
                        <span
                          className={cn(
                            "inline-block min-w-7 rounded-md px-1.5 py-0.5 text-xs font-semibold",
                            games === 0 && "bg-brick-red/15 text-red-300",
                            games >= 3 && "bg-pitch-green/15 font-bold text-win-ink",
                            games > 0 && games < 3 && "text-zinc-300",
                          )}
                          title={
                            games === 0
                              ? `Bye week — ${row.ipl_team_code} play no games in week ${i + 1}`
                              : games >= 3
                                ? `Double-game round — ${games} games in week ${i + 1}`
                                : undefined
                          }
                        >
                          {games}
                        </span>
                      </td>
                    ))}
                    <td className="px-4 py-2.5 text-right font-semibold tabular-nums text-white">
                      {row.total}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-slate-800/60 bg-midnight-soft px-4 py-3 text-[11px] text-zinc-500">
            <span className="inline-flex items-center gap-1.5">
              <CalendarDays className="h-3.5 w-3.5" />
              <span className="rounded bg-brick-red/15 px-1.5 py-0.5 font-semibold text-red-300">0</span> bye week
            </span>
            <span>
              <span className="rounded bg-pitch-green/15 px-1.5 py-0.5 font-semibold text-win-ink">3+</span>{" "}
              double/triple-game round
            </span>
            <span className="ml-auto">
              {matrix.source.includes("standin")
                ? `Source: ${matrix.source} — the 2026 fixture stands in until the real ${matrix.season} fixture imports (~Feb 2027).`
                : `Source: ${matrix.source || "imported fixture"}.`}
            </span>
          </p>
        </section>
      )}
    </div>
  );
}
