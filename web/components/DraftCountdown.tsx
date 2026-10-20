"use client";

/* P5-W51: scheduled-draft countdown — ticks client-side every second
   off the key-dates projection's draft entry (the commissioner's
   scheduled instant). Flips to "scheduled time has passed" once the
   instant passes. Hidden while the draft is unscheduled or already
   started. Read-only: it never starts the draft on its own. */

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { KeyDateEntryOut } from "@/lib/types";
import { Timer } from "lucide-react";

function fmtRemaining(ms: number): string {
  const total = Math.max(0, Math.floor(ms / 1000));
  const d = Math.floor(total / 86400);
  const h = Math.floor((total % 86400) / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d}d ${pad(h)}:${pad(m)}:${pad(s)}`;
}

export function DraftCountdown({
  leagueId,
  leagueStatus,
}: {
  leagueId: number;
  leagueStatus: string;
}) {
  const [entry, setEntry] = useState<KeyDateEntryOut | null>(null);
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    let cancelled = false;
    api
      .keyDates(leagueId)
      .then((d) => {
        if (!cancelled)
          setEntry(d.entries.find((e) => e.key === "draft") ?? null);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [leagueId]);

  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);

  if (leagueStatus !== "setup" || !entry?.at) return null;

  const instant = new Date(entry.at).getTime();
  const passed = now >= instant;

  return (
    <section
      aria-label="Draft countdown"
      className="rounded-xl border border-slate-800 bg-midnight-soft p-5"
    >
      <h2 className="mb-2 flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-zinc-300">
        <Timer className="h-4 w-4 text-gold-ink" /> Draft countdown
      </h2>
      {passed ? (
        <p className="text-sm font-semibold text-gold-ink">
          The scheduled draft time has passed — start the draft from the
          league page.
        </p>
      ) : (
        <>
          <p
            className="text-2xl font-bold tabular-nums text-zinc-100"
            aria-live="off"
          >
            {fmtRemaining(instant - now)}
          </p>
          <p className="mt-1 text-xs text-zinc-500">
            {entry.at_pt} · {entry.at_ist}
          </p>
        </>
      )}
    </section>
  );
}
