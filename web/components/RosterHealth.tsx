"use client";

/* P5-W21: roster-health / IL assistant — read-only lists for the
   selected team: move-to-IL candidates, IL return candidates, and
   retired flags, all from the curated registry (P5-W6 basis). The
   move itself still happens in the lineup editor above via the
   normal validated save — this section never auto-moves anyone. */

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ApiError, type RosterHealthOut, type RosterHealthPlayerOut } from "@/lib/types";
import { HeartPulse } from "lucide-react";

function Group({
  title,
  players,
  emptyNote,
}: {
  title: string;
  players: RosterHealthPlayerOut[];
  emptyNote?: string;
}) {
  if (players.length === 0)
    return emptyNote ? (
      <p className="text-xs text-zinc-500">
        {title}: {emptyNote}
      </p>
    ) : null;
  return (
    <div>
      <p className="text-xs font-bold uppercase tracking-wide text-zinc-400">{title}</p>
      <ul className="mt-1 space-y-1">
        {players.map((p) => (
          <li key={p.player_id} className="text-sm text-zinc-200">
            {p.player_name}
            <span className="text-zinc-500">
              {" "}
              · {p.role ?? "—"} · {p.slot} · {p.status}
              {p.note ? ` — ${p.note.toLowerCase()}` : ""}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function RosterHealth({
  leagueId,
  teamId,
}: {
  leagueId: number;
  teamId: number | null;
}) {
  const [data, setData] = useState<RosterHealthOut | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (teamId == null) return;
    api
      .getRosterHealth(leagueId, teamId)
      .then(setData)
      .catch((e) => setErr(e instanceof ApiError ? e.message : "roster health load failed"));
  }, [leagueId, teamId]);

  if (teamId == null) return null;
  const healthy =
    data &&
    data.move_to_il.length === 0 &&
    data.return_candidates.length === 0 &&
    data.retired.length === 0;

  return (
    <section
      aria-label="Roster health"
      className="mb-5 rounded-xl border border-slate-800 bg-midnight-soft p-5"
    >
      <h2 className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-zinc-300">
        <HeartPulse className="h-4 w-4 text-trophy-gold" /> Roster health
      </h2>
      {err && <p className="mt-2 text-xs text-brick-red">{err}</p>}
      {!data && !err && <p className="mt-3 text-sm text-zinc-500">Checking your roster…</p>}
      {data && healthy && (
        <p className="mt-3 text-sm text-zinc-500">
          Roster is healthy — no IL moves, returns, or retired flags right now.
        </p>
      )}
      {data && !healthy && (
        <div className="mt-3 space-y-3">
          <Group title="Move to IL" players={data.move_to_il} />
          <Group title="Ready to return from IL" players={data.return_candidates} />
          <Group title="Retired" players={data.retired} />
        </div>
      )}
      {data && (
        <p className="mt-3 text-xs text-zinc-600">
          {data.basis}. Moves happen in the lineup editor above — saving still runs the usual
          lock, IL-eligibility, and overseas-cap checks.
        </p>
      )}
    </section>
  );
}
