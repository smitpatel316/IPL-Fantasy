"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, draftWsUrl } from "@/lib/api";
import { useLeague } from "@/lib/league-context";
import { ApiError, type ChatMessage, type DraftRoomState, type LeagueDetailOut, type PlayerOut } from "@/lib/types";
import { PageHeader, ErrorBox } from "@/components/ui";
import { DraftClock } from "@/components/DraftClock";
import { DraftAlertControls } from "@/components/DraftAlertControls";
import { DraftPlayerCard } from "@/components/DraftPlayerCard";
import {
  ScheduleWeekPicker,
  useScheduleBadges,
} from "@/components/ScheduleBadges";
import { DraftRoster } from "@/components/DraftRoster";
import { DraftFeed, type DraftFeedItem } from "@/components/DraftFeed";
import styles from "../draft-room.module.css";

const ROLE_FILTERS = ["ALL", "WK", "BAT", "AR", "BOWL"] as const;
const TABS = [
  { id: "board", label: "Players" },
  { id: "roster", label: "My team" },
  { id: "feed", label: "Feed" },
  { id: "ranks", label: "My ranks" },
  { id: "chat", label: "Chat" },
] as const;
type TabId = (typeof TABS)[number]["id"];

/** Next `n` teams to pick, following the snake order. Derived from existing state only. */
function upcomingTeams(snap: DraftRoomState, n: number): number[] {
  const full: number[] = [];
  for (let r = 1; r <= snap.draft.rounds; r++) {
    const order = r % 2 === 1 ? snap.draft.draft_order : [...snap.draft.draft_order].reverse();
    full.push(...order);
  }
  return full.slice(snap.current_pick_no - 1, snap.current_pick_no - 1 + n);
}

export default function DraftRoomPage({ params }: { params: Promise<{ id: string }> }) {
  const [leagueId, setLeagueId] = useState<string | null>(null);
  const [league, setLeague] = useState<LeagueDetailOut | null>(null);
  const [draftId, setDraftId] = useState<number | null>(null);
  const [myTeamId, setMyTeamId] = useState<number | null>(null);
  const [snap, setSnap] = useState<DraftRoomState | null>(null);
  const [board, setBoard] = useState<PlayerOut[]>([]);
  const [feed, setFeed] = useState<DraftFeedItem[]>([]);
  const [rankOrder, setRankOrder] = useState<number[]>([]);
  const [ranksMsg, setRanksMsg] = useState("");
  const [ranksSaving, setRanksSaving] = useState(false);
  const [err, setErr] = useState("");
  const [starting, setStarting] = useState(false);
  const [connected, setConnected] = useState(false);
  const [now, setNow] = useState(() => Date.now());
  const [tab, setTab] = useState<TabId>("board");
  const [query, setQuery] = useState("");
  const [roleFilter, setRoleFilter] = useState<(typeof ROLE_FILTERS)[number]>("ALL");
  const wsRef = useRef<WebSocket | null>(null);
  const feedKey = useRef(0);
  const { setLeagueId: setCurrentLeague } = useLeague();
  const backfilledDraft = useRef<number | null>(null);
  // P4-W20: room chat (history from state snapshots, live frames appended).
  const [chat, setChat] = useState<ChatMessage[]>([]);
  const [chatText, setChatText] = useState("");

  // P3-A6: schedule-aware nudges — games per IPL team for the chosen week.
  const sched = useScheduleBadges(leagueId ?? "", 1);

  useEffect(() => {
    params.then((p) => {
      setLeagueId(p.id);
      // Viewing a league's draft room makes it the current league (P4-W7).
      const n = Number(p.id);
      if (Number.isFinite(n) && n > 0) setCurrentLeague(n);
    });
  }, [params, setCurrentLeague]);

  // Load league + existing draft + board.
  useEffect(() => {
    if (!leagueId) return;
    api.getLeague(leagueId).then(setLeague).catch((e) => setErr(e instanceof ApiError ? e.message : "league load failed"));
    api.getLeagueDraft(leagueId).then((d) => setDraftId(d ? d.id : null)).catch(() => {});
    api.listPlayers({ league_id: Number(leagueId) }).then(setBoard).catch(() => {});
    const saved = localStorage.getItem(`ipl-draft-team-${leagueId}`);
    if (saved) setMyTeamId(Number(saved));
  }, [leagueId]);

  // Custom ranks (P4-W17): seed the editor from the team's saved ranks,
  // falling back to the board's preseason order; any board players not
  // yet ranked append in board order.
  useEffect(() => {
    if (!myTeamId || board.length === 0) return;
    let live = true;
    api
      .getRanks(myTeamId)
      .then((r) => {
        if (!live) return;
        const boardOrder = [...board]
          .sort((a, b) => (a.preseason_rank ?? 1e9) - (b.preseason_rank ?? 1e9))
          .map((p) => p.id);
        const custom = r.player_ids.filter((id) => boardOrder.includes(id));
        const rest = boardOrder.filter((id) => !custom.includes(id));
        setRankOrder([...custom, ...rest]);
      })
      .catch(() => {});
    return () => {
      live = false;
    };
  }, [myTeamId, board]);

  // P5-W17: private-note indicators on the board for my team. A 403
  // (claimed team, not ours) just means no indicators — never data.
  const [notedIds, setNotedIds] = useState<Set<number>>(new Set());
  useEffect(() => {
    if (!myTeamId || !leagueId) return;
    let live = true;
    api
      .listPlayerNotes(Number(leagueId), myTeamId)
      .then((notes) => live && setNotedIds(new Set(notes.map((n) => n.player_id))))
      .catch(() => live && setNotedIds(new Set()));
    return () => {
      live = false;
    };
  }, [leagueId, myTeamId]);

  function moveRank(idx: number, dir: -1 | 1) {
    setRanksMsg("");
    setRankOrder((prev) => {
      const next = [...prev];
      const j = idx + dir;
      if (j < 0 || j >= next.length) return prev;
      [next[idx], next[j]] = [next[j], next[idx]];
      return next;
    });
  }

  async function saveRanks() {
    if (!myTeamId) return;
    setRanksSaving(true);
    setRanksMsg("");
    try {
      await api.setRanks(myTeamId, rankOrder);
      setRanksMsg("Ranks saved — auto-pick follows this order.");
    } catch (e) {
      setRanksMsg(e instanceof ApiError ? e.message : "ranks save failed");
    } finally {
      setRanksSaving(false);
    }
  }

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
          // Backfill the pick history once per draft (P4-W12): without
          // this, joining mid-draft or refreshing shows an empty feed —
          // the snapshot carries every pick made so far. The current
          // message's own pick event (if any) is excluded here; it is
          // pushed by the event handling below.
          if (backfilledDraft.current !== st.draft.id) {
            backfilledDraft.current = st.draft.id;
            const eventPickNo = st.pick?.pick_no ?? Number.POSITIVE_INFINITY;
            const history = (st.picks ?? [])
              .filter((p) => p.player_id != null && p.pick_no < eventPickNo)
              .sort((a, b) => b.pick_no - a.pick_no)
              .slice(0, 40)
              .map((p) => {
                const nm = playerById.get(p.player_id ?? -1)?.name ?? `#${p.player_id}`;
                const tm = st.draft.teams.find((t) => t.id === p.team_id)?.name ?? `team ${p.team_id}`;
                return {
                  key: `hist-${p.pick_no}`,
                  text: `Pick ${p.pick_no} (R${p.round_no}): ${tm} drafted ${nm}`,
                  auto: p.is_auto,
                };
              });
            if (history.length > 0) setFeed((f) => [...f, ...history].slice(0, 40));
          }
          if (st.chat) setChat(st.chat);
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
        } else if (msg.type === "chat") {
          const m = msg.message as ChatMessage;
          setChat((prev) => (prev.some((x) => x.seq === m.seq) ? prev : [...prev, m]));
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

  function sendChat(e: React.FormEvent) {
    e.preventDefault();
    const text = chatText.trim();
    if (!text) return;
    send({ type: "chat", text });
    setChatText("");
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

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return available.filter(
      (p) =>
        (roleFilter === "ALL" || p.role === roleFilter) && (q === "" || p.name.toLowerCase().includes(q)),
    );
  }, [available, query, roleFilter]);

  const myDnd = useMemo(
    () => new Set((myTeamId != null && snap?.dnd[String(myTeamId)]) || []),
    [snap, myTeamId],
  );

  const myDndIds = useMemo(() => (myTeamId != null && snap?.dnd[String(myTeamId)]) || [], [snap, myTeamId]);

  const myRoster = myTeamId != null ? snap?.rosters[String(myTeamId)] : undefined;
  const onClock = snap?.on_clock_team_id;
  const myTurn = snap?.draft.status === "live" && onClock === myTeamId;
  const deadline = snap?.pick_deadline;
  const clockLeft = deadline != null ? deadline - now / 1000 : null;
  const complete = snap?.draft.status === "complete";

  // Round of the pick currently on the clock — deriving it from the
  // LAST completed pick lagged one round-boundary behind (P4-W13).
  const roundNo = snap
    ? Math.min(
        snap.draft.rounds,
        Math.max(1, Math.ceil(snap.current_pick_no / Math.max(1, snap.draft.teams.length))),
      )
    : 1;
  const pickPct = snap ? Math.min(100, ((snap.current_pick_no - 1) / Math.max(1, snap.total_picks)) * 100) : 0;
  const onClockName = snap?.draft.teams.find((t) => t.id === onClock)?.name ?? "—";
  const upcoming = snap && !complete ? upcomingTeams(snap, 6) : [];
  const teamName = (id: number) => snap?.draft.teams.find((t) => t.id === id)?.name ?? `team ${id}`;

  return (
    <div>
      <PageHeader title="Draft room" sub="Live snake draft · pick clock with auto-pick (D2)" />
      <p className="mb-4 text-xs"><a href="/cheat-sheet" className="font-medium text-trophy-gold hover:underline">Draft cheat sheet →</a></p>
      {err && (
        <div className="mb-4">
          <ErrorBox message={err} />
        </div>
      )}

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <label className="text-sm text-slate-400">
          Drafting as{" "}
          <select
            value={myTeamId ?? ""}
            onChange={(e) => setMyTeamId(Number(e.target.value))}
            className="rounded-md border border-slate-700 bg-midnight-soft px-2 py-1 text-sm text-white"
          >
            {teams.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
        </label>
        <span
          className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs ${
            draftId && connected
              ? "border-emerald-800 bg-emerald-950/50 text-emerald-300"
              : "border-slate-700 bg-slate-800/50 text-slate-500"
          }`}
        >
          <span className={`h-1.5 w-1.5 rounded-full ${draftId && connected ? "bg-emerald-400" : "bg-slate-600"}`} />
          {draftId ? (connected ? "live" : "connecting…") : "no draft yet"}
        </span>
        <DraftAlertControls snap={snap} myTeamId={myTeamId} clockLeft={clockLeft} />
      </div>

      {!draftId ? (
        <div className="mx-auto max-w-md rounded-2xl border border-slate-800 bg-midnight-soft/70 p-8 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-trophy-gold/15 text-3xl">
            🏏
          </div>
          <h2 className="text-lg font-bold text-white">Ready to draft?</h2>
          <p className="mt-1 text-sm text-slate-400">
            Snake draft, 14 rounds. The pick clock auto-drafts from your board when time runs out.
          </p>
          <button
            onClick={start}
            disabled={starting}
            className="mt-4 rounded-lg bg-trophy-gold px-6 py-2.5 text-sm font-bold uppercase tracking-wide text-midnight transition hover:brightness-110 active:scale-95 disabled:opacity-50"
          >
            {starting ? "Starting…" : "Start draft"}
          </button>
        </div>
      ) : !snap ? (
        <div className="space-y-4" aria-label="Joining draft room">
          <div className={`${styles.shimmer} h-32 rounded-2xl`} />
          <div className="grid gap-4 lg:grid-cols-3">
            <div className={`${styles.shimmer} h-96 rounded-xl lg:col-span-2`} />
            <div className={`${styles.shimmer} h-96 rounded-xl`} />
          </div>
        </div>
      ) : (
        <div className="space-y-5">
          {complete ? (
            <div className="rounded-2xl border border-emerald-800/70 bg-emerald-950/40 p-6 text-center">
              <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-emerald-900/60 text-2xl">
                🏆
              </div>
              <p className="text-lg font-bold text-emerald-300">Draft complete — all {snap.total_picks} picks made.</p>
              <p className="mt-1 text-sm text-slate-400">
                Week-1 lineups are set (best available XI); adjust them before the weekly lock.
              </p>
            </div>
          ) : (
            <div
              className={`rounded-2xl border p-4 transition-colors sm:p-5 ${
                myTurn
                  ? "border-trophy-gold/60 bg-gradient-to-b from-trophy-gold/10 to-midnight-soft"
                  : "border-slate-800 bg-midnight-soft/70"
              }`}
            >
              <div className="flex flex-wrap items-center justify-between gap-4">
                <DraftClock
                  secsLeft={clockLeft}
                  totalSecs={snap.draft.pick_clock_secs}
                  teamName={onClockName}
                  myTurn={!!myTurn}
                />
                <div className="text-right">
                  <p className="text-xs uppercase tracking-widest text-slate-500">
                    Round {roundNo} of {snap.draft.rounds}
                  </p>
                  <p className="mt-0.5 font-mono text-sm text-slate-300">
                    Pick {snap.current_pick_no} <span className="text-slate-600">/ {snap.total_picks}</span>
                  </p>
                </div>
              </div>
              <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-slate-800">
                <div
                  className="h-full rounded-full bg-trophy-gold transition-all duration-500"
                  style={{ width: `${pickPct}%` }}
                />
              </div>
              {upcoming.length > 0 && (
                <div className="mt-3 flex items-center gap-2 text-xs">
                  <span className="shrink-0 text-[10px] uppercase tracking-widest text-slate-500">Up next</span>
                  <span className="text-slate-600">{roundNo % 2 === 1 ? "→" : "←"}</span>
                  <div className="flex gap-1.5 overflow-x-auto">
                    {upcoming.map((tid, i) => (
                      <span
                        key={`${tid}-${i}`}
                        className={`shrink-0 rounded-full px-2 py-0.5 ${
                          i === 0
                            ? "bg-trophy-gold/20 font-semibold text-trophy-gold"
                            : "bg-slate-800 text-slate-400"
                        }`}
                      >
                        {teamName(tid)}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Mobile tabs — desktop shows all three panels side by side */}
          <div className="grid grid-cols-3 gap-1 rounded-xl border border-slate-800 bg-midnight-soft/70 p-1 lg:hidden">
            {TABS.map((t) => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`rounded-lg px-3 py-2 text-sm font-semibold transition ${
                  tab === t.id ? "bg-slate-700 text-white" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>

          <div className="grid gap-5 lg:grid-cols-3">
            <section className={`${tab === "board" ? "" : "hidden"} lg:col-span-2 lg:block`} aria-label="Available players">
              <div className="rounded-xl border border-slate-800 bg-midnight-soft/70 p-4">
                <div className="mb-3 flex items-center justify-between">
                  <h2 className="font-semibold text-white">Available players</h2>
                  <span className="rounded-full bg-slate-800 px-2 py-0.5 font-mono text-xs text-slate-400">
                    {filtered.length}
                  </span>
                </div>
                <div className="mb-2 rounded-lg border border-slate-800 bg-midnight/60 p-2">
                  <ScheduleWeekPicker weeks={sched.weeks} week={sched.week} setWeek={sched.setWeek} />
                  {sched.range && !sched.loading && (
                    <p className="mt-1 text-[11px] text-slate-500">
                      Games per IPL team · fantasy week {sched.week} ({sched.range})
                    </p>
                  )}
                </div>
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search players…"
                  className="mb-2 w-full rounded-lg border border-slate-700 bg-midnight px-3 py-2 text-sm text-white placeholder:text-slate-600 focus:border-trophy-gold/60 focus:outline-none"
                />
                <div className="flex flex-wrap gap-1.5">
                  {ROLE_FILTERS.map((r) => (
                    <button
                      key={r}
                      onClick={() => setRoleFilter(r)}
                      className={`rounded-full px-3 py-1 text-xs font-semibold transition ${
                        roleFilter === r
                          ? "bg-trophy-gold text-midnight"
                          : "border border-slate-700 text-slate-400 hover:border-slate-500 hover:text-slate-200"
                      }`}
                    >
                      {r === "ALL" ? "All" : r}
                    </button>
                  ))}
                </div>
                <div className="mt-3 max-h-[60vh] space-y-1.5 overflow-y-auto pr-1 lg:max-h-[540px]">
                  {filtered.slice(0, 60).map((p) => (
                    <DraftPlayerCard
                      key={p.id}
                      player={p}
                      myTurn={!!myTurn}
                      dnd={myDnd.has(p.id)}
                      onDraft={(id) => send({ type: "pick", player_id: id })}
                      onToggleDnd={(id, active) => send({ type: active ? "dnd_add" : "dnd_remove", player_id: id })}
                      weekGames={sched.map}
                      noted={notedIds.has(p.id)}
                    />
                  ))}
                  {filtered.length === 0 && (
                    <p className="py-8 text-center text-sm text-slate-500">
                      No players match — try a different search or filter.
                    </p>
                  )}
                </div>
              </div>
            </section>

            <section className={`${tab === "roster" ? "" : "hidden"} lg:block`} aria-label="My roster">
              <DraftRoster
                roster={myRoster}
                playerById={playerById}
                dndIds={myDndIds}
                onRemoveDnd={(id) => send({ type: "dnd_remove", player_id: id })}
              />
            </section>

            <section className={`${tab === "feed" ? "" : "hidden"} lg:block`} aria-label="Pick feed">
              <DraftFeed items={feed} />
            </section>

            <section className={`${tab === "ranks" ? "" : "hidden"} lg:col-span-2`} aria-label="My custom ranks">
              <div className="rounded-xl border border-slate-800 bg-midnight-soft/70 p-4">
                <div className="mb-1 flex items-center justify-between gap-3">
                  <h2 className="font-semibold text-white">My ranks</h2>
                  <button
                    type="button"
                    onClick={saveRanks}
                    disabled={ranksSaving || !myTeamId || rankOrder.length === 0}
                    className="rounded-lg bg-trophy-gold px-3 py-1.5 text-xs font-bold text-midnight transition hover:brightness-110 disabled:opacity-50"
                  >
                    {ranksSaving ? "Saving…" : "Save ranks"}
                  </button>
                </div>
                <p className="mb-3 text-xs text-zinc-500">
                  Your personal draft order — auto-pick drafts from the top of this list.
                  Reorder with the arrows, then save.
                </p>
                {ranksMsg && <p className="mb-2 text-xs text-pitch-green">{ranksMsg}</p>}
                <ol className="max-h-[420px] space-y-1 overflow-y-auto pr-1">
                  {rankOrder.map((pid, i) => {
                    const p = playerById.get(pid);
                    return (
                      <li
                        key={pid}
                        className="flex items-center gap-2 rounded-md bg-slate-900/60 px-2.5 py-1.5 text-sm"
                      >
                        <span className="w-7 shrink-0 text-right font-mono text-xs text-zinc-500">{i + 1}</span>
                        <span className="min-w-0 flex-1 truncate text-zinc-200">
                          {p?.name ?? `#${pid}`}
                          <span className="ml-2 text-[11px] text-zinc-500">
                            {p?.role ?? ""} · {p?.ipl_team_code ?? ""}
                            {drafted.has(pid) ? " · drafted" : ""}
                          </span>
                        </span>
                        <button
                          type="button"
                          aria-label={`Move ${p?.name ?? pid} up`}
                          onClick={() => moveRank(i, -1)}
                          className="rounded bg-slate-800 px-1.5 py-0.5 text-xs text-zinc-300 hover:bg-slate-700"
                        >
                          ↑
                        </button>
                        <button
                          type="button"
                          aria-label={`Move ${p?.name ?? pid} down`}
                          onClick={() => moveRank(i, 1)}
                          className="rounded bg-slate-800 px-1.5 py-0.5 text-xs text-zinc-300 hover:bg-slate-700"
                        >
                          ↓
                        </button>
                      </li>
                    );
                  })}
                </ol>
              </div>
            </section>

            <section className={`${tab === "chat" ? "" : "hidden"} lg:block`} aria-label="Room chat">
              <div className="rounded-xl border border-slate-800 bg-midnight-soft/70 p-4">
                <h2 className="mb-3 font-semibold text-white">Room chat</h2>
                <div className="mb-3 max-h-64 space-y-2 overflow-y-auto pr-1">
                  {chat.length === 0 && (
                    <p className="text-xs text-zinc-600">No messages yet — say something nice about someone&apos;s last pick.</p>
                  )}
                  {chat.map((m) => (
                    <p key={m.seq} className="text-sm">
                      <span className={m.team_id === myTeamId ? "font-bold text-trophy-gold" : "font-bold text-zinc-300"}>
                        {m.team_name}
                      </span>{" "}
                      <span className="text-zinc-300">{m.text}</span>
                    </p>
                  ))}
                </div>
                <form onSubmit={sendChat} className="flex gap-2">
                  <input
                    value={chatText}
                    onChange={(e) => setChatText(e.target.value)}
                    maxLength={500}
                    placeholder="Message the room…"
                    aria-label="Chat message"
                    className="min-w-0 flex-1 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white placeholder:text-zinc-600 focus:border-trophy-gold focus:outline-none"
                  />
                  <button
                    type="submit"
                    disabled={!connected || !chatText.trim()}
                    className="rounded-lg bg-trophy-gold px-3 py-2 text-xs font-bold text-midnight transition hover:brightness-110 disabled:opacity-50"
                  >
                    Send
                  </button>
                </form>
              </div>
            </section>
          </div>
        </div>
      )}
    </div>
  );
}
