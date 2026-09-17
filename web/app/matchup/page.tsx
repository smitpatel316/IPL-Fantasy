"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { ApiError, type LineupOut, type MatchupOut, type PlayerOut } from "@/lib/types";
import { PageHeader, ErrorBox } from "@/components/ui";
import { ScrollHint } from "@/components/ScrollHint";
import { cn } from "@/lib/utils";
import { Swords, Trophy, X } from "lucide-react";

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

/* P3-A9 (QA m6): matchup drill-down — tap/click a card to see the two
   lineups side by side. Accessible dialog: Escape closes, backdrop click
   closes, focus moves into the dialog on open. */

const LINEUP_SLOT_ORDER = ["WK", "BAT", "AR", "BOWL", "UTIL", "BN", "IL"];

function LineupColumn({
  teamName,
  teamId,
  week,
  players,
}: {
  teamName: string;
  teamId: number;
  week: number;
  players: Map<number, PlayerOut>;
}) {
  const [lineup, setLineup] = useState<LineupOut | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    let live = true;
    api
      .getLineup(teamId, week)
      .then((l) => {
        if (live) setLineup(l);
      })
      .catch((e) => {
        if (live) setErr(e instanceof ApiError ? e.message : "lineup load failed");
      });
    return () => {
      live = false;
    };
  }, [teamId, week]);

  return (
    <div className="min-w-0 flex-1">
      <h3 className="mb-3 truncate text-sm font-bold text-white">{teamName}</h3>
      {err ? (
        <ErrorBox message={err} />
      ) : lineup === null ? (
        <p className="text-xs text-zinc-500">Loading lineup…</p>
      ) : (
        <div className="space-y-3">
          {LINEUP_SLOT_ORDER.map((slot) => {
            const ids = lineup.slots?.[slot] ?? [];
            if (ids.length === 0) return null;
            return (
              <div key={slot}>
                <p className="mb-1 text-[10px] font-bold uppercase tracking-wider text-zinc-500">{slot}</p>
                <ul className="space-y-1">
                  {ids.map((pid) => {
                    const p = players.get(pid);
                    return (
                      <li
                        key={pid}
                        className="flex items-center justify-between gap-2 rounded-md bg-slate-900/70 px-2.5 py-1.5"
                      >
                        <span className="min-w-0 truncate text-xs font-medium text-zinc-200">
                          {p?.name ?? `#${pid}`}
                        </span>
                        <span className="shrink-0 font-mono text-[10px] text-zinc-500">
                          {p?.ipl_team_code ?? ""}
                        </span>
                      </li>
                    );
                  })}
                </ul>
              </div>
            );
          })}
          {!LINEUP_SLOT_ORDER.some((s) => (lineup.slots?.[s] ?? []).length > 0) && (
            <p className="text-xs text-zinc-600">No lineup set for week {week} yet.</p>
          )}
        </div>
      )}
    </div>
  );
}

function MatchupDetail({
  matchup,
  onClose,
}: {
  matchup: MatchupOut;
  onClose: () => void;
}) {
  const [players, setPlayers] = useState<Map<number, PlayerOut>>(new Map());
  const [err, setErr] = useState("");
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let live = true;
    api
      .listPlayers({ league_id: 1 })
      .then((list) => {
        if (live) setPlayers(new Map(list.map((p) => [p.id, p])));
      })
      .catch((e) => {
        if (live) setErr(e instanceof ApiError ? e.message : "players load failed");
      });
    return () => {
      live = false;
    };
  }, []);

  const close = useCallback(onClose, [onClose]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
    };
    document.addEventListener("keydown", onKey);
    dialogRef.current?.querySelector("button")?.focus();
    return () => document.removeEventListener("keydown", onKey);
  }, [close]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
      onClick={close}
      role="presentation"
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label={`${matchup.team_a_name} vs ${matchup.team_b_name}, week ${matchup.week_no}`}
        className="max-h-[85vh] w-full max-w-2xl overflow-y-auto rounded-2xl border border-slate-700 bg-midnight-soft p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <div className="min-w-0">
            <p className="text-[11px] font-bold uppercase tracking-wider text-zinc-500">
              Week {matchup.week_no} · matchup detail
            </p>
            <h2 className="mt-1 truncate text-lg font-bold text-white">
              {matchup.team_a_name} <span className="text-zinc-500">vs</span> {matchup.team_b_name}
            </h2>
            <p className="mt-0.5 font-mono text-sm tabular-nums text-zinc-400">
              {matchup.score_a.toFixed(1)} – {matchup.score_b.toFixed(1)}
            </p>
          </div>
          <button
            onClick={close}
            aria-label="Close matchup detail"
            className="shrink-0 rounded-lg p-2 text-zinc-400 hover:bg-slate-800 hover:text-white"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        {err && (
          <div className="mb-4">
            <ErrorBox message={err} />
          </div>
        )}
        <div className="flex gap-6">
          <LineupColumn teamName={matchup.team_a_name} teamId={matchup.team_a_id} week={matchup.week_no} players={players} />
          <div className="w-px shrink-0 bg-slate-800" aria-hidden />
          <LineupColumn teamName={matchup.team_b_name} teamId={matchup.team_b_id} week={matchup.week_no} players={players} />
        </div>
      </div>
    </div>
  );
}

export default function MatchupPage() {
  const [matchups, setMatchups] = useState<MatchupOut[]>([]);
  const [week, setWeek] = useState(1);
  const [err, setErr] = useState("");
  const [openMatchup, setOpenMatchup] = useState<MatchupOut | null>(null);

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
              <button
                key={m.id}
                type="button"
                onClick={() => setOpenMatchup(m)}
                aria-label={`View matchup detail: ${m.team_a_name} vs ${m.team_b_name}, week ${m.week_no}`}
                className="cursor-pointer rounded-xl border border-slate-800 bg-midnight-soft p-5 text-left transition hover:border-slate-600 hover:bg-slate-900/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-trophy-gold"
              >
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
                <p className="mt-3 text-[11px] font-semibold text-zinc-500">Tap to view lineups →</p>
              </button>
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

      {openMatchup && <MatchupDetail matchup={openMatchup} onClose={() => setOpenMatchup(null)} />}
    </div>
  );
}
