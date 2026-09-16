"use client";

import styles from "@/app/draft-room/draft-room.module.css";

function fmtClock(secs: number): string {
  const s = Math.max(0, Math.ceil(secs));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

interface DraftClockProps {
  secsLeft: number | null;
  totalSecs: number;
  teamName: string;
  myTurn: boolean;
}

/** Circular pick-clock with the on-the-clock team. Purely visual. */
export function DraftClock({ secsLeft, totalSecs, teamName, myTurn }: DraftClockProps) {
  const frac = secsLeft != null && totalSecs > 0 ? Math.max(0, Math.min(1, secsLeft / totalSecs)) : 0;
  const urgent = secsLeft != null && secsLeft < 15;
  const R = 30;
  const C = 2 * Math.PI * R;
  const ring = urgent ? "#ef4444" : "#f59e0b";

  return (
    <div className="flex items-center gap-4">
      <div className={`relative h-20 w-20 shrink-0 ${urgent ? styles.urgent : ""}`}>
        <svg viewBox="0 0 72 72" className="h-20 w-20 -rotate-90" aria-hidden="true">
          <circle cx="36" cy="36" r={R} fill="none" stroke="#1e293b" strokeWidth="7" />
          <circle
            cx="36"
            cy="36"
            r={R}
            fill="none"
            stroke={ring}
            strokeWidth="7"
            strokeLinecap="round"
            strokeDasharray={C}
            strokeDashoffset={C * (1 - frac)}
            style={{ transition: "stroke-dashoffset 1s linear, stroke 0.3s" }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className={`font-mono text-lg font-bold ${urgent ? "text-red-400" : "text-white"}`}>
            {secsLeft != null ? fmtClock(secsLeft) : "—"}
          </span>
        </div>
      </div>
      <div className="min-w-0">
        <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-500">On the clock</p>
        <p className="truncate text-lg font-bold text-white">{teamName}</p>
        {myTurn ? (
          <p
            className={`${styles.pop} mt-1 inline-block rounded-full bg-trophy-gold px-2.5 py-0.5 text-xs font-extrabold uppercase tracking-wide text-midnight`}
          >
            Your pick
          </p>
        ) : (
          <p className="mt-1 text-xs text-slate-500">Waiting for their pick…</p>
        )}
      </div>
    </div>
  );
}
