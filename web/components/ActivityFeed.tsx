"use client";

/* P5-W8: league activity feed — read-only projection of recorded
   league events (draft picks, waiver-run outcomes, executed/vetoed
   trades, commissioner adjustments), newest first with load-older
   paging. The API enforces the D6 invariant (pending claims absent,
   losing bids amount-free); this component just renders entries. */

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ApiError, type ActivityEntryOut } from "@/lib/types";
import { Activity } from "lucide-react";

const PAGE = 50;

const KIND_LABEL: Record<string, string> = {
  draft_pick: "Draft",
  waiver_won: "Waivers",
  waiver_lost: "Waivers",
  trade_executed: "Trade",
  trade_vetoed: "Trade",
  commissioner_faab: "Commissioner",
  commissioner_roster_add: "Commissioner",
  commissioner_roster_drop: "Commissioner",
};

export function ActivityFeed({ leagueId }: { leagueId: number }) {
  const [entries, setEntries] = useState<ActivityEntryOut[]>([]);
  const [total, setTotal] = useState(0);
  const [err, setErr] = useState("");

  const load = useCallback(
    async (offset: number) => {
      try {
        const feed = await api.getActivity(leagueId, PAGE, offset);
        setTotal(feed.total);
        setEntries((prev) =>
          offset === 0 ? feed.entries : [...prev, ...feed.entries],
        );
      } catch (e) {
        setErr(e instanceof ApiError ? e.message : "activity load failed");
      }
    },
    [leagueId],
  );

  useEffect(() => {
    load(0);
  }, [load]);

  return (
    <section
      aria-label="League activity"
      className="mb-5 rounded-xl border border-slate-800 bg-midnight-soft p-5"
    >
      <h2 className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-zinc-300">
        <Activity className="h-4 w-4 text-trophy-gold" /> League activity
        <span className="text-[11px] font-medium normal-case tracking-normal text-zinc-500">
          {total} event{total === 1 ? "" : "s"} · draft, waivers, trades, commissioner moves
        </span>
      </h2>

      {err && <p className="mt-2 text-xs text-brick-red">{err}</p>}

      {entries.length === 0 && !err ? (
        <p className="mt-4 text-sm text-zinc-500">
          Nothing yet — activity lands here as the draft, waiver runs, and trades happen.
        </p>
      ) : (
        <ul className="mt-4 divide-y divide-slate-800/60">
          {entries.map((e) => (
            <li key={e.id} className="flex items-start gap-3 py-2.5">
              <span className="mt-0.5 shrink-0 rounded bg-slate-800 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-zinc-400">
                {KIND_LABEL[e.kind] ?? "League"}
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-sm text-zinc-200">{e.text}</p>
                <p className="mt-0.5 text-xs text-zinc-500">{e.occurred_at} UTC</p>
              </div>
            </li>
          ))}
        </ul>
      )}

      {entries.length < total && (
        <button
          type="button"
          onClick={() => load(entries.length)}
          className="mt-3 rounded-md border border-slate-700 px-3 py-1.5 text-xs font-semibold text-zinc-300 transition hover:bg-slate-800"
        >
          Load older activity ({total - entries.length} more)
        </button>
      )}
    </section>
  );
}
