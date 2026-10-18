"use client";

/* P5-W27: key dates & deadlines — every entry is derived server-side
   from the source that enforces it (settings, lineup locks, waiver
   schedule). Rendered in PT with IST alongside. */

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { KeyDatesOut } from "@/lib/types";
import { CalendarClock } from "lucide-react";
import { cn } from "@/lib/utils";

const STATE_STYLE: Record<string, string> = {
  past: "text-zinc-500",
  "next-up": "text-gold-ink font-semibold",
  upcoming: "text-zinc-300",
};

export function KeyDates({ leagueId }: { leagueId: number }) {
  const [data, setData] = useState<KeyDatesOut | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .keyDates(leagueId)
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [leagueId]);

  if (!data) return null;

  return (
    <section
      aria-label="Key dates and deadlines"
      className="mb-6 rounded-xl border border-slate-800 bg-midnight-soft p-4 sm:p-5"
    >
      <h2 className="mb-3 flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-zinc-300">
        <CalendarClock className="h-4 w-4 text-gold-ink" /> Key dates
        <a
          href={api.keyDatesIcsUrl(leagueId)}
          download
          className="ml-auto text-[11px] font-semibold normal-case tracking-normal text-win-ink hover:underline"
        >
          Add to calendar (.ics)
        </a>
      </h2>
      <ul className="divide-y divide-slate-800/60">
        {data.entries.map((e) => (
          <li key={e.key} className="flex flex-wrap items-baseline gap-x-3 py-2 text-sm">
            <span className={cn("min-w-44", STATE_STYLE[e.state])}>
              {e.label}
              {e.state === "next-up" && (
                <span className="ml-2 rounded bg-trophy-gold/15 px-1.5 py-0.5 text-[10px] font-bold uppercase">
                  Next up
                </span>
              )}
            </span>
            <span className="text-xs text-zinc-400">
              {e.at_pt ? `${e.at_pt} · ${e.at_ist}` : e.detail}
            </span>
            {e.at_pt && <span className="w-full text-xs text-zinc-500">{e.detail}</span>}
          </li>
        ))}
      </ul>
    </section>
  );
}
