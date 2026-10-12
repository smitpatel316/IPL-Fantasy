"use client";

import { useEffect, useState } from "react";
import { PageHeader, ErrorBox } from "@/components/ui";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/types";
import type { PlayoffGameOut, PlayoffsOut } from "@/lib/types";
import { Trophy, Medal, Swords } from "lucide-react";
import { cn } from "@/lib/utils";

const STAGE_TEXT: Record<string, string> = {
  regular_season:
    "Regular season in progress — this bracket is a live projection from the current standings. Seeds lock in after week 6.",
  semifinals: "Regular season complete — seeds are final. The semifinals play in week 7.",
  final: "The semifinals are decided — the final and third-place game play in week 8.",
  complete: "The season is complete — the champion has been crowned.",
};

function TeamRow({
  chip,
  label,
  score,
  winner,
  decided,
}: {
  chip: string;
  label: string;
  score: number | null;
  winner?: boolean;
  decided?: boolean;
}) {
  return (
    <div
      className={cn(
        "flex items-center justify-between rounded-lg px-3 py-2.5 text-sm",
        winner
          ? "bg-trophy-gold/10 text-white"
          : "bg-slate-800/60 text-zinc-400",
        decided && !winner && "opacity-60",
      )}
    >
      <span className="flex items-center gap-2">
        <span
          className={cn(
            "flex h-6 min-w-6 items-center justify-center rounded-md px-1 text-[11px] font-extrabold",
            winner ? "bg-trophy-gold text-midnight" : "bg-slate-700 text-zinc-300",
          )}
        >
          {chip}
        </span>
        <span className={winner ? "font-semibold" : undefined}>{label}</span>
      </span>
      {score != null && (
        <span className="font-mono text-sm font-bold text-zinc-200">{score.toFixed(1)}</span>
      )}
    </div>
  );
}

function GameCard({
  game,
  icon,
  chipFor,
  projected,
}: {
  game: PlayoffGameOut;
  icon: React.ReactNode;
  chipFor: (teamId: number | null, fallback: string) => string;
  projected: boolean;
}) {
  const statusText =
    game.status === "final"
      ? `Final · Week ${game.week_no}`
      : projected
        ? `Projected · Week ${game.week_no}`
        : `Week ${game.week_no}`;
  return (
    <div className="rounded-xl border border-slate-800 bg-midnight-soft p-5">
      <h2 className="mb-1 flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-zinc-300">
        {icon} {game.label}
      </h2>
      <p className="mb-3 text-xs text-zinc-600">{statusText}</p>
      <div className="space-y-2">
        <TeamRow
          chip={chipFor(game.team_a_id, "A")}
          label={game.team_a_label}
          score={game.score_a}
          winner={game.winner_team_id != null && game.winner_team_id === game.team_a_id}
          decided={game.status === "final"}
        />
        <TeamRow
          chip={chipFor(game.team_b_id, "B")}
          label={game.team_b_label}
          score={game.score_b}
          winner={game.winner_team_id != null && game.winner_team_id === game.team_b_id}
          decided={game.status === "final"}
        />
      </div>
    </div>
  );
}

export default function PlayoffsPage() {
  const [data, setData] = useState<PlayoffsOut | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    api
      .getPlayoffs(1)
      .then(setData)
      .catch((e) => setErr(e instanceof ApiError ? e.message : "load failed"));
  }, []);

  const seedChip = (teamId: number | null, fallback: string) => {
    if (teamId == null || !data) return fallback;
    const s = data.seeds.find((x) => x.team_id === teamId);
    return s ? String(s.seed) : fallback;
  };

  return (
    <div>
      <PageHeader title="Playoffs" sub="Top 4 · fantasy weeks 7–8 · semifinals + final" />

      {err && (
        <div className="mb-4">
          <ErrorBox message={err} />
        </div>
      )}
      {!data && !err && <p className="text-sm text-zinc-500">Loading bracket…</p>}

      {data && (
        <>
          <p className="mb-5 rounded-lg border border-slate-800 bg-midnight-soft px-4 py-2.5 text-sm text-zinc-400">
            {STAGE_TEXT[data.stage] ?? ""}
          </p>

          {/* Seeds */}
          <div className="mb-6 rounded-xl border border-slate-800 bg-midnight-soft p-5">
            <h2 className="mb-3 text-sm font-bold uppercase tracking-wider text-zinc-300">
              Playoff seeds{" "}
              <span className="ml-1 font-medium normal-case tracking-normal text-zinc-500">
                {data.seeds_final ? "· final" : "· projected from current standings"}
              </span>
            </h2>
            {data.seeds.length === 0 ? (
              <p className="text-sm text-zinc-500">
                The bracket forms once the league has at least 4 teams.
              </p>
            ) : (
              <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
                {data.seeds.map((s) => (
                  <div
                    key={s.team_id}
                    className="flex items-center justify-between rounded-lg bg-slate-800/60 px-3 py-2.5 text-sm text-zinc-300"
                  >
                    <span className="flex items-center gap-2">
                      <span className="flex h-6 w-6 items-center justify-center rounded-md bg-slate-700 text-[11px] font-extrabold text-zinc-200">
                        {s.seed}
                      </span>
                      <span className="font-medium text-white">{s.team_name}</span>
                    </span>
                    <span className="text-xs text-zinc-500">
                      {s.wins}–{s.losses}
                      {s.ties > 0 ? `–${s.ties}` : ""} · {s.points_for.toFixed(1)} PF
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="grid items-start gap-4 lg:grid-cols-[1fr_auto_1fr]">
            {/* Semifinals */}
            <div className="space-y-4">
              {data.semifinals.map((g) => (
                <GameCard
                  key={g.label}
                  game={g}
                  icon={<Medal className="h-4 w-4 text-zinc-500" />}
                  chipFor={seedChip}
                  projected={!data.seeds_final}
                />
              ))}
              {data.semifinals.length === 0 && (
                <p className="text-sm text-zinc-500">
                  Semifinal pairings appear once four seeds are set.
                </p>
              )}
            </div>

            {/* Connector */}
            <div className="hidden items-center lg:flex" aria-hidden>
              <div className="flex flex-col items-center gap-1 text-zinc-700">
                <div className="h-16 w-px bg-slate-700" />
                <div className="h-px w-8 bg-slate-700" />
                <div className="h-16 w-px bg-slate-700" />
              </div>
            </div>

            {/* Final + third place + champion */}
            <div className="flex flex-col gap-4">
              {data.final && (
                <div className="rounded-xl border border-trophy-gold/30 bg-midnight-soft p-5">
                  <GameCardBody game={data.final} chipFor={seedChip} />
                </div>
              )}
              {data.third_place && (
                <GameCard
                  game={data.third_place}
                  icon={<Swords className="h-4 w-4 text-zinc-500" />}
                  chipFor={seedChip}
                  projected={data.third_place.status === "projected"}
                />
              )}
              <div className="rounded-xl border border-dashed border-trophy-gold/40 bg-trophy-gold/5 p-5 text-center">
                <Trophy className="mx-auto mb-2 h-8 w-8 text-trophy-gold" />
                <p className="text-sm font-bold text-trophy-gold">Champion</p>
                {data.champion_team_name ? (
                  <p className="mt-1 text-base font-bold text-white">
                    {data.champion_team_name}
                  </p>
                ) : (
                  <p className="mt-1 text-xs text-zinc-500">
                    Crowned after the week 8 final
                  </p>
                )}
              </div>
            </div>
          </div>
        </>
      )}

      <p className="mt-6 max-w-2xl text-xs leading-relaxed text-zinc-600">
        The fantasy season ends before the real IPL playoffs — the player pool shrinks to 4 teams,
        so fantasy playoffs finish while every IPL team is still alive (Yahoo's "end before dead
        rubbers" principle). A tied playoff game goes to the higher seed.
      </p>
    </div>
  );
}

/** The final gets the gold treatment, so it renders its rows inline
 *  instead of using the neutral GameCard shell. */
function GameCardBody({
  game,
  chipFor,
}: {
  game: PlayoffGameOut;
  chipFor: (teamId: number | null, fallback: string) => string;
}) {
  return (
    <>
      <h2 className="mb-1 flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-trophy-gold">
        <Trophy className="h-4 w-4" /> {game.label}
      </h2>
      <p className="mb-3 text-xs text-zinc-600">
        {game.status === "final" ? `Final · Week ${game.week_no}` : `Week ${game.week_no}`}
      </p>
      <div className="space-y-2">
        <TeamRow
          chip={chipFor(game.team_a_id, "W1")}
          label={game.team_a_label}
          score={game.score_a}
          winner={game.winner_team_id != null && game.winner_team_id === game.team_a_id}
          decided={game.status === "final"}
        />
        <TeamRow
          chip={chipFor(game.team_b_id, "W2")}
          label={game.team_b_label}
          score={game.score_b}
          winner={game.winner_team_id != null && game.winner_team_id === game.team_b_id}
          decided={game.status === "final"}
        />
      </div>
    </>
  );
}
