"use client";

/* P5-W3: mock-draft UI — pre-season practice drafts against bots.
   Launches P5-L1's POST /api/mock-draft/{league_id} (ephemeral,
   in-memory on the server, zero writes to the live league), then
   replays the completed board pick by pick so managers can watch it
   fill, with per-team projected rosters building alongside. Reuses
   the draft room's DraftFeed component for the pick feed. */

import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/lib/api";
import { useLeague } from "@/lib/league-context";
import { ApiError, type MockBotIn, type MockDraftOut, type MockPickOut } from "@/lib/types";
import { PageHeader, ErrorBox } from "@/components/ui";
import { DraftFeed, type DraftFeedItem } from "@/components/DraftFeed";
import { cn } from "@/lib/utils";
import { Bot, Dices, FastForward, Play, RotateCcw } from "lucide-react";

const SLOT_ORDER = ["WK", "BAT", "AR", "BOWL", "UTIL", "BN", "IL"];
const BOT_COUNTS = [4, 6, 8, 10];
const REVEAL_MS = 90;

const input =
  "rounded-md border border-slate-700 bg-slate-900 px-2 py-1.5 text-sm text-white";

function defaultBots(count: number): MockBotIn[] {
  // Mirrors the server default: alternating sharp/casual, sharp first.
  return Array.from({ length: count }, (_, i) => ({
    name: `Bot ${i + 1}`,
    difficulty: (i % 2 === 0 ? "sharp" : "casual") as MockBotIn["difficulty"],
  }));
}

export default function MockDraftPage() {
  const { leagueId } = useLeague();
  const [botCount, setBotCount] = useState(8);
  const [seed, setSeed] = useState("");
  const [result, setResult] = useState<MockDraftOut | null>(null);
  const [revealed, setRevealed] = useState(0);
  const [running, setRunning] = useState(false);
  const [err, setErr] = useState("");
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  const total = result?.picks.length ?? 0;
  const done = result != null && revealed >= total;

  useEffect(() => {
    if (!result) return;
    timer.current = setInterval(() => {
      setRevealed((r) => {
        if (r >= result.picks.length) {
          if (timer.current) clearInterval(timer.current);
          return r;
        }
        return r + 1;
      });
    }, REVEAL_MS);
    return () => {
      if (timer.current) clearInterval(timer.current);
    };
  }, [result]);

  async function run() {
    setRunning(true);
    setErr("");
    setResult(null);
    setRevealed(0);
    try {
      const seedNum = seed.trim() === "" ? undefined : Number(seed);
      const out = await api.runMockDraft(leagueId, {
        bots: defaultBots(botCount),
        ...(seedNum != null && Number.isFinite(seedNum) ? { seed: seedNum } : {}),
      });
      setResult(out);
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "mock draft failed");
    } finally {
      setRunning(false);
    }
  }

  const shownPicks = useMemo(
    () => (result ? result.picks.slice(0, revealed) : []),
    [result, revealed],
  );

  const feedItems: DraftFeedItem[] = useMemo(
    () =>
      [...shownPicks].reverse().map((p) => ({
        key: `pick-${p.pick_no}`,
        text: `#${p.pick_no} · R${p.round_no} · ${p.team_name} (${p.difficulty}) — ${p.player_name} (${p.slot})`,
        auto: true,
      })),
    [shownPicks],
  );

  const rounds = useMemo(() => {
    if (!result) return [];
    const byRound = new Map<number, MockPickOut[]>();
    for (const p of result.picks) {
      const arr = byRound.get(p.round_no) ?? [];
      arr.push(p);
      byRound.set(p.round_no, arr);
    }
    return [...byRound.entries()].sort((a, b) => a[0] - b[0]);
  }, [result]);

  const rosterByTeam = useMemo(() => {
    const map = new Map<string, Map<string, string[]>>();
    for (const p of shownPicks) {
      if (!map.has(p.team_name)) map.set(p.team_name, new Map());
      const slots = map.get(p.team_name)!;
      const arr = slots.get(p.slot) ?? [];
      arr.push(p.player_name);
      slots.set(p.slot, arr);
    }
    return map;
  }, [shownPicks]);

  return (
    <div>
      <PageHeader
        title="Practice draft"
        sub="Mock draft vs bots — sharp bots draft by consensus ranks + schedule, casual bots draft with rank noise. Your live league is never touched."
      />

      <section className="mb-6 rounded-xl border border-slate-800 bg-midnight-soft p-4 sm:p-5">
        <div className="flex flex-wrap items-end gap-4">
          <label className="flex flex-col gap-1 text-xs font-medium text-slate-400">
            Bots
            <select
              className={input}
              value={botCount}
              onChange={(e) => setBotCount(Number(e.target.value))}
            >
              {BOT_COUNTS.map((n) => (
                <option key={n} value={n}>
                  {n} bots
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-xs font-medium text-slate-400">
            Seed (optional)
            <input
              className={cn(input, "w-28")}
              inputMode="numeric"
              placeholder="42"
              value={seed}
              onChange={(e) => setSeed(e.target.value)}
            />
          </label>
          <button
            type="button"
            onClick={run}
            disabled={running}
            className="flex items-center gap-2 rounded-md bg-trophy-gold px-4 py-2 text-sm font-bold text-midnight transition hover:bg-trophy-gold/90 disabled:opacity-50"
          >
            {result ? <RotateCcw className="h-4 w-4" /> : <Play className="h-4 w-4" />}
            {running ? "Drafting…" : result ? "Run another mock" : "Run practice draft"}
          </button>
          {result && !done && (
            <button
              type="button"
              onClick={() => setRevealed(total)}
              className="flex items-center gap-2 rounded-md border border-slate-700 px-3 py-2 text-sm text-zinc-300 transition hover:bg-slate-800"
            >
              <FastForward className="h-4 w-4" /> Show all picks
            </button>
          )}
        </div>
        <p className="mt-3 flex items-start gap-2 text-xs text-slate-500">
          <Dices className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          Same seed + same bots = same draft, every time. The draft runs instantly on the
          server; the board below replays it pick by pick so you can follow along.
        </p>
      </section>

      {err && (
        <div className="mb-4">
          <ErrorBox message={err} onRetry={run} />
        </div>
      )}

      {!result && !err && (
        <p className="rounded-xl border border-dashed border-slate-800 p-6 text-sm text-zinc-500">
          No mock draft yet — pick a bot count and run one. Projected rosters, the full
          pick board, and each bot&apos;s average consensus rank land here.
        </p>
      )}

      {result && (
        <>
          <section className="mb-6 flex flex-wrap items-center gap-x-5 gap-y-2 rounded-xl border border-slate-800 bg-midnight-soft px-5 py-3 text-sm text-zinc-300">
            <span className="flex items-center gap-2 font-semibold text-white">
              <Bot className="h-4 w-4 text-trophy-gold" />
              {done ? "Mock draft complete" : `Drafting… pick ${revealed} of ${total}`}
            </span>
            <span>Seed {result.seed}</span>
            <span>
              {result.teams.length} bots · {result.rounds} rounds · {total} picks
            </span>
            <span className="text-zinc-500">
              {result.schedule_weighted
                ? "Sharp bots weighted by weeks 1–3 schedule."
                : "No fixture data for this season — sharp bots used ranks only."}
            </span>
          </section>

          <div className="grid gap-6 lg:grid-cols-3">
            <div className="lg:col-span-1">
              <DraftFeed items={feedItems} />
            </div>

            <section
              aria-label="Draft board"
              className="rounded-xl border border-slate-800 bg-midnight-soft/70 p-4 lg:col-span-2"
            >
              <h2 className="mb-3 font-semibold text-white">Board</h2>
              <div className="space-y-2">
                {rounds.map(([roundNo, picks]) => (
                  <div key={roundNo} className="flex flex-wrap items-center gap-1.5">
                    <span className="w-10 shrink-0 font-mono text-[10px] uppercase tracking-widest text-slate-500">
                      R{roundNo}
                    </span>
                    {picks.map((p) => {
                      const shown = p.pick_no <= revealed;
                      return (
                        <span
                          key={p.pick_no}
                          className={cn(
                            "rounded-md border px-2 py-1 text-xs",
                            shown
                              ? "border-slate-700 bg-slate-800/80 text-white"
                              : "border-slate-800 bg-slate-900/40 text-slate-600",
                          )}
                          title={
                            shown
                              ? `${p.team_name} (${p.difficulty}) · ${p.slot}`
                              : `Pick ${p.pick_no}`
                          }
                        >
                          {shown ? p.player_name : `#${p.pick_no}`}
                        </span>
                      );
                    })}
                  </div>
                ))}
              </div>
            </section>
          </div>

          <section aria-label="Projected rosters" className="mt-6">
            <h2 className="mb-3 text-sm font-bold uppercase tracking-wider text-zinc-300">
              Projected rosters
            </h2>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              {result.teams.map((t) => {
                const slots = rosterByTeam.get(t.name);
                const picked =
                  slots != null
                    ? [...slots.values()].reduce((n, a) => n + a.length, 0)
                    : 0;
                return (
                  <div
                    key={t.name}
                    className="rounded-xl border border-slate-800 bg-midnight-soft/70 p-4"
                  >
                    <div className="mb-3 flex items-center justify-between gap-2">
                      <h3 className="font-semibold text-white">{t.name}</h3>
                      <span
                        className={cn(
                          "rounded-full px-2 py-0.5 text-[11px] font-bold uppercase",
                          t.difficulty === "sharp"
                            ? "bg-trophy-gold/15 text-trophy-gold"
                            : "bg-slate-800 text-slate-300",
                        )}
                      >
                        {t.difficulty}
                      </span>
                    </div>
                    <p className="mb-3 text-xs text-zinc-500">
                      Avg consensus rank{" "}
                      <span className="font-semibold text-zinc-300">
                        {t.avg_consensus_rank.toFixed(1)}
                      </span>{" "}
                      · {picked}/14 picked
                    </p>
                    {picked === 0 ? (
                      <p className="text-sm text-slate-500">No picks yet.</p>
                    ) : (
                      <div className="space-y-2.5">
                        {SLOT_ORDER.filter((s) => (slots?.get(s)?.length ?? 0) > 0).map(
                          (slot) => (
                            <div key={slot}>
                              <p className="mb-1 font-mono text-[10px] uppercase tracking-widest text-slate-500">
                                {slot}
                              </p>
                              <div className="flex flex-wrap gap-1.5">
                                {slots!.get(slot)!.map((name) => (
                                  <span
                                    key={name}
                                    className="rounded-md border border-slate-700 bg-slate-800/80 px-2 py-1 text-xs text-white"
                                  >
                                    {name}
                                  </span>
                                ))}
                              </div>
                            </div>
                          ),
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </section>
        </>
      )}
    </div>
  );
}
