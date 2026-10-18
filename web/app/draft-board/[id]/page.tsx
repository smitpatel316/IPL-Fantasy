"use client";

/**
 * P5-W41: draft board grid (Yahoo/ESPN parity). Rounds as rows, teams as
 * columns in draft order, each cell the pick that team made that round.
 * Read-only: pulls draft + picks + player universe + team names.
 * Click a cell for the pick's draft context (pick #, ADP vs actual).
 */

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/types";
import type { DraftOut, DraftPickOut, PlayerOut, TeamOut } from "@/lib/types";
import { Card, ErrorBox, PageHeader } from "@/components/ui";

type Cell = { pick: DraftPickOut; player: PlayerOut | undefined };

export default function DraftBoardPage() {
  const params = useParams<{ id: string }>();
  const draftId = params.id;

  const [draft, setDraft] = useState<DraftOut | null>(null);
  const [picks, setPicks] = useState<DraftPickOut[]>([]);
  const [players, setPlayers] = useState<PlayerOut[]>([]);
  const [teams, setTeams] = useState<TeamOut[]>([]);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<{ round: number; teamId: number } | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setErr("");
    (async () => {
      try {
        const d = await api.getDraft(draftId);
        const [pk, pl, tm] = await Promise.all([
          api.listPicks(draftId),
          api.listPlayers({ league_id: d.league_id }),
          api.listTeams(d.league_id),
        ]);
        if (cancelled) return;
        setDraft(d);
        setPicks(pk);
        setPlayers(pl);
        setTeams(tm);
      } catch (e) {
        if (!cancelled) setErr(e instanceof ApiError ? e.message : "load failed");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [draftId]);

  const playerById = useMemo(() => new Map(players.map((p) => [p.id, p])), [players]);
  const teamById = useMemo(() => new Map(teams.map((t) => [t.id, t])), [teams]);

  // Columns = teams in round-1 draft order. cellMap[(round, team)] -> pick.
  const columns = useMemo(() => draft?.draft_order ?? [], [draft]);
  const cellMap = useMemo(() => {
    const m = new Map<string, Cell>();
    for (const pick of picks) {
      m.set(`${pick.round_no}:${pick.team_id}`, {
        pick,
        player: pick.player_id != null ? playerById.get(pick.player_id) : undefined,
      });
    }
    return m;
  }, [picks, playerById]);

  const rounds = useMemo(() => {
    const n = draft?.rounds ?? 0;
    return Array.from({ length: n }, (_, i) => i + 1);
  }, [draft]);

  const selCell = selected ? cellMap.get(`${selected.round}:${selected.teamId}`) : undefined;
  const selTeam = selected ? teamById.get(selected.teamId) : undefined;

  return (
    <div>
      <PageHeader
        title="Draft board"
        sub={
          draft
            ? `League ${draft.league_id} · ${draft.status} · ${rounds.length} rounds, ${columns.length} teams — snake order`
            : "Every pick, every round — click a cell for draft context"
        }
      />
      {err && (
        <div className="mb-4">
          <ErrorBox message={err} />
        </div>
      )}
      {loading && <p className="text-sm text-zinc-500">Loading…</p>}
      {!loading && draft && columns.length > 0 && (
        <>
          <Card className="mb-4 overflow-x-auto p-0">
            <table className="min-w-full border-collapse text-sm" data-testid="draft-board">
              <thead>
                <tr className="border-b hairline">
                  <th className="sticky left-0 z-10 w-12 bg-midnight-soft px-2 py-2 text-xs font-bold uppercase tracking-wider text-zinc-500">
                    Rd
                  </th>
                  {columns.map((teamId, i) => (
                    <th
                      key={teamId}
                      className="min-w-36 whitespace-nowrap border-l hairline px-2 py-2 text-left text-xs font-bold text-zinc-200"
                    >
                      <span className="mr-1 text-zinc-500">#{i + 1}</span>
                      {teamById.get(teamId)?.name ?? `Team ${teamId}`}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rounds.map((round) => (
                  <tr key={round} className="border-b hairline last:border-0">
                    <td className="sticky left-0 z-10 bg-midnight-soft px-2 py-1.5 text-center text-xs font-bold text-zinc-500">
                      {round}
                    </td>
                    {columns.map((teamId) => {
                      const cell = cellMap.get(`${round}:${teamId}`);
                      const p = cell?.player;
                      const isSel = selected?.round === round && selected?.teamId === teamId;
                      return (
                        <td
                          key={teamId}
                          className="border-l hairline px-1.5 py-1"
                        >
                          <button
                            type="button"
                            onClick={() => setSelected({ round, teamId })}
                            data-testid={`cell-${round}-${teamId}`}
                            className={`block w-full rounded-lg px-2 py-1.5 text-left transition-colors ${
                              isSel
                                ? "bg-trophy-gold/15 ring-1 ring-trophy-gold/60"
                                : "hover:bg-white/5"
                            }`}
                          >
                            {cell && p ? (
                              <>
                                <div className="truncate text-[13px] font-medium text-white">
                                  {p.name}
                                </div>
                                <div className="mt-0.5 flex items-center gap-1.5 text-[11px] text-zinc-500">
                                  <span className="font-semibold text-zinc-400">{p.role ?? "—"}</span>
                                  {p.ipl_team_code && (
                                    <span className="rounded bg-white/10 px-1 font-bold text-zinc-300">
                                      {p.ipl_team_code}
                                    </span>
                                  )}
                                  <span className="ml-auto text-zinc-600">#{cell.pick.pick_no}</span>
                                </div>
                              </>
                            ) : (
                              <div className="py-2 text-center text-[11px] text-zinc-600">—</div>
                            )}
                          </button>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>

          {/* Pick context panel */}
          {selected && selCell && (
            <div data-testid="pick-context">
            <Card className="mb-4">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="eyebrow mb-1">
                    Round {selected.round} · {selTeam?.name ?? `Team ${selected.teamId}`}
                  </p>
                  {selCell.player ? (
                    <>
                      <h2 className="text-xl font-extrabold text-white">{selCell.player.name}</h2>
                      <p className="mt-1 text-sm text-zinc-400">
                        {selCell.player.role ?? "—"}
                        {selCell.player.ipl_team_code ? ` · ${selCell.player.ipl_team_code}` : ""}
                        {selCell.pick.is_auto ? " · auto-pick" : ""}
                      </p>
                    </>
                  ) : (
                    <h2 className="text-xl font-extrabold text-white">Pick not made yet</h2>
                  )}
                </div>
                <dl className="grid grid-cols-3 gap-x-8 gap-y-2 text-sm">
                  <div>
                    <dt className="text-xs text-zinc-500">Overall pick</dt>
                    <dd className="text-lg font-bold text-white">#{selCell.pick.pick_no}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-zinc-500">ADP (consensus)</dt>
                    <dd className="text-lg font-bold text-white">
                      {selCell.player?.preseason_rank != null ? `#${selCell.player.preseason_rank}` : "—"}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs text-zinc-500">Reach / value</dt>
                    <dd className="text-lg font-bold text-white">
                      {selCell.player?.preseason_rank != null
                        ? selCell.player.preseason_rank - selCell.pick.pick_no > 0
                          ? `+${selCell.player.preseason_rank - selCell.pick.pick_no} value`
                          : selCell.player.preseason_rank - selCell.pick.pick_no < 0
                            ? `${selCell.player.preseason_rank - selCell.pick.pick_no} reach`
                            : "at ADP"
                        : "—"}
                    </dd>
                  </div>
                </dl>
              </div>
            </Card>
            </div>
          )}
        </>
      )}
      {!loading && draft && columns.length === 0 && (
        <p className="rounded-xl border hairline bg-midnight-soft p-8 text-center text-sm text-zinc-500">
          No draft order yet — the board fills in once the draft starts.
        </p>
      )}
    </div>
  );
}
