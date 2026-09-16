"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { ApiError, type PlayerOut, type TeamOut, type WaiverClaimOut } from "@/lib/types";
import { PageHeader, ErrorBox, EngineStub } from "@/components/ui";
import { cn } from "@/lib/utils";
import { Gavel, CircleDollarSign, Timer, Scale, ArrowRight } from "lucide-react";

const STATUS_STYLE: Record<string, string> = {
  pending: "bg-trophy-gold/15 text-trophy-gold",
  won: "bg-pitch-green/15 text-pitch-green",
  lost: "bg-slate-800 text-zinc-500",
};

export default function WaiversPage() {
  const [teams, setTeams] = useState<TeamOut[]>([]);
  const [claims, setClaims] = useState<WaiverClaimOut[]>([]);
  const [players, setPlayers] = useState<PlayerOut[]>([]);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.listTeams(1).then(setTeams).catch(() => {});
    api.listPlayers({ league_id: 1 }).then(setPlayers).catch(() => {});
    api.pendingClaims(1, 1).then(setClaims).catch((e) => {
      if (!(e instanceof ApiError && e.status === 501)) setErr(e instanceof ApiError ? e.message : "load failed");
    });
  }, []);

  const playerName = useMemo(() => new Map(players.map((p) => [p.id, p.name])), [players]);
  const teamName = useMemo(() => new Map(teams.map((t) => [t.id, t.name])), [teams]);
  const sorted = useMemo(() => [...teams].sort((a, b) => b.faab_remaining - a.faab_remaining), [teams]);

  return (
    <div>
      <PageHeader title="Waivers" sub="Weekly blind FAAB · $100 season budget · runs Wednesday ~3am PT" />

      <div className="mb-5 grid gap-2 sm:grid-cols-3">
        {[
          { icon: Gavel, label: "Blind bids", sub: "Nobody sees your bid" },
          { icon: Timer, label: "Runs Wednesday", sub: "~3am PT, weekly" },
          { icon: Scale, label: "Tiebreak", sub: "Reverse standings" },
        ].map(({ icon: Icon, label, sub }) => (
          <div key={label} className="flex items-center gap-3 rounded-xl border border-slate-800 bg-midnight-soft px-4 py-3">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-trophy-gold/10 text-trophy-gold">
              <Icon className="h-4 w-4" />
            </span>
            <div>
              <p className="text-sm font-semibold text-white">{label}</p>
              <p className="text-xs text-zinc-500">{sub}</p>
            </div>
          </div>
        ))}
      </div>

      {err && <div className="mb-4"><ErrorBox message={err} /></div>}

      <section className="mb-6 rounded-xl border border-slate-800 bg-midnight-soft p-4 sm:p-5">
        <h2 className="mb-4 flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-zinc-300">
          <CircleDollarSign className="h-4 w-4 text-trophy-gold" /> FAAB remaining
        </h2>
        <div className="space-y-3">
          {sorted.map((t) => (
            <div key={t.id}>
              <div className="mb-1 flex items-baseline justify-between text-sm">
                <span className="font-medium text-zinc-200">{t.name}</span>
                <span className="tabular-nums font-bold text-trophy-gold">${t.faab_remaining}</span>
              </div>
              <div className="h-1.5 overflow-hidden rounded-full bg-slate-800">
                <div
                  className="h-full rounded-full bg-trophy-gold/80"
                  style={{ width: `${Math.max(0, Math.min(100, t.faab_remaining))}%` }}
                />
              </div>
            </div>
          ))}
          {sorted.length === 0 && <p className="text-sm text-zinc-600">No teams yet.</p>}
        </div>
      </section>

      <h2 className="mb-3 text-sm font-bold uppercase tracking-wider text-zinc-300">This week's claims</h2>
      {claims.length === 0 ? (
        <EngineStub track="P2-L3" what="Waiver claims (blind bids, reverse-standings tiebreak)" />
      ) : (
        <ul className="space-y-2">
          {claims.map((c) => (
            <li
              key={c.id}
              className="flex flex-wrap items-center gap-x-3 gap-y-1.5 rounded-xl border border-slate-800 bg-midnight-soft px-4 py-3 text-sm"
            >
              <span className="font-semibold text-white">{teamName.get(c.team_id) ?? `Team ${c.team_id}`}</span>
              <span className="inline-flex items-center gap-1.5 text-zinc-300">
                adds <span className="font-medium text-white">{playerName.get(c.add_player_id) ?? `#${c.add_player_id}`}</span>
              </span>
              {c.drop_player_id != null && (
                <span className="inline-flex items-center gap-1.5 text-zinc-500">
                  <ArrowRight className="h-3.5 w-3.5" />
                  drops {playerName.get(c.drop_player_id) ?? `#${c.drop_player_id}`}
                </span>
              )}
              <span className="ml-auto flex items-center gap-2">
                <span className="tabular-nums font-bold text-trophy-gold">${c.bid}</span>
                <span className={cn("rounded px-1.5 py-0.5 text-[11px] font-bold uppercase", STATUS_STYLE[c.status] ?? "bg-slate-800 text-zinc-400")}>
                  {c.status}
                </span>
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
