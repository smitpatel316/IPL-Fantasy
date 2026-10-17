"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useLeague } from "@/lib/league-context";
import { ApiError, type CheatSheetOut } from "@/lib/types";
import { PageHeader, ErrorBox } from "@/components/ui";
import { AvailabilityDot } from "@/components/AvailabilityDot";

/**
 * P5-W25: draft cheat sheet — every draftable player tiered by D7 role
 * from consensus preseason ranks (a tier break wherever the rank gap
 * to the next player at that role exceeds the pinned threshold).
 * Print-friendly + CSV download of the same payload for draft day.
 */
export default function CheatSheetPage() {
  const { leagueId } = useLeague();
  const [sheet, setSheet] = useState<CheatSheetOut | null>(null);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    setErr("");
    api
      .cheatSheet(leagueId)
      .then(setSheet)
      .catch((e) => setErr(e instanceof ApiError ? e.message : "load failed"))
      .finally(() => setLoading(false));
  }, [leagueId]);

  const empty = sheet && sheet.groups.every((g) => g.players.length === 0);

  return (
    <div>
      <PageHeader
        title="Draft cheat sheet"
        sub="Tiered by role from consensus preseason ranks — take it offline on draft day"
      />
      {err && <div className="mb-4"><ErrorBox message={err} /></div>}
      {loading && <p className="text-sm text-zinc-500">Loading…</p>}
      {sheet && (
        <div className="mb-4 flex flex-wrap items-center gap-3 print:hidden">
          <button
            onClick={() => window.print()}
            className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs font-medium text-zinc-200 hover:border-trophy-gold"
          >
            Print sheet
          </button>
          <a
            href={api.cheatSheetCsvUrl(leagueId)}
            className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs font-medium text-zinc-200 hover:border-trophy-gold"
          >
            Download CSV
          </a>
          <p className="text-xs text-zinc-500">
            Tiers break where the consensus-rank gap passes {sheet.tier_gap_threshold}.
            {sheet.source
              ? ` Schedule totals from the ${sheet.source} fixture (standin until the real 2027 fixture imports).`
              : " Schedule totals land when the season fixture imports."}
          </p>
        </div>
      )}
      {sheet && empty && (
        <p className="rounded-xl border border-slate-800 bg-midnight-soft p-8 text-center text-sm text-zinc-500">
          No ranked players yet for the {sheet.season} season — the sheet fills in
          once the player universe and preseason ranks land.
        </p>
      )}
      {sheet &&
        sheet.groups.map(
          (g) =>
            g.players.length > 0 && (
              <section key={g.role} className="mb-6">
                <h2 className="mb-2 text-sm font-bold uppercase tracking-wider text-zinc-300">
                  {g.role}
                </h2>
                <div className="overflow-hidden rounded-xl border border-slate-800">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="bg-midnight-soft text-left text-xs uppercase tracking-wide text-zinc-500">
                        <th className="px-3 py-2">Tier</th>
                        <th className="px-3 py-2">Player</th>
                        <th className="px-3 py-2">Team</th>
                        <th className="px-3 py-2">Rank</th>
                        <th className="px-3 py-2">Avg pts</th>
                        <th className="px-3 py-2">Games</th>
                      </tr>
                    </thead>
                    <tbody>
                      {g.players.map((p, i) => (
                        <tr
                          key={p.id}
                          className={
                            (i > 0 && g.players[i - 1].tier !== p.tier
                              ? "border-t-2 border-t-trophy-gold/60 "
                              : "border-t border-slate-800/60 ") +
                            "text-zinc-300"
                          }
                        >
                          <td className="px-3 py-2 font-semibold text-trophy-gold">
                            {p.tier}
                          </td>
                          <td className="px-3 py-2">
                            <span className="mr-2 inline-flex align-middle">
                              <AvailabilityDot availability={p.availability} />
                            </span>
                            <span className="font-medium text-white">{p.name}</span>
                            {p.is_overseas && (
                              <span className="ml-2 text-xs text-zinc-500">OS</span>
                            )}
                          </td>
                          <td className="px-3 py-2">{p.ipl_team_code ?? "—"}</td>
                          <td className="px-3 py-2">{p.preseason_rank ?? "—"}</td>
                          <td className="px-3 py-2">{p.avg_points ?? "—"}</td>
                          <td className="px-3 py-2">{p.total_games ?? "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            ),
        )}
    </div>
  );
}
