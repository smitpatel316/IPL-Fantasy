"use client";

/* P5-W28: per-team FAAB & transaction ledger — the managing team's
   own money trail with running balances. Claim-gated server-side;
   a 403 (claimed team, wrong browser) renders an honest note. */

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ApiError, type TeamLedgerOut } from "@/lib/types";
import { ReceiptText } from "lucide-react";

export function TeamLedger({
  leagueId,
  teamId,
}: {
  leagueId: number;
  teamId: number | null;
}) {
  const [data, setData] = useState<TeamLedgerOut | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (teamId == null) return;
    let cancelled = false;
    setErr("");
    api
      .getLedger(leagueId, teamId)
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch((e) => {
        if (!cancelled) {
          setData(null);
          setErr(
            e instanceof ApiError && e.status === 403
              ? "This team is claimed — its ledger is visible only from the browser that claimed it."
              : "ledger load failed",
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, [leagueId, teamId]);

  if (teamId == null) return null;

  return (
    <section
      aria-label="FAAB and transaction ledger"
      className="mb-6 rounded-xl border border-slate-800 bg-midnight-soft p-4 sm:p-5"
    >
      <h2 className="mb-1 flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-zinc-300">
        <ReceiptText className="h-4 w-4 text-gold-ink" /> My ledger
      </h2>
      {err && <p className="text-sm text-zinc-500">{err}</p>}
      {data && data.entries.length <= 1 && (
        <p className="text-sm text-zinc-500">
          No transactions yet — your ${data.starting_faab} FAAB is untouched.
        </p>
      )}
      {data && data.entries.length > 1 && (
        <ul className="divide-y divide-slate-800/60">
          {data.entries.map((e) => (
            <li key={e.id} className="flex flex-wrap items-baseline gap-x-3 py-2 text-sm text-zinc-300">
              <span className="flex-1">{e.text}</span>
              {e.faab_delta !== 0 && (
                <span className={e.faab_delta > 0 ? "text-win-ink" : "text-loss-ink"}>
                  {e.faab_delta > 0 ? `+$${e.faab_delta}` : `-$${-e.faab_delta}`}
                </span>
              )}
              <span className="text-xs text-zinc-500">balance ${e.balance_after}</span>
            </li>
          ))}
        </ul>
      )}
      {data && (
        <p className="mt-2 text-xs text-zinc-500">
          Current FAAB: ${data.current_faab}. Pending bids stay sealed (amount-free)
          until the Wednesday run resolves them.
        </p>
      )}
    </section>
  );
}
