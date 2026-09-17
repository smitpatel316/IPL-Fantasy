"use client";

import type { PlayerOut } from "@/lib/types";
import { GameCountBadge } from "@/components/ScheduleBadges";

const ROLE_STYLES: Record<string, string> = {
  WK: "border-sky-800 bg-sky-950/60 text-sky-300",
  BAT: "border-emerald-800 bg-emerald-950/60 text-emerald-300",
  AR: "border-amber-800 bg-amber-950/60 text-amber-300",
  BOWL: "border-rose-800 bg-rose-950/60 text-rose-300",
};

interface DraftPlayerCardProps {
  player: PlayerOut;
  myTurn: boolean;
  dnd: boolean;
  onDraft: (id: number) => void;
  onToggleDnd: (id: number, active: boolean) => void;
  /** P3-A6: ipl_team_code -> games this schedule week (badge rendering). */
  weekGames?: Map<string, number>;
}

/** One row on the available-players board. Visual only — actions pass through. */
export function DraftPlayerCard({ player: p, myTurn, dnd, onDraft, onToggleDnd, weekGames }: DraftPlayerCardProps) {
  const schedGames = p.ipl_team_code ? weekGames?.get(p.ipl_team_code) : undefined;
  return (
    <div
      className={`flex items-center gap-2 rounded-lg border px-3 py-2 transition-colors ${
        myTurn
          ? "border-trophy-gold/40 bg-midnight-soft hover:border-trophy-gold/70"
          : "border-slate-800/70 bg-midnight-soft/60 hover:border-slate-700"
      } ${dnd ? "opacity-50" : ""}`}
    >
      <span className="w-9 shrink-0 font-mono text-xs text-slate-500">#{p.preseason_rank ?? "–"}</span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-white">{p.name}</p>
        <div className="mt-1 flex items-center gap-1.5">
          {p.role && (
            <span className={`rounded border px-1 text-[10px] font-semibold ${ROLE_STYLES[p.role] ?? ""}`}>
              {p.role}
            </span>
          )}
          {p.ipl_team_code && (
            <span className="rounded bg-slate-800 px-1 font-mono text-[10px] text-slate-400">{p.ipl_team_code}</span>
          )}
          {schedGames !== undefined && p.ipl_team_code && (
            <GameCountBadge code={p.ipl_team_code} games={schedGames} />
          )}
          {p.is_overseas && (
            <span title="Overseas player" className="text-[10px] text-slate-500">
              ✈
            </span>
          )}
        </div>
      </div>
      <button
        onClick={() => onDraft(p.id)}
        disabled={!myTurn}
        className={`shrink-0 rounded-md px-3 py-1.5 text-xs font-bold uppercase tracking-wide transition ${
          myTurn
            ? "bg-trophy-gold text-midnight hover:brightness-110 active:scale-95"
            : "cursor-not-allowed bg-slate-800/70 text-slate-600"
        }`}
      >
        Draft
      </button>
      <button
        onClick={() => onToggleDnd(p.id, !dnd)}
        title={dnd ? "Remove from do-not-draft" : "Add to do-not-draft"}
        className={`shrink-0 rounded-md px-2 py-1.5 text-xs font-semibold transition ${
          dnd
            ? "border border-red-800 bg-red-950/60 text-red-300"
            : "border border-slate-700 text-slate-500 hover:border-slate-500 hover:text-slate-300"
        }`}
      >
        {dnd ? "✕ DND" : "DND"}
      </button>
    </div>
  );
}
