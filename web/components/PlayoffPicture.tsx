"use client";

/* P5-W22: playoff picture + remaining strength of schedule —
   descriptive only: current record, games back from the 4th seed,
   and who is left to play. No projections or win probabilities.
   P5-W34: clinch status + magic number are deterministic bounds
   arithmetic on standings points (see api/routers/playoff_picture.py)
   — a tied bound never clinches or eliminates. */

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ApiError, type PlayoffPictureOut } from "@/lib/types";
import { Flag } from "lucide-react";
import { cn } from "@/lib/utils";

export function PlayoffPicture({ leagueId }: { leagueId: number }) {
  const [data, setData] = useState<PlayoffPictureOut | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    api
      .getPlayoffPicture(leagueId)
      .then(setData)
      .catch((e) => setErr(e instanceof ApiError ? e.message : "playoff picture load failed"));
  }, [leagueId]);

  if (err)
    return (
      <section className="mb-6 rounded-xl border border-slate-800 bg-midnight-soft p-5">
        <p className="text-xs text-loss-ink">{err}</p>
      </section>
    );
  if (!data) return null;

  return (
    <section
      aria-label="Playoff picture"
      className="mb-6 rounded-xl border border-slate-800 bg-midnight-soft p-5"
    >
      <h2 className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-zinc-300">
        <Flag className="h-4 w-4 text-gold-ink" /> Playoff picture
        <span className="text-[11px] font-medium normal-case tracking-normal text-zinc-500">
          {data.regular_season_complete
            ? "regular season complete — the final picture"
            : `through week ${data.through_week} · current record + remaining fixtures only, no projections`}
        </span>
      </h2>
      <div className="mt-3 overflow-x-auto">
        <table className="w-full min-w-[560px] text-sm">
          <thead>
            <tr className="text-left text-[11px] uppercase tracking-wide text-zinc-500">
              <th className="py-1 pr-2">Seed</th>
              <th className="py-1 pr-2">Team</th>
              <th className="py-1 pr-2">Record</th>
              <th className="py-1 pr-2">GB from 4th</th>
              <th className="py-1 pr-2">Left</th>
              <th className="py-1 pr-2">Status</th>
              <th className="py-1 pr-2">Magic no.</th>
              <th className="py-1 pr-2">Remaining opponents</th>
              <th className="py-1">Rem. SOS</th>
            </tr>
          </thead>
          <tbody>
            {data.entries.map((e) => (
              <tr
                key={e.team_id}
                className={cn(
                  "border-t border-slate-800/60",
                  e.seed === 4 && "border-b-2 border-b-trophy-gold/50",
                )}
              >
                <td className="py-2 pr-2 font-bold text-zinc-300">{e.seed}</td>
                <td className="py-2 pr-2 font-medium text-white">{e.team_name}</td>
                <td className="py-2 pr-2 text-zinc-400">
                  {e.wins}–{e.losses}
                  {e.ties > 0 ? `–${e.ties}` : ""}
                </td>
                <td className="py-2 pr-2 text-zinc-400">
                  {e.games_back == null
                    ? "—"
                    : e.games_back <= 0
                      ? e.games_back === 0
                        ? "—"
                        : `${Math.abs(e.games_back)} up`
                      : e.games_back.toFixed(1)}
                </td>
                <td className="py-2 pr-2 text-zinc-400">{e.remaining_games}</td>
                <td className="py-2 pr-2">
                  {e.clinch_status === "clinched" ? (
                    <span className="rounded bg-pitch-green/15 px-1.5 py-0.5 text-[11px] font-bold uppercase text-win-ink">
                      Clinched
                    </span>
                  ) : e.clinch_status === "eliminated" ? (
                    <span className="rounded bg-brick-red/15 px-1.5 py-0.5 text-[11px] font-bold uppercase text-loss-ink">
                      Eliminated
                    </span>
                  ) : (
                    <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[11px] font-bold uppercase text-zinc-400">
                      In contention
                    </span>
                  )}
                </td>
                <td className="py-2 pr-2 tabular-nums text-zinc-400">
                  {e.clinch_status === "in_contention"
                    ? e.magic_number != null
                      ? e.magic_number
                      : "—"
                    : "—"}
                </td>
                <td className="py-2 pr-2 text-zinc-400">
                  {e.remaining_opponents.length === 0
                    ? "—"
                    : e.remaining_opponents
                        .map((o) => `${o.opponent_team_name} (w${o.week_no})`)
                        .join(", ")}
                </td>
                <td className="py-2 text-zinc-400">
                  {e.remaining_games === 0 ? "—" : e.remaining_sos.toFixed(4)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-2 text-xs text-zinc-600">
        Remaining SOS is the average standings-points share (2 pts per win, 1 per tie) of the
        opponents still to play — a description of the run-in, not a prediction.
      </p>
      <p className="mt-1 text-xs text-zinc-600">
        Clinch status and the magic number (standings points needed to guarantee a top-4
        finish) are bounds arithmetic only — best/worst-case standings points, with tied
        bounds always resolving to “in contention”. No win probability, no simulation.
      </p>
    </section>
  );
}
