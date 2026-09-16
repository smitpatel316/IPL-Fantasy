"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { ApiError, type PlayerOut, type TeamOut } from "@/lib/types";
import { PageHeader, ErrorBox } from "@/components/ui";
import { ScrollHint } from "@/components/ScrollHint";
import { cn } from "@/lib/utils";
import { Plane, Save, Search, X, CheckCircle2, AlertTriangle } from "lucide-react";

const STARTERS: { slot: string; max: number; label: string }[] = [
  { slot: "WK", max: 1, label: "Wicket-keeper" },
  { slot: "BAT", max: 3, label: "Batters" },
  { slot: "AR", max: 2, label: "All-rounders" },
  { slot: "BOWL", max: 3, label: "Bowlers" },
  { slot: "UTIL", max: 2, label: "Utility" },
];
const SQUAD: { slot: string; max: number; label: string }[] = [
  { slot: "BN", max: 3, label: "Bench" },
  { slot: "IL", max: 1, label: "Injured list" },
];
const ALL_SLOTS = [...STARTERS, ...SQUAD];
const WEEKS = [1, 2, 3, 4, 5, 6, 7, 8];
const OVERSEAS_CAP = 4;

const ROLE_BADGE: Record<string, string> = {
  WK: "bg-yellow-400/10 text-yellow-300",
  BAT: "bg-blue-400/10 text-blue-300",
  AR: "bg-purple-400/10 text-purple-300",
  BOWL: "bg-emerald-400/10 text-emerald-300",
};

function playerSlot(slots: Record<string, number[]>, pid: number): string | null {
  for (const [s, ids] of Object.entries(slots)) if (ids.includes(pid)) return s;
  return null;
}

export default function LineupPage() {
  const [teams, setTeams] = useState<TeamOut[]>([]);
  const [teamId, setTeamId] = useState<number | null>(null);
  const [week, setWeek] = useState(1);
  const [roster, setRoster] = useState<PlayerOut[]>([]);
  const [slots, setSlots] = useState<Record<string, number[]>>({});
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");
  const [saving, setSaving] = useState(false);
  const [q, setQ] = useState("");
  const [role, setRole] = useState("");

  useEffect(() => {
    api
      .listTeams(1)
      .then((t) => {
        setTeams(t);
        if (t[0]) setTeamId(t[0].id);
      })
      .catch((e) => setErr(e instanceof ApiError ? e.message : "load failed"));
  }, []);

  useEffect(() => {
    if (!teamId) return;
    setErr("");
    api
      .listPlayers({ league_id: 1 })
      .then((ps) => setRoster(ps.filter((p) => p.owned_by_team_id === teamId)))
      .catch(() => {});
    // Prefill from any saved lineup for this team+week.
    api
      .getLineup(teamId, week)
      .then((l) => setSlots(l.slots ?? {}))
      .catch(() => setSlots({}));
  }, [teamId, week]);

  function toggle(slot: string, pid: number) {
    setMsg("");
    setSlots((prev) => {
      const max = ALL_SLOTS.find((s) => s.slot === slot)?.max ?? 1;
      const next: Record<string, number[]> = {};
      for (const s of Object.keys(prev)) next[s] = prev[s].filter((x) => x !== pid);
      const cur = next[slot] ?? [];
      if (!(prev[slot] ?? []).includes(pid) && cur.length < max) {
        next[slot] = [...cur, pid];
      }
      return next;
    });
  }

  async function save() {
    if (!teamId) return;
    setErr("");
    setMsg("");
    setSaving(true);
    try {
      const out = await api.setLineup(teamId, week, slots);
      setMsg(`Lineup saved · ${out.overseas_starters}/${OVERSEAS_CAP} overseas starters`);
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "save failed");
    } finally {
      setSaving(false);
    }
  }

  const startersSet = STARTERS.reduce((n, s) => n + (slots[s.slot] ?? []).length, 0);
  const overseas = roster.filter(
    (p) =>
      p.is_overseas &&
      STARTERS.some((s) => (slots[s.slot] ?? []).includes(p.id)),
  ).length;
  const overCap = overseas > OVERSEAS_CAP;

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return roster.filter(
      (p) =>
        (!role || p.role === role) &&
        (!needle || p.name.toLowerCase().includes(needle)),
    );
  }, [roster, q, role]);

  const byId = useMemo(() => new Map(roster.map((p) => [p.id, p])), [roster]);

  return (
    <div>
      <PageHeader
        title="Lineup"
        sub={`Week ${week}${week >= 7 ? " · playoffs" : ""} · set your XI — lineups lock at the week's first ball`}
      />

      {/* Controls */}
      <div className="mb-5 rounded-xl border border-slate-800 bg-midnight-soft p-4">
        <div className="flex flex-wrap items-center gap-3">
          <select
            aria-label="Team"
            className="rounded-lg border border-slate-700 bg-midnight px-3 py-2 text-sm text-white focus:border-trophy-gold focus:outline-none"
            value={teamId ?? ""}
            onChange={(e) => setTeamId(Number(e.target.value))}
          >
            {teams.map((t) => (
              <option key={t.id} value={t.id}>{t.name}</option>
            ))}
          </select>
          <ScrollHint className="flex flex-1 items-center gap-1 overflow-x-auto" role="tablist" aria-label="Week">
            {WEEKS.map((w) => (
              <button
                key={w}
                role="tab"
                aria-selected={week === w}
                onClick={() => setWeek(w)}
                className={cn(
                  "shrink-0 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  week === w
                    ? "bg-trophy-gold text-midnight"
                    : "text-zinc-400 hover:bg-slate-800 hover:text-white",
                )}
              >
                {w}
                {w >= 7 && <span className={cn("ml-1 text-[10px]", week === w ? "text-midnight/70" : "text-trophy-gold")}>PO</span>}
              </button>
            ))}
          </ScrollHint>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-slate-800/70 pt-3">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wide text-zinc-500">Starters</span>
            <div className="h-1.5 w-24 overflow-hidden rounded-full bg-slate-800">
              <div
                className={cn("h-full rounded-full transition-all", startersSet === 11 ? "bg-pitch-green" : "bg-trophy-gold")}
                style={{ width: `${(startersSet / 11) * 100}%` }}
              />
            </div>
            <span className="text-xs text-zinc-400">{startersSet}/11</span>
          </div>
          <div className={cn("flex items-center gap-1.5", overCap ? "text-brick-red" : "text-zinc-400")}>
            <Plane className="h-3.5 w-3.5" />
            <div className="flex gap-1" aria-label={`${overseas} of ${OVERSEAS_CAP} overseas starters`}>
              {Array.from({ length: OVERSEAS_CAP }).map((_, i) => (
                <span
                  key={i}
                  className={cn(
                    "h-2 w-2 rounded-full",
                    i < overseas ? (overCap ? "bg-brick-red" : "bg-trophy-gold") : "bg-slate-700",
                  )}
                />
              ))}
            </div>
            <span className="text-xs font-medium">{overseas}/{OVERSEAS_CAP} overseas</span>
          </div>
          <button
            onClick={save}
            disabled={saving || !teamId}
            className="ml-auto inline-flex items-center gap-2 rounded-lg bg-trophy-gold px-5 py-2 text-sm font-bold text-midnight transition hover:brightness-110 disabled:opacity-50"
          >
            <Save className="h-4 w-4" />
            {saving ? "Saving…" : "Save lineup"}
          </button>
        </div>
        {overCap && (
          <p className="mt-2 flex items-center gap-1.5 text-xs text-brick-red">
            <AlertTriangle className="h-3.5 w-3.5" /> Too many overseas starters — max {OVERSEAS_CAP} in the XI.
          </p>
        )}
      </div>

      {err && <div className="mb-4"><ErrorBox message={err} /></div>}
      {msg && (
        <p className="mb-4 flex items-center gap-1.5 text-sm text-pitch-green">
          <CheckCircle2 className="h-4 w-4" /> {msg}
        </p>
      )}

      <div className="grid gap-5 lg:grid-cols-5">
        {/* Slots */}
        <div className="space-y-5 lg:col-span-3">
          <section className="rounded-xl border border-slate-800 bg-midnight-soft p-4 sm:p-5">
            <h2 className="mb-4 text-sm font-bold uppercase tracking-wider text-zinc-300">
              Starting XI
            </h2>
            <div className="space-y-4">
              {STARTERS.map(({ slot, max, label }) => {
                const ids = slots[slot] ?? [];
                return (
                  <div key={slot}>
                    <div className="mb-1.5 flex items-center justify-between">
                      <p className="text-xs font-semibold text-zinc-400">
                        <span className="mr-2 inline-block w-11 rounded bg-slate-800 px-1.5 py-0.5 text-center font-bold text-zinc-200">{slot}</span>
                        {label}
                      </p>
                      <span className={cn("text-xs font-medium", ids.length === max ? "text-pitch-green" : "text-zinc-500")}>
                        {ids.length}/{max}
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {ids.map((pid) => {
                        const p = byId.get(pid);
                        return (
                          <button
                            key={pid}
                            onClick={() => toggle(slot, pid)}
                            title="Tap to remove"
                            className="group inline-flex items-center gap-1.5 rounded-lg border border-ipl-blue-bright/40 bg-ipl-blue/25 px-2.5 py-1.5 text-xs font-medium text-white transition hover:border-brick-red/60 hover:bg-brick-red/15"
                          >
                            {p?.name ?? `#${pid}`}
                            {p?.is_overseas && <Plane className="h-3 w-3 text-zinc-400" />}
                            <X className="h-3 w-3 text-zinc-500 group-hover:text-brick-red" />
                          </button>
                        );
                      })}
                      {Array.from({ length: max - ids.length }).map((_, i) => (
                        <span
                          key={`empty-${i}`}
                          className="rounded-lg border border-dashed border-slate-700 px-3 py-1.5 text-xs text-zinc-600"
                        >
                          Empty
                        </span>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </section>

          <section className="rounded-xl border border-slate-800 bg-midnight-soft p-4 sm:p-5">
            <h2 className="mb-4 text-sm font-bold uppercase tracking-wider text-zinc-300">
              Squad
            </h2>
            <div className="space-y-4">
              {SQUAD.map(({ slot, max, label }) => {
                const ids = slots[slot] ?? [];
                return (
                  <div key={slot}>
                    <div className="mb-1.5 flex items-center justify-between">
                      <p className="text-xs font-semibold text-zinc-400">
                        <span className="mr-2 inline-block w-11 rounded bg-slate-800 px-1.5 py-0.5 text-center font-bold text-zinc-200">{slot}</span>
                        {label}
                        {slot === "IL" && <span className="ml-2 font-normal text-zinc-600">missed / expected to miss a game</span>}
                      </p>
                      <span className="text-xs font-medium text-zinc-500">{ids.length}/{max}</span>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {ids.map((pid) => {
                        const p = byId.get(pid);
                        return (
                          <button
                            key={pid}
                            onClick={() => toggle(slot, pid)}
                            title="Tap to remove"
                            className="group inline-flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800/60 px-2.5 py-1.5 text-xs font-medium text-zinc-200 transition hover:border-brick-red/60 hover:bg-brick-red/15"
                          >
                            {p?.name ?? `#${pid}`}
                            {p?.is_overseas && <Plane className="h-3 w-3 text-zinc-500" />}
                            <X className="h-3 w-3 text-zinc-500 group-hover:text-brick-red" />
                          </button>
                        );
                      })}
                      {Array.from({ length: max - ids.length }).map((_, i) => (
                        <span key={`empty-${i}`} className="rounded-lg border border-dashed border-slate-700 px-3 py-1.5 text-xs text-zinc-600">
                          Empty
                        </span>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        </div>

        {/* Roster */}
        <div className="lg:col-span-2">
          <section className="rounded-xl border border-slate-800 bg-midnight-soft p-4 sm:p-5 lg:sticky lg:top-20">
            <h2 className="mb-3 text-sm font-bold uppercase tracking-wider text-zinc-300">
              My roster <span className="ml-1 font-medium normal-case text-zinc-500">{roster.length} players</span>
            </h2>
            <div className="mb-3 flex gap-2">
              <div className="relative flex-1">
                <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-zinc-500" />
                <input
                  value={q}
                  onChange={(e) => setQ(e.target.value)}
                  placeholder="Search roster…"
                  className="w-full rounded-lg border border-slate-700 bg-midnight py-2 pl-8 pr-3 text-sm text-white placeholder:text-zinc-600 focus:border-trophy-gold focus:outline-none"
                />
              </div>
            </div>
            <div className="mb-3 flex gap-1.5">
              {["", "WK", "BAT", "AR", "BOWL"].map((r) => (
                <button
                  key={r}
                  onClick={() => setRole(r)}
                  className={cn(
                    "rounded-md px-2.5 py-1 text-xs font-semibold transition",
                    role === r ? "bg-trophy-gold text-midnight" : "bg-slate-800 text-zinc-400 hover:text-white",
                  )}
                >
                  {r || "All"}
                </button>
              ))}
            </div>
            <div className="-mx-1 max-h-[28rem] space-y-1 overflow-y-auto px-1">
              {filtered.map((p) => {
                const assigned = playerSlot(slots, p.id);
                return (
                  <div
                    key={p.id}
                    className={cn(
                      "flex items-center gap-2 rounded-lg px-2 py-2 transition",
                      assigned ? "bg-ipl-blue/10" : "hover:bg-slate-800/50",
                    )}
                  >
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-white">
                        {p.name}
                        {p.is_overseas && <Plane className="ml-1.5 inline h-3 w-3 text-zinc-500" />}
                      </p>
                      <p className="mt-0.5 flex items-center gap-1.5 text-[11px] text-zinc-500">
                        {p.role && (
                          <span className={cn("rounded px-1 py-px text-[10px] font-bold", ROLE_BADGE[p.role])}>
                            {p.role}
                          </span>
                        )}
                        <span>{p.ipl_team_code ?? "—"}</span>
                        {assigned && <span className="font-semibold text-ipl-blue-bright">· {assigned}</span>}
                      </p>
                    </div>
                    <select
                      aria-label={`Assign ${p.name} to slot`}
                      className="shrink-0 rounded-md border border-slate-700 bg-midnight px-1.5 py-1.5 text-xs text-zinc-300 focus:border-trophy-gold focus:outline-none"
                      value={assigned ?? ""}
                      onChange={(e) => {
                        if (e.target.value) toggle(e.target.value, p.id);
                        else if (assigned) toggle(assigned, p.id);
                      }}
                    >
                      <option value="">—</option>
                      {ALL_SLOTS.map((s) => (
                        <option key={s.slot} value={s.slot}>{s.slot}</option>
                      ))}
                    </select>
                  </div>
                );
              })}
              {filtered.length === 0 && (
                <p className="py-8 text-center text-sm text-zinc-600">
                  {roster.length === 0 ? "No players yet — run the draft first." : "No players match."}
                </p>
              )}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
