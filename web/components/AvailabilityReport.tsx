"use client";

/* P5-W29: league-wide availability report — flagged rostered players
   grouped by status and team, IL occupancy, and flagged free agents.
   Read-only; moves still go through the lineup editor. */

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { AvailabilityReportOut } from "@/lib/types";
import { AvailabilityDot } from "@/components/AvailabilityDot";
import { HeartPulse } from "lucide-react";

export function AvailabilityReport({ leagueId }: { leagueId: number }) {
  const [data, setData] = useState<AvailabilityReportOut | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .availabilityReport(leagueId)
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [leagueId]);

  if (!data) return null;
  const empty = data.groups.length === 0 && data.free_agents.length === 0;

  return (
    <section
      aria-label="League availability report"
      className="mb-6 rounded-xl border border-slate-800 bg-midnight-soft p-4 sm:p-5"
    >
      <h2 className="mb-1 flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-zinc-300">
        <HeartPulse className="h-4 w-4 text-trophy-gold" /> Availability report
      </h2>
      <p className="mb-3 text-xs text-zinc-500">{data.basis}</p>
      {empty && (
        <p className="text-sm text-zinc-500">
          Everyone is available — no rostered player or free agent is flagged.
        </p>
      )}
      {data.groups.map((g) => (
        <div key={g.availability} className="mb-3">
          <h3 className="mb-1 text-xs font-bold uppercase tracking-wider text-zinc-400">
            {g.availability === "out" ? "Out / injured" : "Retired"}
          </h3>
          {g.teams.map((t) => (
            <p key={t.team_id} className="py-0.5 text-sm text-zinc-300">
              <span className="font-medium text-white">{t.team_name}:</span>{" "}
              {t.players.map((p, i) => (
                <span key={p.id}>
                  {i > 0 && ", "}
                  <span className="mr-1 inline-flex align-middle">
                    <AvailabilityDot availability={p.availability} />
                  </span>
                  {p.name}
                  {p.on_il && <span className="text-xs text-zinc-500"> (on IL)</span>}
                </span>
              ))}
            </p>
          ))}
        </div>
      ))}
      {data.free_agents.length > 0 && (
        <p className="py-0.5 text-sm text-zinc-300">
          <span className="font-medium text-white">Free agents flagged:</span>{" "}
          {data.free_agents.map((p) => p.name).join(", ")} — check before bidding.
        </p>
      )}
      <p className="mt-2 text-xs text-zinc-500">
        IL slots:{" "}
        {data.il_occupancy
          .map((o) => `${o.team_name} ${o.il_player_name ? `(${o.il_player_name})` : "open"}`)
          .join(" · ")}
      </p>
    </section>
  );
}
