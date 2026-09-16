"use client";

import type { PlayerOut } from "@/lib/types";

const SLOT_ORDER = ["WK", "BAT", "AR", "BOWL", "UTIL", "BN", "IL"];

interface DraftRosterProps {
  roster: Record<string, number[]> | undefined;
  playerById: Map<number, PlayerOut>;
  dndIds: number[];
  onRemoveDnd: (id: number) => void;
}

/** My roster panel: slot-grouped picks + do-not-draft list. Visual only. */
export function DraftRoster({ roster, playerById, dndIds, onRemoveDnd }: DraftRosterProps) {
  const slots = SLOT_ORDER.filter((s) => (roster?.[s]?.length ?? 0) > 0);
  const picked = Object.values(roster ?? {}).reduce((n, ids) => n + ids.length, 0);

  return (
    <div className="rounded-xl border border-slate-800 bg-midnight-soft/70 p-4">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="font-semibold text-white">My roster</h2>
        <span className="rounded-full bg-slate-800 px-2 py-0.5 font-mono text-xs text-slate-300">{picked}/14</span>
      </div>
      {slots.length === 0 ? (
        <p className="text-sm text-slate-500">No picks yet — your squad builds here live.</p>
      ) : (
        <div className="space-y-2.5">
          {slots.map((slot) => (
            <div key={slot}>
              <p className="mb-1 font-mono text-[10px] uppercase tracking-widest text-slate-500">{slot}</p>
              <div className="flex flex-wrap gap-1.5">
                {(roster?.[slot] ?? []).map((pid) => (
                  <span
                    key={pid}
                    className="rounded-md border border-slate-700 bg-slate-800/80 px-2 py-1 text-xs text-white"
                  >
                    {playerById.get(pid)?.name ?? `#${pid}`}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
      {dndIds.length > 0 && (
        <div className="mt-4 border-t border-slate-800 pt-3">
          <p className="mb-1.5 text-[10px] uppercase tracking-widest text-slate-500">
            Do-not-draft ({dndIds.length})
          </p>
          <div className="flex flex-wrap gap-1.5">
            {dndIds.map((pid) => (
              <button
                key={pid}
                onClick={() => onRemoveDnd(pid)}
                title="Remove from do-not-draft"
                className="group rounded-md border border-red-900 bg-red-950/40 px-2 py-1 text-xs text-red-300 transition hover:border-red-700"
              >
                {playerById.get(pid)?.name ?? `#${pid}`}
                <span className="ml-1 text-red-500 group-hover:text-red-300">✕</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
