"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ApiError, type DraftOut, type DraftPickOut, type PlayerOut } from "@/lib/types";
import { PageHeader, ErrorBox, EngineStub } from "@/components/ui";

export default function DraftRoomPage({ params }: { params: Promise<{ id: string }> }) {
  const [leagueId, setLeagueId] = useState<string | null>(null);
  const [draft, setDraft] = useState<DraftOut | null>(null);
  const [picks, setPicks] = useState<DraftPickOut[]>([]);
  const [board, setBoard] = useState<PlayerOut[]>([]);
  const [err, setErr] = useState("");
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    params.then((p) => setLeagueId(p.id));
  }, [params]);

  useEffect(() => {
    if (!leagueId) return;
    api.listPlayers({ league_id: Number(leagueId) }).then(setBoard).catch(() => {});
  }, [leagueId]);

  async function start() {
    if (!leagueId) return;
    setStarting(true);
    setErr("");
    try {
      await api.startDraft(leagueId);
    } catch (e) {
      if (e instanceof ApiError && e.status === 501) {
        setErr(`Draft engine not wired yet (${e.track}).`);
      } else {
        setErr(e instanceof ApiError ? e.message : "start failed");
      }
    } finally {
      setStarting(false);
    }
  }

  return (
    <div>
      <PageHeader title="Draft room" sub="Snake draft · 15 rounds · pick clock with auto-pick (D2)" />
      {err && <div className="mb-4"><ErrorBox message={err} /></div>}

      {!draft ? (
        <div className="space-y-4">
          <div className="rounded-xl border border-slate-800 bg-midnight-soft p-6 text-center">
            <p className="text-sm text-slate-400">No draft started for this league yet.</p>
            <button
              onClick={start}
              disabled={starting}
              className="mt-3 rounded-md bg-trophy-gold px-5 py-2 text-sm font-semibold text-midnight hover:brightness-110 disabled:opacity-50"
            >
              {starting ? "Starting…" : "Start draft"}
            </button>
          </div>
          <EngineStub track="P2-L1" what="Draft engine (serpentine order, clock, auto-pick, WebSocket room)" />
        </div>
      ) : (
        <p className="text-sm text-slate-400">Draft #{draft.id} — {draft.status}</p>
      )}

      <h2 className="mb-2 mt-8 font-semibold text-white">Draft board (preseason ranks)</h2>
      <div className="grid gap-1 sm:grid-cols-2 lg:grid-cols-3">
        {board.slice(0, 30).map((p) => (
          <div key={p.id} className="flex items-center justify-between rounded-md border border-slate-800/60 px-3 py-1.5 text-sm">
            <span className="text-slate-500">#{p.preseason_rank}</span>
            <span className="flex-1 px-2 text-white">{p.name}</span>
            <span className="text-xs text-slate-500">{p.role} · {p.ipl_team_code}{p.is_overseas ? " ✈" : ""}</span>
          </div>
        ))}
      </div>
      {picks.length > 0 && (
        <p className="mt-4 text-xs text-slate-600">{picks.length} picks made</p>
      )}
    </div>
  );
}
