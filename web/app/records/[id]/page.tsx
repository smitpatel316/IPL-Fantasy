"use client";

/* P5-W46: the league records book — highest weekly score, largest
   margin of victory, longest win streak, narrowest win, most points in
   a loss. All values come from persisted FINAL matchups via
   GET /api/leagues/{id}/records; an unscored league shows the honest
   pre-season empty state. Read-only. */

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useLeague } from "@/lib/league-context";
import { ApiError, type LeagueRecordsOut } from "@/lib/types";import { PageHeader, Card, EmptyState, ErrorBox } from "@/components/ui";
import { Trophy } from "lucide-react";

export default function RecordsPage({ params }: { params: Promise<{ id: string }> }) {
  const [id, setId] = useState<string | null>(null);
  const { setLeagueId } = useLeague();
  const [rec, setRec] = useState<LeagueRecordsOut | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    params.then((p) => {
      setId(p.id);
      // Viewing a league makes it the current league for every tab (P4-W7).
      const n = Number(p.id);
      if (Number.isFinite(n) && n > 0) setLeagueId(n);
    });
  }, [params, setLeagueId]);

  useEffect(() => {
    if (!id) return;
    api
      .getRecords(id)
      .then(setRec)
      .catch((e) => setErr(e instanceof ApiError ? e.message : "load failed"));
  }, [id]);

  if (err) return <div className="pt-8"><ErrorBox message={err} /></div>;
  if (!rec)
    return (
      <div className="space-y-3 pt-8" aria-label="Loading">
        {[0, 1, 2].map((i) => (
          <div key={i} className="h-14 animate-pulse rounded-xl bg-midnight-soft" />
        ))}
      </div>
    );

  return (
    <div>
      <PageHeader
        title="Records book"
        sub={`League ${id} · ${rec.scored} scored matchup${rec.scored === 1 ? "" : "s"}`}
      />
      {rec.records.length === 0 ? (
        <EmptyState
          icon={<Trophy className="h-6 w-6" />}
          title="No records yet"
          sub="No matchups are finalized — records land here once weeks are scored."
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {rec.records.map((r) => (
            <Card key={r.key} className="p-5">
              <p className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
                {r.label}
              </p>
              <p className="tnum mt-2 text-4xl font-extrabold tracking-tight text-gold-400">
                {r.value}
              </p>
              <p className="mt-1.5 text-sm text-zinc-400">{r.detail}</p>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
