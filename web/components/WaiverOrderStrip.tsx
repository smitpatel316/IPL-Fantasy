"use client";

/* P5-W47: the waiver-wire tiebreak order strip. The engine resolves
   tied bids by reverse standings (worst record wins); this renders the
   current order with the visitor's selected team highlighted so
   managers no longer bid blind. Read-only. */

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { WaiverOrderOut } from "@/lib/types";
import { cn } from "@/lib/utils";

function ordinal(n: number): string {
  const mod100 = n % 100;
  if (mod100 >= 11 && mod100 <= 13) return `${n}th`;
  switch (n % 10) {
    case 1: return `${n}st`;
    case 2: return `${n}nd`;
    case 3: return `${n}rd`;
    default: return `${n}th`;
  }
}

export function WaiverOrderStrip({
  leagueId,
  teamId,
}: {
  leagueId: number;
  teamId: number | null;
}) {
  const [order, setOrder] = useState<WaiverOrderOut | null>(null);

  useEffect(() => {
    api.waiverOrder(leagueId).then(setOrder).catch(() => setOrder(null));
  }, [leagueId]);

  if (!order || order.order.length === 0) return null;
  const mine = order.order.find((o) => o.team_id === teamId);

  return (
    <section
      aria-label="Waiver tiebreak order"
      className="mb-5 rounded-xl border hairline bg-midnight-soft px-4 py-3"
    >
      <p className="text-sm text-zinc-300">
        <strong className="font-semibold text-white">Waiver tiebreak order:</strong>{" "}
        {mine ? (
          <>
            your tiebreak position is{" "}
            <strong className="font-bold text-gold-400">
              {ordinal(mine.position)} of {order.order.length}
            </strong>
          </>
        ) : (
          <>position 1 wins tied bids</>
        )}
        <span className="text-zinc-500"> — {order.basis}</span>
      </p>
      <ol className="mt-2.5 flex flex-wrap gap-1.5">
        {order.order.map((o) => (
          <li
            key={o.team_id}
            className={cn(
              "rounded-full border px-2.5 py-1 text-xs font-semibold",
              o.team_id === teamId
                ? "border-gold-500/50 bg-gold-500/10 text-gold-300"
                : "hairline bg-white/[0.02] text-zinc-400"
            )}
            title={`${o.wins}–${o.losses}`}
          >
            {o.position}. {o.team_name} ({o.wins}–{o.losses})
          </li>
        ))}
      </ol>
    </section>
  );
}
