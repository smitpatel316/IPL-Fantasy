"use client";

/* P5-W48: the weekly recap — /recap/[id]/week/[n]. Biggest upset,
   highest scorer, closest matchup, biggest blowout for one scored
   week, all from persisted matchup scores. An unscored week shows the
   honest 'week not scored yet' state. Read-only. */

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useLeague } from "@/lib/league-context";
import { ApiError, type WeeklyRecapOut } from "@/lib/types";
import { PageHeader, Card, EmptyState, ErrorBox } from "@/components/ui";
import { Newspaper } from "lucide-react";
import { cn } from "@/lib/utils";

const WEEKS = [1, 2, 3, 4, 5, 6, 7, 8];

export default function RecapPage({
  params,
}: {
  params: Promise<{ id: string; n: string }>;
}) {
  const [id, setId] = useState<string | null>(null);
  const [week, setWeek] = useState(1);
  const { setLeagueId } = useLeague();
  const [recap, setRecap] = useState<WeeklyRecapOut | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    params.then((p) => {
      setId(p.id);
      const n = Number(p.n);
      if (Number.isFinite(n) && n >= 1 && n <= WEEKS.length) setWeek(n);
      // Viewing a league makes it the current league for every tab (P4-W7).
      const lid = Number(p.id);
      if (Number.isFinite(lid) && lid > 0) setLeagueId(lid);
    });
  }, [params, setLeagueId]);

  useEffect(() => {
    if (!id) return;
    setRecap(null);
    api
      .getRecap(id, week)
      .then(setRecap)
      .catch((e) => setErr(e instanceof ApiError ? e.message : "load failed"));
  }, [id, week]);

  if (err) return <div className="pt-8"><ErrorBox message={err} /></div>;

  return (
    <div>
      <PageHeader title="Weekly recap" sub={`League ${id} · the week in review`} />

      <div className="mb-5 rounded-xl border border-slate-800 bg-midnight-soft p-2">
        <div className="flex gap-1.5 overflow-x-auto" role="tablist" aria-label="Week">
          {WEEKS.map((w) => (
            <Link
              key={w}
              href={`/recap/${id}/week/${w}`}
              role="tab"
              aria-selected={week === w}
              onClick={() => setWeek(w)}
              className={cn(
                "shrink-0 rounded-lg px-4 py-2 text-sm font-semibold transition-colors",
                week === w ? "bg-trophy-gold text-midnight" : "text-zinc-400 hover:bg-slate-800 hover:text-white"
              )}
            >
              W{w}
            </Link>
          ))}
        </div>
      </div>

      {!recap ? (
        <div className="space-y-3" aria-label="Loading">
          {[0, 1].map((i) => (
            <div key={i} className="h-14 animate-pulse rounded-xl bg-midnight-soft" />
          ))}
        </div>
      ) : !recap.scored ? (
        <EmptyState
          icon={<Newspaper className="h-6 w-6" />}
          title={`Week ${week} isn't scored yet`}
          sub="The recap lands here once the week's matchups are finalized."
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {recap.facts.map((f) => (
            <Card key={f.key} className="p-5">
              <p className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
                {f.label}
              </p>
              <p className="tnum mt-2 text-4xl font-extrabold tracking-tight text-gold-400">
                {f.value}
              </p>
              <p className="mt-1.5 text-sm text-zinc-400">{f.detail}</p>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
