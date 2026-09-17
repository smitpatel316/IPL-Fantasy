"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { ApiError, type PlayerOut, type TeamOut, type WaiverClaimOut } from "@/lib/types";
import { PageHeader, ErrorBox } from "@/components/ui";
import { GameCountBadge, ScheduleWeekPicker, useScheduleBadges } from "@/components/ScheduleBadges";
import { cn } from "@/lib/utils";
import { Gavel, CircleDollarSign, Timer, Scale, ArrowRight } from "lucide-react";

const STATUS_STYLE: Record<string, string> = {
  pending: "bg-trophy-gold/15 text-trophy-gold",
  won: "bg-pitch-green/15 text-pitch-green",
  lost: "bg-slate-800 text-zinc-500",
};

const ROLES = ["", "WK", "BAT", "AR", "BOWL"];
const ROLE_COLOR: Record<string, string> = {
  WK: "text-yellow-300 bg-yellow-300/10",
  BAT: "text-blue-300 bg-blue-300/10",
  AR: "text-purple-300 bg-purple-300/10",
  BOWL: "text-green-300 bg-green-300/10",
};
const WEEKS = [8, 7, 6, 5, 4, 3, 2, 1];

const input =
  "rounded-md border border-slate-700 bg-midnight px-3 py-2 text-sm text-white placeholder:text-slate-500 focus:border-ipl-blue-bright focus:outline-none";
const btnPrimary =
  "rounded-md bg-ipl-blue px-4 py-2 text-sm font-semibold text-white hover:bg-ipl-blue-bright disabled:opacity-40 disabled:cursor-not-allowed";
const btnGhost =
  "rounded-md border border-slate-700 px-4 py-2 text-sm text-slate-300 hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed";

export default function WaiversPage() {
  const [teams, setTeams] = useState<TeamOut[]>([]);
  const [teamId, setTeamId] = useState<number | null>(null);
  const [players, setPlayers] = useState<PlayerOut[]>([]);
  const [claims, setClaims] = useState<WaiverClaimOut[]>([]);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);
  const [q, setQ] = useState("");
  const [role, setRole] = useState("");

  // bid panel state
  const [bidTarget, setBidTarget] = useState<PlayerOut | null>(null);
  const [dropId, setDropId] = useState("");
  const [amount, setAmount] = useState("");
  const [bidErr, setBidErr] = useState("");
  const [bidOk, setBidOk] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const team = useMemo(() => teams.find((t) => t.id === teamId) ?? null, [teams, teamId]);
  const faab = team?.faab_remaining ?? 0;
  const freeAgents = useMemo(() => players.filter((p) => p.owned_by_team_id == null), [players]);
  const roster = useMemo(() => players.filter((p) => p.owned_by_team_id === teamId), [players, teamId]);
  const playerName = useMemo(() => new Map(players.map((p) => [p.id, p.name])), [players]);
  const teamName = useMemo(() => new Map(teams.map((t) => [t.id, t.name])), [teams]);
  const sorted = useMemo(() => [...teams].sort((a, b) => b.faab_remaining - a.faab_remaining), [teams]);
  const claimsWeek = claims[0]?.week_no;

  async function load() {
    setLoading(true);
    setErr("");
    try {
      const ts = await api.listTeams(1);
      setTeams(ts);
      const sel = teamId ?? ts[0]?.id ?? null;
      if (sel !== teamId) setTeamId(sel);
      const ps = await api.listPlayers({ league_id: 1, role: role || undefined, q: q || undefined });
      setPlayers(ps);
      // Claims feed: show the latest week that has any.
      const weeks = await Promise.all(WEEKS.map((w) => api.pendingClaims(1, w).catch(() => [] as WaiverClaimOut[])));
      const latest = WEEKS.find((w, i) => weeks[i].length > 0);
      setClaims(latest != null ? weeks[WEEKS.indexOf(latest)] : []);
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "load failed");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function openBid(p: PlayerOut) {
    setBidTarget(p);
    setBidErr("");
    setBidOk("");
    setDropId(roster[0] ? String(roster[0].id) : "");
    setAmount("");
  }

  async function submitBid() {
    if (!bidTarget || teamId == null) return;
    setBidErr("");
    setBidOk("");
    const amt = Number(amount);
    if (!Number.isInteger(amt) || amt < 0) {
      setBidErr("Bid must be a whole-dollar amount of $0 or more.");
      return;
    }
    if (amt > faab) {
      setBidErr(`That bid is over your remaining budget ($${faab}).`);
      return;
    }
    if (!dropId) {
      setBidErr("Pick a player to drop — rosters are capped at 14, so every claim needs a drop.");
      return;
    }
    setSubmitting(true);
    try {
      await api.submitClaim({
        league_id: 1,
        team_id: teamId,
        add_player_id: bidTarget.id,
        drop_player_id: Number(dropId),
        bid: amt,
      });
      setBidOk(`Bid of $${amt} submitted for ${bidTarget.name}. It's blind — other managers can't see it.`);
      setBidTarget(null);
      await load();
    } catch (e) {
      setBidErr(e instanceof ApiError ? e.message : "bid failed");
    } finally {
      setSubmitting(false);
    }
  }

  // P3-A6: schedule-aware nudge — games per IPL team per fantasy week.
  const sched = useScheduleBadges(1, 1);

  return (
    <div>
      <PageHeader title="Waivers" sub="Weekly blind FAAB · $100 season budget · runs Wednesday ~3am PT" />

      <div className="mb-5 grid gap-2 sm:grid-cols-3">
        {[
          { icon: Gavel, label: "Blind bids", sub: "Nobody sees your bid" },
          { icon: Timer, label: "Runs Wednesday", sub: "~3am PT, weekly" },
          { icon: Scale, label: "Tiebreak", sub: "Reverse standings" },
        ].map(({ icon: Icon, label, sub }) => (
          <div key={label} className="flex items-center gap-3 rounded-xl border border-slate-800 bg-midnight-soft px-4 py-3">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-trophy-gold/10 text-trophy-gold">
              <Icon className="h-4 w-4" />
            </span>
            <div>
              <p className="text-sm font-semibold text-white">{label}</p>
              <p className="text-xs text-zinc-500">{sub}</p>
            </div>
          </div>
        ))}
      </div>

      {err && <div className="mb-4"><ErrorBox message={err} onRetry={load} /></div>}

      {/* P3-A6 schedule-aware nudge: target players from teams with more games. */}
      <section className="mb-6 rounded-xl border border-slate-800 bg-midnight-soft p-4 sm:p-5">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-bold uppercase tracking-wider text-zinc-300">
            Schedule outlook{sched.range ? ` · fantasy week ${sched.week} (${sched.range})` : ""}
          </h2>
          <ScheduleWeekPicker weeks={sched.weeks} week={sched.week} setWeek={sched.setWeek} />
        </div>
        {sched.loading ? (
          <p className="text-xs text-slate-500">Loading game counts…</p>
        ) : sched.map.size === 0 ? (
          <p className="text-xs text-slate-500">
            No fixture imported yet — schedule badges appear once the importer runs.
          </p>
        ) : (
          <div className="flex flex-wrap gap-1.5">
            {[...sched.map.entries()].map(([code, games]) => (
              <GameCountBadge key={code} code={code} games={games} />
            ))}
          </div>
        )}
        <p className="mt-2 text-[11px] text-slate-500">
          More games = more chances to score. Bid with the schedule in mind.
        </p>
      </section>

      <section className="mb-6 rounded-xl border border-slate-800 bg-midnight-soft p-4 sm:p-5">
        <h2 className="mb-4 flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-zinc-300">
          <CircleDollarSign className="h-4 w-4 text-trophy-gold" /> FAAB remaining
        </h2>
        <div className="space-y-3">
          {sorted.map((t) => (
            <div key={t.id}>
              <div className="mb-1 flex items-baseline justify-between text-sm">
                <span className="font-medium text-zinc-200">{t.name}</span>
                <span className="tabular-nums font-bold text-trophy-gold">${t.faab_remaining}</span>
              </div>
              <div className="h-1.5 overflow-hidden rounded-full bg-slate-800">
                <div
                  className="h-full rounded-full bg-trophy-gold/80"
                  style={{ width: `${Math.max(0, Math.min(100, t.faab_remaining))}%` }}
                />
              </div>
            </div>
          ))}
          {sorted.length === 0 && <p className="text-sm text-zinc-600">No teams yet.</p>}
        </div>
      </section>

      <form
        className="mb-6 flex flex-wrap items-end gap-3 rounded-xl border border-slate-800 bg-midnight-soft p-5"
        onSubmit={(e) => {
          e.preventDefault();
          load();
        }}
      >
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-400">Managing as</label>
          <select className={input} value={teamId ?? ""} onChange={(e) => setTeamId(Number(e.target.value))}>
            {teams.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name} (${t.faab_remaining} left)
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-400">Search</label>
          <input className={cn(input, "w-56")} placeholder="Player name…" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-400">Role</label>
          <select className={input} value={role} onChange={(e) => setRole(e.target.value)}>
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {r || "All roles"}
              </option>
            ))}
          </select>
        </div>
        <button className={btnPrimary} disabled={loading}>
          {loading ? "Loading…" : "Search"}
        </button>
      </form>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <h2 className="mb-2 text-sm font-bold uppercase tracking-wider text-zinc-300">Free agents</h2>
          {freeAgents.length === 0 ? (
            <p className="text-sm text-slate-500">No free agents match{loading ? " (loading)…" : "."}</p>
          ) : (
            <div className="overflow-hidden rounded-xl border border-slate-800">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-midnight-soft text-left text-xs uppercase text-slate-400">
                    <th className="px-3 py-2">Rank</th>
                    <th className="px-3 py-2">Player</th>
                    <th className="px-3 py-2">Role</th>
                    <th className="px-3 py-2">IPL team</th>
                    <th className="px-3 py-2 text-right">Claim</th>
                  </tr>
                </thead>
                <tbody>
                  {freeAgents.map((p) => (
                    <tr key={p.id} className="border-t border-slate-800/60 hover:bg-slate-900/50">
                      <td className="px-3 py-2 text-slate-500">{p.preseason_rank ?? "—"}</td>
                      <td className="px-3 py-2 font-medium text-white">
                        {p.name}
                        {p.is_overseas && (
                          <span className="ml-2 rounded bg-slate-700/60 px-1.5 py-0.5 text-[10px] font-semibold text-slate-300">
                            OS
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-2">
                        <span className={cn("rounded px-1.5 py-0.5 text-[11px] font-semibold", ROLE_COLOR[p.role ?? ""] ?? "text-slate-300 bg-slate-700/40")}>
                          {p.role ?? "—"}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-slate-400">{p.ipl_team_code ?? "—"}</td>
                      <td className="px-3 py-2 text-right">
                        <button
                          className="rounded-md bg-trophy-gold/15 px-3 py-1 text-xs font-semibold text-trophy-gold hover:bg-trophy-gold/25"
                          onClick={() => openBid(p)}
                        >
                          Bid
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div>
          <h2 className="mb-3 text-sm font-bold uppercase tracking-wider text-zinc-300">
            Claims{claimsWeek ? ` — week ${claimsWeek}` : ""}
          </h2>
          {claims.length === 0 ? (
            <p className="text-sm text-slate-500">No bids in yet this week.</p>
          ) : (
            <ul className="space-y-2">
              {claims.map((c) => (
                <li
                  key={c.id}
                  className="flex flex-wrap items-center gap-x-3 gap-y-1.5 rounded-xl border border-slate-800 bg-midnight-soft px-4 py-3 text-sm"
                >
                  <span className="font-semibold text-white">{teamName.get(c.team_id) ?? `Team ${c.team_id}`}</span>
                  <span className="inline-flex items-center gap-1.5 text-zinc-300">
                    adds <span className="font-medium text-white">{playerName.get(c.add_player_id) ?? `#${c.add_player_id}`}</span>
                  </span>
                  {c.drop_player_id != null && (
                    <span className="inline-flex items-center gap-1.5 text-zinc-500">
                      <ArrowRight className="h-3.5 w-3.5" />
                      drops {playerName.get(c.drop_player_id) ?? `#${c.drop_player_id}`}
                    </span>
                  )}
                  <span className="ml-auto flex items-center gap-2">
                    <span className="tabular-nums font-bold text-trophy-gold">${c.bid}</span>
                    <span className={cn("rounded px-1.5 py-0.5 text-[11px] font-bold uppercase", STATUS_STYLE[c.status] ?? "bg-slate-800 text-zinc-400")}>
                      {c.status}
                    </span>
                  </span>
                </li>
              ))}
            </ul>
          )}
          <p className="mt-2 text-xs text-slate-500">
            Bids are blind — amounts stay sealed until the Wednesday run. Highest bid wins; ties go to the worse-standing team.
          </p>
        </div>
      </div>

      {bidTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={() => setBidTarget(null)}>
          <div
            className="w-full max-w-md rounded-xl border border-slate-700 bg-midnight-soft p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-lg font-semibold text-white">Bid for {bidTarget.name}</h3>
            <p className="mt-1 text-sm text-slate-400">
              {bidTarget.role ?? "—"} · {bidTarget.ipl_team_code ?? "—"}
              {bidTarget.is_overseas ? " · overseas" : ""} · you have <span className="font-semibold text-trophy-gold">${faab}</span> left
            </p>
            <div className="mt-4 space-y-3">
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-400">Player to drop (rosters are capped at 14)</label>
                <select className={cn(input, "w-full")} value={dropId} onChange={(e) => setDropId(e.target.value)}>
                  {roster.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({p.role ?? "—"}, {p.ipl_team_code ?? "—"})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-400">Bid ($0 – ${faab})</label>
                <input
                  className={cn(input, "w-full")}
                  inputMode="numeric"
                  placeholder="0"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value.replace(/[^0-9]/g, ""))}
                />
              </div>
            </div>
            {bidErr && (
              <div className="mt-3">
                <ErrorBox message={bidErr} />
              </div>
            )}
            {bidOk && <p className="mt-3 text-sm text-green-300">{bidOk}</p>}
            <div className="mt-5 flex justify-end gap-2">
              <button className={btnGhost} onClick={() => setBidTarget(null)} disabled={submitting}>
                Cancel
              </button>
              <button className={btnPrimary} onClick={submitBid} disabled={submitting}>
                {submitting ? "Submitting…" : "Submit bid"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
