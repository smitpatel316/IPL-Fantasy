"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, draftWsUrl } from "@/lib/api";
import { ApiError, type DraftRoomState, type LeagueDetailOut, type PlayerOut } from "@/lib/types";
import { PageHeader, ErrorBox } from "@/components/ui";

type FeedItem = { key: string; text: string; auto?: boolean };

function fmtClock(secs: number): string {
  const s = Math.max(0, Math.ceil(secs));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

export default function DraftRoomPage({ params }: { params: Promise<{ id: string }> }) {
  const [leagueId, setLeagueId] = useState<string | null>(null);
  const [league, setLeague] = useState<LeagueDetailOut | null>(null);
  const [draftId, setDraftId] = useState<number | null>(null);
  const [myTeamId, setMyTeamId] = useState<number | null>(null);
  const [snap, setSnap] = useState<DraftRoomState | null>(null);
  const [board, setBoard] = useState<PlayerOut[]>([]);
  const [feed, setFeed] = useState<FeedItem[]>([]);
  const [err, setErr] = useState("");
  const [starting, setStarting] = useState(false);
  const [connected, setConnected] = useState(false);
  const [now, setNow] = useState(() => Date.now());
  const wsRef = useRef<WebSocket | null>(null);
  const feedKey = useRef(0);

  useEffect(() => {
    params.then((p) => setLeagueId(p.id));
  }, [params]);

  // Load league + existing draft + board.
  useEffect(() => {
    if (!leagueId) return;
    api.getLeague(leagueId).then(setLeague).catch((e) => setErr(e instanceof ApiError ? e.message : "league load failed"));
    api.getLeagueDraft(leagueId).then((d) => setDraftId(d ? d.id : null)).catch(() => {});
    api.listPlayers({ league_id: Number(leagueId) }).then(setBoard).catch(() => {});
    const saved = localStorage.getItem(`ipl-draft-team-${leagueId}`);
    if (saved) setMyTeamId(Number(saved));
  }, [leagueId]);

  const teams = useMemo(() => league?.standings.map((s) => ({ id: s.team_id, name: s.team_name })) ?? [], [league]);

  useEffect(() => {
    if (!myTeamId && teams.length > 0) setMyTeamId(teams[0].id);
  }, [teams, myTeamId]);

  useEffect(() => {
    if (leagueId && myTeamId) localStorage.setItem(`ipl-draft-team-${leagueId}`, String(myTeamId));
  }, [leagueId, myTeamId]);

  const playerById = useMemo(() => {
    const m = new Map<number, PlayerOut>();
    for (const p of board) m.set(p.id, p);
    return m;
  }, [board]);

  const pushFeed = useCallback((text: string, auto?: boolean) => {
    const key = `f${feedKey.current++}`;
    setFeed((f) => [{ key, text, auto }, ...f].slice(0, 40));
  }, []);

  // WebSocket room.
  useEffect(() => {
    if (!draftId || !myTeamId) return;
    let closed = false;
    let retry: ReturnType<typeof setTimeout> | null = null;
    const connect = () => {
      const ws = new WebSocket(draftWsUrl(draftId, myTeamId));
      wsRef.current = ws;
      ws.onopen = () => setConnected(true);
      ws.onclose = () => {
        setConnected(false);
        wsRef.current = null;
        if (!closed) retry = setTimeout(connect, 2000);
      };
      ws.onerror = () => ws.close();
      ws.onmessage = (ev) => {
        let msg: Record<string, unknown>;
        try {
          msg = JSON.parse(ev.data as string);
        } catch {
          return;
        }
        if (msg.type === "state") {
          const st = msg as unknown as DraftRoomState;
          setSnap(st);
          const pick = st.pick;
          if (st.event === "pick" && pick) {
            const nm = playerById.get(pick.player_id ?? -1)?.name ?? `#${pick.player_id}`;
            const tm = st.draft.teams.find((t) => t.id === pick.team_id)?.name ?? `team ${pick.team_id}`;
            pushFeed(`Pick ${pick.pick_no} (R${pick.round_no}): ${tm} drafted ${nm}`, pick.is_auto);
          } else if (st.event === "clock_expired" && pick) {
            const nm = playerById.get(pick.player_id ?? -1)?.name ?? `#${pick.player_id}`;
            const tm = st.draft.teams.find((t) => t.id === pick.team_id)?.name ?? `team ${pick.team_id}`;
            pushFeed(`Clock expired — ${tm} auto-picked ${nm}`, true);
          } else if (st.event === "dnd_updated" && st.dnd_updated) {
            const tm = st.draft.teams.find((t) => t.id === st.dnd_updated!.team_id)?.name ?? "a team";
            pushFeed(`${tm} updated their do-not-draft list`);
          }
        } else if (msg.type === "error") {
          setErr(String(msg.detail ?? "draft room error"));
        }
      };
    };
    connect();
    return () => {
      closed = true;
      if (retry) clearTimeout(retry);
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [draftId, myTeamId, playerById, pushFeed]);

  // Countdown ticker.
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);

  async function start() {
    if (!leagueId) return;
    setStarting(true);
    setErr("");
    try {
      const d = await api.startDraft(leagueId);
      setDraftId(d.id);
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "start failed");
    } finally {
      setStarting(false);
    }
  }

  function send(msg: object) {
    wsRef.current?.send(JSON.stringify(msg));
  }

  const drafted = useMemo(() => {
    const s = new Set<number>();
    for (const p of snap?.picks ?? []) if (p.player_id != null) s.add(p.player_id);
    return s;
  }, [snap]);

  const available = useMemo(
    () => board.filter((p) => !drafted.has(p.id)).sort((a, b) => (a.preseason_rank ?? 1e9) - (b.preseason_rank ?? 1e9)),
    [board, drafted],
  );

  const myDnd = useMemo(
    () => new Set((myTeamId != null && snap?.dnd[String(myTeamId)]) || []),
    [snap, myTeamId],
  );

  const myRoster = myTeamId != null ? snap?.rosters[String(myTeamId)] : undefined;
  const onClock = snap?.on_clock_team_id;
  const myTurn = snap?.draft.status === "live" && onClock === myTeamId;
  const deadline = snap?.pick_deadline;
  const clockLeft = deadline != null ? deadline - now / 1000 : null;
  const complete = snap?.draft.status === "complete";

  return (
    <div>
      <PageHeader title="Draft room" sub="Live snake draft · pick clock with auto-pick (D2)" />
      {err && <div className="mb-4"><ErrorBox message={err} /></div>}

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <label className="text-sm text-slate-400">
          Drafting as{" "}
          <select
            value={myTeamId ?? ""}
            onChange={(e) => setMyTeamId(Number(e.target.value))}
            className="rounded-md border border-slate-700 bg-midnight-soft px-2 py-1 text-sm text-white"
          >
            {teams.map((t) => (
              <option key={t.id} value={t.id}>{t.name}</option>
            ))}
          </select>
        </label>
        <span className={`text-xs ${connected ? "text-emerald-400" : "text-slate-500"}`}>
          {draftId ? (connected ? "● live" : "○ connecting…") : "no draft yet"}
        </span>
      </div>

      {!draftId ? (
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
      ) : !snap ? (
        <p className="text-sm text-slate-500">Joining draft room…</p>
      ) : (
        <div className="space-y-6">
          {complete ? (
            <div className="rounded-xl border border-emerald-800 bg-emerald-950/40 p-4 text-center">
              <p className="font-semibold text-emerald-300">Draft complete — all {snap.total_picks} picks made.</p>
              <p className="mt-1 text-sm text-slate-400">Week-1 lineups are set (best available XI); adjust them before the weekly lock.</p>
            </div>
          ) : (
            <div className="flex items-center justify-between rounded-xl border border-slate-800 bg-midnight-soft px-4 py-3">
              <div>
                <p className="text-sm text-slate-400">
                  Round {snap.picks.length > 0 ? snap.picks[snap.picks.length - 1].round_no : 1} of {snap.draft.rounds}
                  {" · "}Pick {snap.current_pick_no} of {snap.total_picks}
                </p>
                <p className="font-semibold text-white">
                  On the clock: {snap.draft.teams.find((t) => t.id === onClock)?.name ?? "—"}
                  {myTurn && <span className="ml-2 text-trophy-gold">— your pick!</span>}
                </p>
              </div>
              <div className={`font-mono text-2xl ${clockLeft != null && clockLeft < 15 ? "text-red-400" : "text-white"}`}>
                {clockLeft != null ? fmtClock(clockLeft) : "—"}
              </div>
            </div>
          )}

          <div className="grid gap-6 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <h2 className="mb-2 font-semibold text-white">Available players</h2>
              <div className="max-h-[480px] space-y-1 overflow-y-auto pr-1">
                {available.slice(0, 60).map((p) => (
                  <div key={p.id} className="flex items-center justify-between rounded-md border border-slate-800/60 px-3 py-1.5 text-sm">
                    <span className="w-10 text-slate-500">#{p.preseason_rank ?? "–"}</span>
                    <span className="flex-1 px-2 text-white">{p.name}</span>
                    <span className="text-xs text-slate-500">{p.role} · {p.ipl_team_code}{p.is_overseas ? " ✈" : ""}</span>
                    <button
                      onClick={() => send({ type: "pick", player_id: p.id })}
                      disabled={!myTurn}
                      className="ml-2 rounded bg-trophy-gold px-2 py-0.5 text-xs font-semibold text-midnight disabled:opacity-30"
                    >
                      Draft
                    </button>
                    <button
                      onClick={() => send({ type: myDnd.has(p.id) ? "dnd_remove" : "dnd_add", player_id: p.id })}
                      title={myDnd.has(p.id) ? "Remove from do-not-draft" : "Add to do-not-draft"}
                      className={`ml-1 rounded px-2 py-0.5 text-xs ${myDnd.has(p.id) ? "bg-red-900 text-red-200" : "border border-slate-700 text-slate-400"}`}
                    >
                      {myDnd.has(p.id) ? "DND ✕" : "DND"}
                    </button>
                  </div>
                ))}
              </div>
            </div>

            <div className="space-y-6">
              <div>
                <h2 className="mb-2 font-semibold text-white">My roster</h2>
                {!myRoster || Object.keys(myRoster).length === 0 ? (
                  <p className="text-sm text-slate-500">No picks yet.</p>
                ) : (
                  <div className="space-y-1">
                    {Object.entries(myRoster).map(([slot, pids]) => (
                      <div key={slot} className="text-sm">
                        <span className="mr-2 font-mono text-xs text-slate-500">{slot}</span>
                        {pids.map((pid) => (
                          <span key={pid} className="mr-1 rounded bg-slate-800 px-1.5 py-0.5 text-xs text-white">
                            {playerById.get(pid)?.name ?? `#${pid}`}
                          </span>
                        ))}
                      </div>
                    ))}
                  </div>
                )}
                {myDnd.size > 0 && (
                  <p className="mt-2 text-xs text-slate-500">Do-not-draft: {myDnd.size} player{myDnd.size === 1 ? "" : "s"}</p>
                )}
              </div>

              <div>
                <h2 className="mb-2 font-semibold text-white">Pick feed</h2>
                <div className="max-h-[300px] space-y-1 overflow-y-auto text-sm">
                  {feed.length === 0 && <p className="text-xs text-slate-600">Picks will appear here live.</p>}
                  {feed.map((f) => (
                    <p key={f.key} className="text-slate-300">
                      {f.auto && <span className="mr-1 rounded bg-slate-700 px-1 text-[10px] text-slate-300">AUTO</span>}
                      {f.text}
                    </p>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
