"use client";

/* P5-W24: league polls — quick advisory votes next to the message
   board (e.g. picking a draft date). Any claimed team can create a
   poll; each team votes once and can change its vote while the poll
   is open; the creator or the commissioner can close it. ADVISORY
   ONLY: results never change league settings — the API enforces the
   claim gate (P4-W18), this component just renders. */

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ApiError, type PollOut } from "@/lib/types";
import { BarChart3, Check, Plus } from "lucide-react";
import { cn } from "@/lib/utils";

export function LeaguePolls({
  leagueId,
  myTeamId,
}: {
  leagueId: number;
  myTeamId: number | null;
}) {
  const [polls, setPolls] = useState<PollOut[]>([]);
  const [commissionerTeamId, setCommissionerTeamId] = useState<number | null>(null);
  const [err, setErr] = useState("");
  const [question, setQuestion] = useState("");
  const [optionsText, setOptionsText] = useState("");
  const [creating, setCreating] = useState(false);

  const load = useCallback(async () => {
    try {
      const out = await api.getPolls(leagueId, myTeamId);
      setPolls(out.polls);
      setCommissionerTeamId(out.commissioner_team_id);
      setErr("");
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "polls load failed");
    }
  }, [leagueId, myTeamId]);

  useEffect(() => {
    load();
  }, [load]);

  async function create() {
    if (myTeamId == null) return;
    const options = optionsText
      .split("\n")
      .map((s) => s.trim())
      .filter(Boolean);
    setCreating(true);
    try {
      await api.createPoll(leagueId, myTeamId, question.trim(), options);
      setQuestion("");
      setOptionsText("");
      await load();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "poll create failed");
    } finally {
      setCreating(false);
    }
  }

  async function vote(poll: PollOut, optionId: number) {
    if (myTeamId == null || poll.closed) return;
    try {
      const updated = await api.votePoll(leagueId, poll.id, myTeamId, optionId);
      setPolls((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "vote failed");
    }
  }

  async function close(poll: PollOut) {
    if (myTeamId == null) return;
    try {
      const updated = await api.closePoll(leagueId, poll.id, myTeamId);
      setPolls((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "close failed");
    }
  }

  const canClose = (p: PollOut) =>
    myTeamId != null && (myTeamId === p.team_id || myTeamId === commissionerTeamId);

  return (
    <section
      aria-label="League polls"
      className="mb-5 rounded-xl border border-slate-800 bg-midnight-soft p-5"
    >
      <h2 className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-zinc-300">
        <BarChart3 className="h-4 w-4 text-trophy-gold" /> League polls
        <span className="text-[11px] font-medium normal-case tracking-normal text-zinc-500">
          advisory only — results never change league settings
        </span>
      </h2>

      {err && <p className="mt-3 text-xs text-brick-red">{err}</p>}

      {polls.length === 0 && !err && (
        <p className="mt-3 text-sm text-zinc-500">
          No polls yet — float the first question (draft date, anyone?).
        </p>
      )}

      <ul className="mt-4 space-y-4">
        {polls.map((p) => (
          <li key={p.id} className="rounded-lg border border-slate-800/80 p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-white">{p.question}</p>
                <p className="mt-0.5 text-[11px] text-zinc-500">
                  by {p.team_name} · {p.total_votes}{" "}
                  {p.total_votes === 1 ? "vote" : "votes"}
                  {p.closed ? " · closed" : " · open"}
                </p>
              </div>
              {!p.closed && canClose(p) && (
                <button
                  type="button"
                  onClick={() => void close(p)}
                  className="shrink-0 text-[11px] font-semibold text-zinc-400 underline hover:text-zinc-200"
                >
                  Close poll
                </button>
              )}
            </div>
            <ul className="mt-3 space-y-1.5">
              {p.options.map((o) => {
                const mine = p.my_option_id === o.id;
                return (
                  <li key={o.id}>
                    <button
                      type="button"
                      disabled={p.closed || myTeamId == null}
                      onClick={() => void vote(p, o.id)}
                      className={cn(
                        "relative block w-full overflow-hidden rounded-md border px-3 py-2 text-left text-sm",
                        mine
                          ? "border-trophy-gold/60 text-white"
                          : "border-slate-800 text-zinc-300",
                        !p.closed && myTeamId != null && "hover:border-slate-600",
                        (p.closed || myTeamId == null) && "cursor-default",
                      )}
                    >
                      <span
                        aria-hidden
                        className="absolute inset-y-0 left-0 bg-trophy-gold/10"
                        style={{ width: `${o.pct}%` }}
                      />
                      <span className="relative flex items-center justify-between gap-2">
                        <span className="flex items-center gap-1.5">
                          {o.label}
                          {mine && <Check className="h-3.5 w-3.5 text-trophy-gold" />}
                        </span>
                        <span className="tabular-nums text-zinc-400">
                          {o.votes} · {o.pct.toFixed(1)}%
                        </span>
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
            {!p.closed && myTeamId != null && (
              <p className="mt-2 text-[11px] text-zinc-600">
                Tap an option to vote — you can change it while the poll is open.
              </p>
            )}
          </li>
        ))}
      </ul>

      {myTeamId != null ? (
        <div className="mt-5 border-t border-slate-800 pt-4">
          <label className="block text-[11px] font-semibold uppercase tracking-wider text-zinc-500">
            New poll
          </label>
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            maxLength={200}
            placeholder="Question — e.g. Which day should we draft?"
            className="mt-2 w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white placeholder:text-zinc-600"
          />
          <textarea
            value={optionsText}
            onChange={(e) => setOptionsText(e.target.value)}
            rows={3}
            placeholder={"One option per line (2–6)\nSaturday\nSunday"}
            className="mt-2 w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white placeholder:text-zinc-600"
          />
          <button
            type="button"
            disabled={creating || !question.trim()}
            onClick={() => void create()}
            className="mt-2 flex items-center gap-1.5 rounded-md bg-trophy-gold px-3 py-1.5 text-xs font-bold text-midnight disabled:opacity-50"
          >
            <Plus className="h-3.5 w-3.5" /> Create poll
          </button>
        </div>
      ) : (
        <p className="mt-4 border-t border-slate-800 pt-3 text-[11px] text-zinc-600">
          Pick your team above to create a poll or vote.
        </p>
      )}
    </section>
  );
}
