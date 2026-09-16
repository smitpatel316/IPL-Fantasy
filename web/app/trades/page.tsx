"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { ApiError, type PlayerOut, type TeamOut, type TradeOut } from "@/lib/types";
import { PageHeader, ErrorBox, EngineStub } from "@/components/ui";
import { cn } from "@/lib/utils";
import { ArrowLeftRight, ArrowRight, Clock } from "lucide-react";

const STATUS_STYLE: Record<string, string> = {
  pending: "bg-trophy-gold/15 text-trophy-gold",
  proposed: "bg-trophy-gold/15 text-trophy-gold",
  accepted: "bg-pitch-green/15 text-pitch-green",
  executed: "bg-pitch-green/15 text-pitch-green",
  rejected: "bg-brick-red/15 text-brick-red",
  vetoed: "bg-brick-red/15 text-brick-red",
};

function PlayerChips({ ids, names }: { ids: number[]; names: Map<number, string> }) {
  if (ids.length === 0) return <span className="text-xs text-zinc-600">—</span>;
  return (
    <div className="flex flex-wrap gap-1.5">
      {ids.map((id) => (
        <span
          key={id}
          className="rounded-lg border border-slate-700 bg-slate-800/60 px-2.5 py-1 text-xs font-medium text-zinc-100"
        >
          {names.get(id) ?? `Player #${id}`}
        </span>
      ))}
    </div>
  );
}

export default function TradesPage() {
  const [trades, setTrades] = useState<TradeOut[]>([]);
  const [teams, setTeams] = useState<TeamOut[]>([]);
  const [players, setPlayers] = useState<PlayerOut[]>([]);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.listTrades(1).then(setTrades).catch((e) => setErr(e instanceof ApiError ? e.message : "load failed"));
    api.listTeams(1).then(setTeams).catch(() => {});
    api.listPlayers({ league_id: 1 }).then(setPlayers).catch(() => {});
  }, []);

  const teamName = useMemo(() => new Map(teams.map((t) => [t.id, t.name])), [teams]);
  const playerName = useMemo(() => new Map(players.map((p) => [p.id, p.name])), [players]);

  return (
    <div>
      <PageHeader
        title="Trades"
        sub="Propose · accept / reject · commissioner review (2-day window) · deadline end of week 6"
      />
      {err && <div className="mb-4"><ErrorBox message={err} /></div>}

      <h2 className="mb-3 text-sm font-bold uppercase tracking-wider text-zinc-300">Trade inbox</h2>
      {trades.length === 0 ? (
        <EngineStub track="P2-L4" what="Trade engine (proposals, legality checks, veto)" />
      ) : (
        <ul className="space-y-3">
          {trades.map((t) => (
            <li key={t.id} className="rounded-xl border border-slate-800 bg-midnight-soft p-4 sm:p-5">
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <span className="inline-flex items-center gap-1.5 text-sm font-semibold text-white">
                  <ArrowLeftRight className="h-4 w-4 text-trophy-gold" />
                  {teamName.get(t.from_team_id) ?? `Team ${t.from_team_id}`}
                </span>
                <ArrowRight className="h-3.5 w-3.5 text-zinc-600" />
                <span className="text-sm font-semibold text-white">
                  {teamName.get(t.to_team_id) ?? `Team ${t.to_team_id}`}
                </span>
                <span className={cn("ml-auto rounded px-1.5 py-0.5 text-[11px] font-bold uppercase", STATUS_STYLE[t.status] ?? "bg-slate-800 text-zinc-400")}>
                  {t.status}
                </span>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-zinc-500">
                    {teamName.get(t.from_team_id) ?? `Team ${t.from_team_id}`} gives
                  </p>
                  <PlayerChips ids={t.gives} names={playerName} />
                </div>
                <div>
                  <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-zinc-500">
                    {teamName.get(t.to_team_id) ?? `Team ${t.to_team_id}`} gives
                  </p>
                  <PlayerChips ids={t.receives} names={playerName} />
                </div>
              </div>
              {t.review_deadline && (
                <p className="mt-3 flex items-center gap-1.5 text-xs text-zinc-500">
                  <Clock className="h-3.5 w-3.5" /> Review deadline {t.review_deadline}
                </p>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
