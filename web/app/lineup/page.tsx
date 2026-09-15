"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ApiError, type PlayerOut, type TeamOut } from "@/lib/types";
import { PageHeader, ErrorBox, EngineStub } from "@/components/ui";
import { cn } from "@/lib/utils";

const SLOTS = ["WK", "BAT", "AR", "BOWL", "UTIL", "BN", "IL"] as const;
const SLOT_MAX: Record<string, number> = { WK: 1, BAT: 3, AR: 2, BOWL: 3, UTIL: 2, BN: 3, IL: 1 };

export default function LineupPage() {
  const [teams, setTeams] = useState<TeamOut[]>([]);
  const [teamId, setTeamId] = useState<number | null>(null);
  const [week, setWeek] = useState(1);
  const [roster, setRoster] = useState<PlayerOut[]>([]);
  const [slots, setSlots] = useState<Record<string, number[]>>({});
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");

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
    api
      .listPlayers({ league_id: 1 })
      .then((ps) => setRoster(ps.filter((p) => p.owned_by_team_id === teamId)))
      .catch(() => {});
  }, [teamId]);

  function toggle(slot: string, pid: number) {
    setSlots((prev) => {
      const cur = prev[slot] ?? [];
      const next = { ...prev };
      if (cur.includes(pid)) {
        next[slot] = cur.filter((x) => x !== pid);
      } else {
        // remove from any other slot first (one player, one slot)
        for (const s of Object.keys(next)) next[s] = next[s].filter((x) => x !== pid);
        next[slot] = [...cur.filter((x) => x !== pid), pid].slice(0, SLOT_MAX[slot]);
      }
      return next;
    });
  }

  async function save() {
    if (!teamId) return;
    setErr("");
    setMsg("");
    try {
      const out = await api.setLineup(teamId, week, slots);
      setMsg(`Lineup saved · ${out.overseas_starters}/4 overseas starters`);
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "save failed");
    }
  }

  const overseas = roster.filter((p) => p.is_overseas && Object.entries(slots).some(
    ([s, ids]) => ["WK", "BAT", "AR", "BOWL", "UTIL"].includes(s) && ids.includes(p.id),
  )).length;

  return (
    <div>
      <PageHeader title="My lineup" sub="Weekly lock · set your XI once per fantasy week (D5)" />
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <select
          className="rounded-md border border-slate-700 bg-midnight px-3 py-2 text-sm"
          value={teamId ?? ""}
          onChange={(e) => setTeamId(Number(e.target.value))}
        >
          {teams.map((t) => (
            <option key={t.id} value={t.id}>{t.name}</option>
          ))}
        </select>
        <select
          className="rounded-md border border-slate-700 bg-midnight px-3 py-2 text-sm"
          value={week}
          onChange={(e) => setWeek(Number(e.target.value))}
        >
          {[1, 2, 3, 4, 5, 6, 7, 8].map((w) => (
            <option key={w} value={w}>Week {w}{w >= 7 ? " (playoff)" : ""}</option>
          ))}
        </select>
        <span className={cn("text-sm", overseas > 4 ? "text-brick-red font-semibold" : "text-slate-400")}>
          ✈ {overseas}/4 overseas starters
        </span>
        <button onClick={save} className="rounded-md bg-pitch-green px-4 py-2 text-sm font-semibold text-midnight hover:brightness-110">
          Save lineup
        </button>
      </div>
      {err && <div className="mb-4"><ErrorBox message={err} /></div>}
      {msg && <p className="mb-4 text-sm text-pitch-green">{msg}</p>}

      {roster.length === 0 ? (
        <EngineStub track="P2-L1" what="Roster construction (draft)" />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          <div className="rounded-xl border border-slate-800 bg-midnight-soft p-4">
            <h2 className="mb-3 font-semibold text-white">Starting slots</h2>
            <div className="space-y-3">
              {SLOTS.filter((s) => !["BN", "IL"].includes(s)).map((slot) => (
                <div key={slot}>
                  <p className="mb-1 text-xs font-semibold uppercase text-slate-500">
                    {slot} <span className="text-slate-600">({(slots[slot] ?? []).length}/{SLOT_MAX[slot]})</span>
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {(slots[slot] ?? []).map((pid) => {
                      const p = roster.find((r) => r.id === pid);
                      return (
                        <button
                          key={pid}
                          onClick={() => toggle(slot, pid)}
                          className="rounded-md bg-ipl-blue px-2.5 py-1 text-xs font-medium text-white hover:bg-brick-red"
                          title="click to remove"
                        >
                          {p?.name}{p?.is_overseas ? " ✈" : ""}
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="rounded-xl border border-slate-800 bg-midnight-soft p-4">
            <h2 className="mb-3 font-semibold text-white">My roster (tap to assign)</h2>
            <div className="mb-2 flex flex-wrap gap-1.5">
              {SLOTS.map((s) => (
                <span key={s} className="text-[11px] text-slate-500">
                  {s}×{SLOT_MAX[s]}
                </span>
              ))}
            </div>
            <div className="max-h-96 space-y-1 overflow-y-auto">
              {roster.map((p) => (
                <div key={p.id} className="flex items-center justify-between rounded-md px-2 py-1.5 hover:bg-slate-800/50">
                  <span className="text-sm text-white">
                    {p.name} <span className="text-xs text-slate-500">{p.role}{p.is_overseas ? " ✈" : ""}</span>
                  </span>
                  <select
                    className="rounded border border-slate-700 bg-midnight px-1.5 py-1 text-xs"
                    value={Object.entries(slots).find(([, ids]) => ids.includes(p.id))?.[0] ?? ""}
                    onChange={(e) => e.target.value && toggle(e.target.value, p.id)}
                  >
                    <option value="">—</option>
                    {SLOTS.map((s) => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
