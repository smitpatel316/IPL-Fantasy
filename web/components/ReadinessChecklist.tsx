"use client";

/* P5-W10: season-start checklist — commissioner-facing readiness
   card. Every item is derived server-side from live DB state; each
   incomplete item links to the surface that fixes it. Collapses to
   a one-line "ready" note once everything is done. */

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { ApiError, type ReadinessOut } from "@/lib/types";
import { CheckCircle2, Circle, ClipboardCheck } from "lucide-react";

export function ReadinessChecklist({ leagueId }: { leagueId: number }) {
  const [data, setData] = useState<ReadinessOut | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    let cancelled = false;
    api
      .getReadiness(leagueId)
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch((e) => {
        if (!cancelled)
          setErr(e instanceof ApiError ? e.message : "readiness load failed");
      });
    return () => {
      cancelled = true;
    };
  }, [leagueId]);

  if (err || !data) return null;

  const allDone = data.ready_count === data.total_count;

  return (
    <section
      aria-label="Season-start checklist"
      className="mb-5 rounded-xl border border-slate-800 bg-midnight-soft p-5"
    >
      <h2 className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-zinc-300">
        <ClipboardCheck className="h-4 w-4 text-trophy-gold" /> Season-start checklist
        <span className="text-[11px] font-medium normal-case tracking-normal text-zinc-500">
          {allDone
            ? "all set — this league is ready for week 1"
            : `${data.ready_count}/${data.total_count} ready · for the commissioner`}
        </span>
      </h2>
      {!allDone && (
        <ul className="mt-4 space-y-2.5">
          {data.items.map((i) => (
            <li key={i.key} className="flex items-start gap-2.5 text-sm">
              {i.done ? (
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-pitch-green" />
              ) : (
                <Circle className="mt-0.5 h-4 w-4 shrink-0 text-zinc-600" />
              )}
              <div className="min-w-0 flex-1">
                <span className={i.done ? "text-zinc-400" : "font-medium text-zinc-100"}>
                  {i.label}
                </span>
                <span className="block text-xs text-zinc-500">{i.detail}</span>
              </div>
              {!i.done && (
                <Link
                  href={i.fix_href}
                  className="shrink-0 text-xs font-semibold text-pitch-green hover:underline"
                >
                  Fix →
                </Link>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
