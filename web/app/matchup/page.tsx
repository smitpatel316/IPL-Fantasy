"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ApiError, type MatchupOut } from "@/lib/types";
import { PageHeader, ErrorBox } from "@/components/ui";
import { ScrollHint } from "@/components/ScrollHint";
import { cn } from "@/lib/utils";
import { Swords, Trophy } from "lucide-react";

const WEEKS = [1, 2, 3, 4, 5, 6, 7, 8];

const STATUS_STYLE: Record<string, string> = {
  scheduled: "bg-slate-800 text-zinc-400",
  live: "bg-brick-red/15 text-brick-red",
  final: "bg-pitch-green/15 text-pitch-green",
  complete: "bg-pitch-green/15 text-pitch-green",
};

function TeamRow({
  name,
  score,
  winner,
  align,
}: {
  name: string;
  score: number;
  winner: boolean;
  align: "left" | "right";
}) {
  return (
    <div className="flex-1">
      <div className={cn("flex items-center gap-2", align === "right" && "flex-row-reverse text-right")}>
        {winner && <Trophy className="h-4 w-4 shrink-0 text-trophy-gold" aria-label="Winner" />}
        <p className={cn("min-w-0 flex-1 truncate text-sm font-semibold", winner ? "text-white" : "text-zinc-300")}>
          {name}
        </p>
      </div>
      <p className={cn("mt-1 text-3xl font-extrabold tabular-nums tracking-tight", winner ? "text-trophy-gold" : "text-white")}>
        {score.toFixed(1)}
      </p>
    </div>
  );
}

export default function MatchupPage() {
  const [matchups, setMatchups] = useState<MatchupOut[]>([]);
  const [week, setWeek] = useState(1);
  const [err, setErr] = useState("");

  useEffect(() => {
    api
      .listMatchups(1, week)
      .then(setMatchups)
      .catch((e) => setErr(e instanceof ApiError ? e.message : "load failed"));
  }, [week]);

  return (
    <div>
      <PageHeader title="Matchups" sub="Weekly head-to-head · Monday–Sunday periods" />

      <div className="mb-5 rounded-xl border border-slate-800 bg-midnight-soft p-2">
        <ScrollHint className="flex gap-1.5 overflow-x-auto" role="tablist" aria-label="Week">
          {WEEKS.map((w) => (
            <button
              key={w}
              role="tab"
              aria-selected={week === w}
              onClick={() => setWeek(w)}
              className={cn(
                "shrink-0 rounded-lg px-4 py-2 text-sm font-semibold transition-colors",
                week === w ? "bg-trophy-gold text-midnight" : "text-zinc-400 hover:bg-slate-800 hover:text-white",
              )}
            >
              W{w}
            </button>
          ))}
        </ScrollHint>
      </div>

      {err && <div className="mb-4"><ErrorBox message={err} /></div>}

      {matchups.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2">
          {matchups.map((m) => {
            const played = m.score_a > 0 || m.score_b > 0;
            const aWin = played && m.score_a >= m.score_b;
            const bWin = played && m.score_b > m.score_a;
            const total = m.score_a + m.score_b;
            const aPct = total > 0 ? (m.score_a / total) * 100 : 50;
            return (
              <div key={m.id} className="rounded-xl border border-slate-800 bg-midnight-soft p-5">
                <div className="mb-4 flex items-center justify-between">
                  <span className="inline-flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-zinc-500">
                    <Swords className="h-3.5 w-3.5" /> Week {m.week_no}
                  </span>
                  <span className={cn("rounded px-1.5 py-0.5 text-[11px] font-bold uppercase", STATUS_STYLE[m.status] ?? "bg-slate-800 text-zinc-400")}>
                    {m.status}
                  </span>
                </div>
                <div className="flex items-start justify-between gap-4">
                  <TeamRow name={m.team_a_name} score={m.score_a} winner={aWin} align="left" />
                  <span className="pt-7 text-xs font-bold text-zinc-600">VS</span>
                  <TeamRow name={m.team_b_name} score={m.score_b} winner={bWin} align="right" />
                </div>
                <div className="mt-4 flex h-1.5 overflow-hidden rounded-full bg-slate-800" aria-hidden>
                  <div className={cn("h-full rounded-l-full", aWin ? "bg-trophy-gold" : "bg-slate-600")} style={{ width: `${aPct}%` }} />
                  <div className={cn("h-full rounded-r-full", bWin ? "bg-trophy-gold" : "bg-slate-600")} style={{ width: `${100 - aPct}%` }} />
                </div>
                {!played && (
                  <p className="mt-3 text-xs text-zinc-600">Not played yet — set your lineup before the week's first ball.</p>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        !err && (
          <div className="rounded-xl border border-dashed border-slate-700 p-10 text-center">
            <Swords className="mx-auto mb-3 h-8 w-8 text-zinc-700" />
            <p className="text-sm font-medium text-zinc-400">
              {week >= 7
                ? `Playoff matchups for week ${week} are set once the regular season ends and the top 4 are seeded.`
                : `No matchups scheduled for week ${week} yet.`}
            </p>
            <p className="mt-1 text-xs text-zinc-600">
              {week >= 7
                ? "The playoff bracket is decided by final regular-season standings."
                : "The schedule is set once the league fills and the draft completes."}
            </p>
          </div>
        )
      )}
    </div>
  );
}
