"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { ApiError, type PlayerDetailOut } from "@/lib/types";
import { PageHeader, ErrorBox } from "@/components/ui";
import { cn } from "@/lib/utils";
import { ArrowLeft, Plane } from "lucide-react";

const ROLE_BADGE: Record<string, string> = {
  WK: "bg-yellow-400/10 text-yellow-300",
  BAT: "bg-blue-400/10 text-blue-300",
  AR: "bg-purple-400/10 text-purple-300",
  BOWL: "bg-emerald-400/10 text-emerald-300",
};

export default function PlayerDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const [id, setId] = useState<string | null>(null);
  const [player, setPlayer] = useState<PlayerDetailOut | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    params.then((p) => setId(p.id));
  }, [params]);

  useEffect(() => {
    if (!id) return;
    api
      .getPlayer(id, 1)
      .then(setPlayer)
      .catch((e) => setErr(e instanceof ApiError ? e.message : "load failed"));
  }, [id]);

  if (err) return <div className="pt-8"><ErrorBox message={err} /></div>;
  if (!player)
    return (
      <div className="space-y-3 pt-8" aria-label="Loading">
        {[0, 1].map((i) => (
          <div key={i} className="h-24 animate-pulse rounded-xl bg-midnight-soft" />
        ))}
      </div>
    );

  return (
    <div>
      <Link href="/players" className="mb-4 inline-flex items-center gap-1.5 text-sm text-zinc-400 hover:text-white">
        <ArrowLeft className="h-4 w-4" /> All players
      </Link>
      <PageHeader
        title={player.name}
        sub={`${player.ipl_team_code ?? "—"} · season ${player.season}`}
      />

      <div className="grid gap-5 lg:grid-cols-3">
        <section className="rounded-xl border border-slate-800 bg-midnight-soft p-5">
          <h2 className="mb-3 text-sm font-bold uppercase tracking-wider text-zinc-300">Profile</h2>
          <dl className="space-y-2 text-sm">
            <div className="flex items-baseline justify-between gap-4">
              <dt className="text-zinc-500">Role</dt>
              <dd>
                {player.role ? (
                  <span className={cn("rounded px-1.5 py-0.5 text-xs font-bold", ROLE_BADGE[player.role])}>
                    {player.role}
                  </span>
                ) : (
                  "—"
                )}
              </dd>
            </div>
            <div className="flex items-baseline justify-between gap-4">
              <dt className="text-zinc-500">IPL team</dt>
              <dd className="font-medium text-zinc-200">{player.ipl_team_code ?? "—"}</dd>
            </div>
            <div className="flex items-baseline justify-between gap-4">
              <dt className="text-zinc-500">Overseas</dt>
              <dd className="font-medium text-zinc-200">
                {player.is_overseas ? (
                  <span className="inline-flex items-center gap-1"><Plane className="h-3.5 w-3.5" /> Yes</span>
                ) : (
                  "No"
                )}
              </dd>
            </div>
            <div className="flex items-baseline justify-between gap-4">
              <dt className="text-zinc-500">Preseason rank</dt>
              <dd className="font-medium text-zinc-200">{player.preseason_rank ?? "—"}</dd>
            </div>
            <div className="flex items-baseline justify-between gap-4">
              <dt className="text-zinc-500">Ownership</dt>
              <dd className="font-medium text-zinc-200">
                {player.ownership_pct != null ? `${player.ownership_pct.toFixed(0)}% of leagues` : "—"}
              </dd>
            </div>
            <div className="flex items-baseline justify-between gap-4">
              <dt className="text-zinc-500">Avg points</dt>
              <dd className="font-medium text-zinc-200">
                {player.avg_points != null ? player.avg_points.toFixed(1) : "—"}
              </dd>
            </div>
          </dl>
        </section>

        <section className="rounded-xl border border-slate-800 bg-midnight-soft p-5">
          <h2 className="mb-3 text-sm font-bold uppercase tracking-wider text-zinc-300">Owned by</h2>
          {player.owners.length === 0 ? (
            <p className="text-sm text-pitch-green">Free agent in every league.</p>
          ) : (
            <ul className="space-y-2 text-sm">
              {player.owners.map((o) => (
                <li key={`${o.league_id}-${o.team_id}`} className="flex items-baseline justify-between gap-4">
                  <span className="text-zinc-400">{o.league_name}</span>
                  <Link href={`/league/${o.league_id}`} className="font-medium text-zinc-100 hover:text-trophy-gold">
                    {o.team_name}
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="rounded-xl border border-slate-800 bg-midnight-soft p-5">
          <h2 className="mb-3 text-sm font-bold uppercase tracking-wider text-zinc-300">Match log</h2>
          {player.match_log.length === 0 ? (
            <p className="text-sm text-zinc-500">
              No scored matches yet — match-by-match points land with the season scoring pipeline.
            </p>
          ) : (
            <>
              <p className="mb-3 text-sm text-zinc-400">
                {player.matches_played} matches · {player.total_points} total points
              </p>
              <ul className="space-y-1.5 text-sm">
                {player.match_log.map((m) => (
                  <li key={m.match_id} className="flex items-baseline justify-between gap-3">
                    <span className="text-zinc-400">
                      {m.home_code ?? "?"} v {m.away_code ?? "?"}
                      <span className="ml-2 text-[11px] text-zinc-600">
                        {m.week_no ? `Wk ${m.week_no} · ` : ""}{m.match_date_ist ?? ""}
                      </span>
                    </span>
                    <span className="font-semibold tabular-nums text-white">{m.fantasy_points}</span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </section>
      </div>
    </div>
  );
}
