"use client";

/* P3-A6 (D10 option 4): schedule-aware UI nudges.
   Shared hook + badge rendering so the draft room and the waiver wire show
   per-IPL-team game counts for a fantasy week — schedule luck as a
   draftable/waivable skill ("MI 3 games this week"). */

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import type { ScheduleNudgesOut } from "@/lib/types";

export interface ScheduleBadges {
  /** ipl_team_code -> games that week */
  map: Map<string, number>;
  weeks: number[];
  week: number;
  setWeek: (w: number) => void;
  range: string | null;
  loading: boolean;
}

export function useScheduleBadges(leagueId: number | string, initialWeek = 1): ScheduleBadges {
  const [week, setWeek] = useState(initialWeek);
  const [data, setData] = useState<ScheduleNudgesOut | null>(null);
  useEffect(() => {
    if (!leagueId) return;
    let live = true;
    api
      .scheduleNudges(leagueId, week)
      .then((d) => {
        if (live) setData(d);
      })
      .catch(() => {
        if (live) setData(null);
      });
    return () => {
      live = false;
    };
  }, [leagueId, week]);
  const map = useMemo(() => {
    const m = new Map<string, number>();
    for (const g of data?.games ?? []) m.set(g.ipl_team_code, g.games);
    return m;
  }, [data]);
  const range =
    data?.week_start && data?.week_end ? `${data.week_start} – ${data.week_end}` : null;
  return { map, weeks: data?.weeks_available ?? [], week, setWeek, range, loading: data === null };
}

/** Color semantics: more games = more lineup chances. */
export function gamesBadgeClass(games: number): string {
  if (games >= 3) return "border-trophy-gold/50 bg-trophy-gold/10 text-trophy-gold";
  if (games === 2) return "border-emerald-800 bg-emerald-950/50 text-emerald-300";
  if (games === 1) return "border-slate-700 bg-slate-800/60 text-slate-400";
  return "border-slate-800 bg-slate-900/60 text-slate-600";
}

export function GameCountBadge({ code, games }: { code: string; games: number }) {
  return (
    <span
      title={`${code} plays ${games} game${games === 1 ? "" : "s"} this fantasy week`}
      className={`rounded border px-1 font-mono text-[10px] font-semibold ${gamesBadgeClass(games)}`}
    >
      {code} {games}g
    </span>
  );
}

/** Week selector pills for the schedule outlook. */
export function ScheduleWeekPicker({
  weeks,
  week,
  setWeek,
}: {
  weeks: number[];
  week: number;
  setWeek: (w: number) => void;
}) {
  if (weeks.length === 0) return null;
  return (
    <div className="flex flex-wrap items-center gap-1">
      <span className="mr-1 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
        Schedule week
      </span>
      {weeks.map((w) => (
        <button
          key={w}
          onClick={() => setWeek(w)}
          className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold transition ${
            w === week
              ? "bg-trophy-gold text-midnight"
              : "border border-slate-700 text-slate-400 hover:border-slate-500 hover:text-slate-200"
          }`}
        >
          W{w}
        </button>
      ))}
    </div>
  );
}
