"use client";

/* P5-W12: all-teams roster view — every team's full roster grouped
   by slot, with its overseas-starter count vs the D8 cap, FAAB
   remaining, and P5-W6 availability dots. Fully read-only: there are
   no mutation affordances here for any team. */

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ApiError, type RostersOut } from "@/lib/types";
import { AvailabilityDot } from "@/components/AvailabilityDot";
import { Users } from "lucide-react";

const SLOT_ORDER = ["WK", "BAT", "AR", "BOWL", "UTIL", "BN", "IL"] as const;

export function AllRosters({ leagueId }: { leagueId: number }) {
  const [data, setData] = useState<RostersOut | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    let cancelled = false;
    api
      .getRosters(leagueId)
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch((e) => {
        if (!cancelled)
          setErr(e instanceof ApiError ? e.message : "rosters load failed");
      });
    return () => {
      cancelled = true;
    };
  }, [leagueId]);

  if (err || !data || data.teams.length === 0) return null;
  const anyRostered = data.teams.some((t) => t.roster_size > 0);
  if (!anyRostered) return null;

  return (
    <section
      aria-label="All teams' rosters"
      className="mb-5 rounded-xl border border-slate-800 bg-midnight-soft p-5"
    >
      <h2 className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-zinc-300">
        <Users className="h-4 w-4 text-gold-ink" /> Teams
        <span className="text-[11px] font-medium normal-case tracking-normal text-zinc-500">
          every roster, grouped by slot · overseas starters vs the 4-cap · read-only
        </span>
      </h2>
      <div className="mt-4 grid gap-4 md:grid-cols-2">
        {data.teams.map((t) => (
          <div
            key={t.team_id}
            className="rounded-lg border border-slate-800 bg-slate-900/40 p-4"
          >
            <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
              <h3 className="text-sm font-bold text-white">{t.team_name}</h3>
              <span className="text-xs text-zinc-500">
                {t.roster_size} players · {t.overseas_starters}/4 overseas starters · $
                {t.faab_remaining} FAAB left
              </span>
            </div>
            <div className="mt-3 space-y-1.5">
              {SLOT_ORDER.map((slot) => {
                const players = t.slots[slot] ?? [];
                if (players.length === 0) return null;
                return (
                  <div key={slot} className="flex items-start gap-2 text-xs">
                    <span className="w-9 shrink-0 pt-0.5 font-bold uppercase tracking-wide text-zinc-500">
                      {slot}
                    </span>
                    <span className="flex flex-wrap gap-x-3 gap-y-1">
                      {players.map((p) => (
                        <span key={p.id} className="inline-flex items-center gap-1.5 text-zinc-200">
                          <AvailabilityDot availability={p.availability} />
                          {p.name}
                          <span className="text-zinc-500">
                            {p.ipl_team_code ?? ""}
                            {p.is_overseas ? " · OS" : ""}
                          </span>
                        </span>
                      ))}
                    </span>
                  </div>
                );
              })}
              {t.roster_size === 0 && (
                <p className="text-xs text-zinc-600">No roster yet — the draft fills this in.</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
