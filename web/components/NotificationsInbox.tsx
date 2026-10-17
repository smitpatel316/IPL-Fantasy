"use client";

/* P5-W20: "For you" notifications inbox — claim-aware per-team feed
   of persisted events that touch the managing-as team (trade proposals
   and outcomes, own resolved waiver claims, commissioner adjustments),
   with an unread count and a claim-gated mark-as-read action. The API
   enforces D6 (only the team's own resolved claims; no amounts on
   lost claims); this component just renders. */

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ApiError, type NotificationsOut } from "@/lib/types";
import { Bell } from "lucide-react";
import { cn } from "@/lib/utils";

export function NotificationsInbox({
  leagueId,
  myTeamId,
}: {
  leagueId: number;
  myTeamId: number | null;
}) {
  const [data, setData] = useState<NotificationsOut | null>(null);
  const [err, setErr] = useState("");

  const load = useCallback(async () => {
    if (myTeamId == null) return;
    try {
      setData(await api.getNotifications(leagueId, myTeamId));
      setErr("");
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "inbox load failed");
    }
  }, [leagueId, myTeamId]);

  useEffect(() => {
    load();
  }, [load]);

  async function markRead() {
    if (myTeamId == null) return;
    try {
      setData(await api.markNotificationsRead(leagueId, myTeamId));
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "mark-as-read failed");
    }
  }

  return (
    <section
      aria-label="For you"
      className="mb-5 rounded-xl border border-slate-800 bg-midnight-soft p-5"
    >
      <h2 className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-zinc-300">
        <Bell className="h-4 w-4 text-trophy-gold" /> For you
        {data && data.unread_count > 0 && (
          <span className="rounded-full bg-trophy-gold px-2 py-0.5 text-[11px] font-extrabold text-midnight">
            {data.unread_count} unread
          </span>
        )}
        {data && data.unread_count > 0 && (
          <button
            type="button"
            onClick={markRead}
            className="ml-auto rounded-md border border-slate-700 px-3 py-1.5 text-xs font-semibold normal-case tracking-normal text-zinc-300 transition hover:bg-slate-800"
          >
            Mark all read
          </button>
        )}
      </h2>

      {myTeamId == null ? (
        <p className="mt-4 text-sm text-zinc-500">
          Pick your team above to see trades, waiver results, and commissioner moves that touch it.
        </p>
      ) : err ? (
        <p className="mt-2 text-xs text-brick-red">{err}</p>
      ) : !data ? (
        <p className="mt-4 text-sm text-zinc-500">Loading your inbox…</p>
      ) : data.entries.length === 0 ? (
        <p className="mt-4 text-sm text-zinc-500">
          Nothing for you yet — trade proposals, waiver results, and commissioner moves for your team land here.
        </p>
      ) : (
        <ul className="mt-4 divide-y divide-slate-800/60">
          {data.entries.map((e) => (
            <li key={e.id} className="flex items-start gap-3 py-2.5">
              <span
                className={cn(
                  "mt-1.5 h-2 w-2 shrink-0 rounded-full",
                  e.read ? "bg-slate-700" : "bg-trophy-gold",
                )}
                aria-label={e.read ? "read" : "unread"}
              />
              <div className="min-w-0 flex-1">
                <p className={cn("text-sm", e.read ? "text-zinc-400" : "text-zinc-100")}>
                  {e.text}
                </p>
                <p className="mt-0.5 text-xs text-zinc-500">{e.occurred_at} UTC</p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
