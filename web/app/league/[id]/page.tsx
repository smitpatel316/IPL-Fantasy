"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useLeague } from "@/lib/league-context";
import { ApiError, type AdjustmentOut, type LeagueDetailOut } from "@/lib/types";
import { PageHeader, ErrorBox } from "@/components/ui";
import { cn } from "@/lib/utils";
import { Trophy, Settings2, ArrowRight, Crown } from "lucide-react";

export default function LeaguePage({ params }: { params: Promise<{ id: string }> }) {
  const [id, setId] = useState<string | null>(null);
  const [league, setLeague] = useState<LeagueDetailOut | null>(null);
  const [err, setErr] = useState("");
  const { setLeagueId } = useLeague();

  useEffect(() => {
    params.then((p) => {
      setId(p.id);
      // Viewing a league makes it the current league for every tab (P4-W7).
      const n = Number(p.id);
      if (Number.isFinite(n) && n > 0) setLeagueId(n);
    });
  }, [params, setLeagueId]);

  function refresh() {
    if (!id) return;
    api
      .getLeague(id)
      .then(setLeague)
      .catch((e) => setErr(e instanceof ApiError ? e.message : "load failed"));
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  if (err) return <div className="pt-8"><ErrorBox message={err} /></div>;
  if (!league)
    return (
      <div className="space-y-3 pt-8" aria-label="Loading">
        {[0, 1, 2].map((i) => (
          <div key={i} className="h-14 animate-pulse rounded-xl bg-midnight-soft" />
        ))}
      </div>
    );

  const playoffTeams = league.settings.playoff_teams || 4;

  return (
    <div>
      <PageHeader
        title={league.name}
        sub={`Season ${league.season} · invite code ${league.invite_code} · ${league.status}`}
      />

      <div className="grid gap-5 lg:grid-cols-3">
        {/* Standings */}
        <section className="overflow-hidden rounded-xl border border-slate-800 bg-midnight-soft lg:col-span-2">
          <h2 className="flex items-center gap-2 border-b border-slate-800 px-5 py-4 text-sm font-bold uppercase tracking-wider text-zinc-300">
            <Trophy className="h-4 w-4 text-trophy-gold" /> Standings
          </h2>
          {/* Desktop */}
          <table className="hidden w-full text-sm sm:table">
            <thead>
              <tr className="text-left text-[11px] uppercase tracking-wider text-zinc-500">
                <th className="px-5 py-2.5 font-semibold">#</th>
                <th className="px-2 py-2.5 font-semibold">Team</th>
                <th className="hidden px-2 py-2.5 font-semibold md:table-cell">Manager</th>
                <th className="px-2 py-2.5 text-center font-semibold">W–L</th>
                <th className="px-2 py-2.5 text-right font-semibold">PF</th>
                <th className="px-5 py-2.5 text-right font-semibold">FAAB</th>
              </tr>
            </thead>
            <tbody>
              {league.standings.map((s, i) => (
                <tr
                  key={s.team_id}
                  className={cn(
                    "border-t border-slate-800/60 transition hover:bg-slate-800/30",
                    i === playoffTeams && "border-t-2 border-t-trophy-gold/40",
                  )}
                >
                  <td className="px-5 py-3">
                    <span className={cn(
                      "flex h-6 w-6 items-center justify-center rounded-md text-[11px] font-extrabold",
                      i < playoffTeams ? "bg-trophy-gold/15 text-trophy-gold" : "bg-slate-800 text-zinc-500",
                    )}>
                      {i + 1}
                    </span>
                  </td>
                  <td className="px-2 py-3 font-semibold text-white">{s.team_name}</td>
                  <td className="hidden px-2 py-3 text-zinc-400 md:table-cell">{s.owner_name ?? "—"}</td>
                  <td className="px-2 py-3 text-center tabular-nums">
                    <span className="font-semibold text-pitch-green">{s.wins}</span>
                    <span className="text-zinc-600">–</span>
                    <span className="font-semibold text-brick-red">{s.losses}</span>
                    {s.ties > 0 && <span className="text-zinc-500">–{s.ties}</span>}
                  </td>
                  <td className="px-2 py-3 text-right tabular-nums text-zinc-300">{s.points_for.toFixed(1)}</td>
                  <td className="px-5 py-3 text-right tabular-nums font-semibold text-trophy-gold">${s.faab_remaining}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {/* Mobile cards */}
          <ul className="divide-y divide-slate-800/60 sm:hidden">
            {league.standings.map((s, i) => (
              <li key={s.team_id} className="flex items-center gap-3 px-4 py-3">
                <span className={cn(
                  "flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-xs font-extrabold",
                  i < playoffTeams ? "bg-trophy-gold/15 text-trophy-gold" : "bg-slate-800 text-zinc-500",
                )}>
                  {i + 1}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-semibold text-white">{s.team_name}</p>
                  <p className="text-[11px] tabular-nums text-zinc-500">
                    <span className="text-pitch-green">{s.wins}W</span>–<span className="text-brick-red">{s.losses}L</span>
                    {" · "}{s.points_for.toFixed(0)} PF
                  </p>
                </div>
                <span className="shrink-0 text-sm font-bold tabular-nums text-trophy-gold">${s.faab_remaining}</span>
              </li>
            ))}
          </ul>
          <p className="border-t border-slate-800 px-5 py-3 text-[11px] text-zinc-600">
            <Crown className="mr-1 inline h-3 w-3 text-trophy-gold/70" />
            Top {playoffTeams} make the fantasy playoffs (weeks 7–8).
          </p>
        </section>

        {/* Side column */}
        <div className="space-y-4">
          <section className="rounded-xl border border-slate-800 bg-midnight-soft p-5">
            <h2 className="mb-3 flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-zinc-300">
              <Settings2 className="h-4 w-4 text-zinc-500" /> League settings
            </h2>
            <dl className="space-y-2 text-sm">
              {[
                ["Draft", `${league.settings.draft_type} · ${league.settings.rounds} rounds`],
                ["Scoring", league.settings.scoring_table_version],
                ["Overseas cap", `${league.settings.overseas_cap} starters`],
                ["FAAB budget", `$${league.settings.faab_budget}`],
                ["Playoffs", `Top ${league.settings.playoff_teams} · weeks 7–8`],
                ["Trade deadline", `End of week ${league.settings.trade_deadline_week}`],
              ].map(([k, v]) => (
                <div key={k} className="flex items-baseline justify-between gap-4">
                  <dt className="shrink-0 text-zinc-500">{k}</dt>
                  <dd className="text-right font-medium text-zinc-200">{v}</dd>
                </div>
              ))}
            </dl>
          </section>
          <Link
            href={`/draft-room/${league.id}`}
            className="group flex items-center justify-center gap-2 rounded-xl bg-trophy-gold p-5 text-center text-sm font-bold text-midnight transition hover:brightness-110"
          >
            Enter draft room
            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
          </Link>
        </div>
      </div>

      <CommissionerTools league={league} onChanged={refresh} />
    </div>
  );
}

const WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"];

/** Commissioner tools (P4-W15): settings edit + audited FAAB adjustments.
 *  Ungated until team identity lands (P4-W18) — every change is written
 *  to the league's audit log below. */
function CommissionerTools({
  league,
  onChanged,
}: {
  league: LeagueDetailOut;
  onChanged: () => void;
}) {
  const [clock, setClock] = useState(String(league.settings.pick_clock_secs ?? 90));
  const [deadline, setDeadline] = useState(String(league.settings.trade_deadline_week ?? 6));
  const [weekday, setWeekday] = useState(String(league.settings.waiver_run_weekday ?? "wednesday"));
  const [adjTeam, setAdjTeam] = useState("");
  const [adjDelta, setAdjDelta] = useState("");
  const [adjNote, setAdjNote] = useState("");
  const [adjustments, setAdjustments] = useState<AdjustmentOut[]>([]);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.listAdjustments(league.id).then(setAdjustments).catch(() => {});
  }, [league.id]);

  const input =
    "rounded-lg border border-slate-700 bg-midnight px-3 py-2 text-sm text-white placeholder:text-zinc-600 focus:border-trophy-gold focus:outline-none";

  async function saveSettings(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    setMsg("");
    setBusy(true);
    try {
      await api.patchLeagueSettings(league.id, {
        pick_clock_secs: Number(clock),
        trade_deadline_week: Number(deadline),
        waiver_run_weekday: weekday,
      });
      setMsg("Settings saved.");
      onChanged();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "settings save failed");
    } finally {
      setBusy(false);
    }
  }

  async function submitAdjustment(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    setMsg("");
    const teamId = Number(adjTeam || league.standings[0]?.team_id);
    const delta = Number(adjDelta);
    if (!teamId || !Number.isFinite(delta) || adjNote.trim() === "") {
      setErr("Pick a team, a FAAB delta, and an audit note.");
      return;
    }
    setBusy(true);
    try {
      const adj = await api.createAdjustment(league.id, {
        team_id: teamId,
        faab_delta: delta,
        note: adjNote.trim(),
      });
      setAdjustments((prev) => [adj, ...prev]);
      setAdjDelta("");
      setAdjNote("");
      setMsg(`FAAB adjusted — ${adj.team_name} now has $${adj.faab_after}.`);
      onChanged();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "adjustment failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="mt-6 rounded-xl border border-slate-800 bg-midnight-soft p-5">
      <h2 className="mb-1 flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-zinc-300">
        <Settings2 className="h-4 w-4 text-zinc-500" /> Commissioner tools
      </h2>
      <p className="mb-4 text-xs text-zinc-500">
        Settings edits and manual FAAB adjustments. Every adjustment is written to the audit
        log with its note.
      </p>
      {err && (
        <div className="mb-3">
          <ErrorBox message={err} />
        </div>
      )}
      {msg && <p className="mb-3 text-sm text-pitch-green">{msg}</p>}

      <div className="grid gap-6 lg:grid-cols-2">
        <form onSubmit={saveSettings} className="space-y-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-400">League settings</h3>
          <label className="block text-xs text-zinc-500">
            Pick clock (seconds, applies to future drafts)
            <input type="number" min={0} max={600} className={cn(input, "mt-1 w-full")} value={clock} onChange={(e) => setClock(e.target.value)} />
          </label>
          <label className="block text-xs text-zinc-500">
            Trade deadline (end of week)
            <input type="number" min={1} max={8} className={cn(input, "mt-1 w-full")} value={deadline} onChange={(e) => setDeadline(e.target.value)} />
          </label>
          <label className="block text-xs text-zinc-500">
            Waiver run day
            <select className={cn(input, "mt-1 w-full")} value={weekday} onChange={(e) => setWeekday(e.target.value)}>
              {WEEKDAYS.map((d) => (
                <option key={d} value={d}>
                  {d[0].toUpperCase() + d.slice(1)}
                </option>
              ))}
            </select>
          </label>
          <button type="submit" disabled={busy} className="rounded-lg bg-trophy-gold px-4 py-2 text-sm font-bold text-midnight transition hover:brightness-110 disabled:opacity-50">
            Save settings
          </button>
        </form>

        <form onSubmit={submitAdjustment} className="space-y-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-400">FAAB adjustment</h3>
          <label className="block text-xs text-zinc-500">
            Team
            <select className={cn(input, "mt-1 w-full")} value={adjTeam} onChange={(e) => setAdjTeam(e.target.value)}>
              {league.standings.map((s) => (
                <option key={s.team_id} value={s.team_id}>
                  {s.team_name} (${s.faab_remaining})
                </option>
              ))}
            </select>
          </label>
          <label className="block text-xs text-zinc-500">
            Delta (e.g. 10 to grant, -5 to dock)
            <input type="number" className={cn(input, "mt-1 w-full")} value={adjDelta} onChange={(e) => setAdjDelta(e.target.value)} placeholder="0" />
          </label>
          <label className="block text-xs text-zinc-500">
            Audit note (required)
            <input className={cn(input, "mt-1 w-full")} value={adjNote} onChange={(e) => setAdjNote(e.target.value)} placeholder="Why is this being adjusted?" maxLength={200} />
          </label>
          <button type="submit" disabled={busy} className="rounded-lg bg-slate-800 px-4 py-2 text-sm font-bold text-white transition hover:bg-slate-700 disabled:opacity-50">
            Apply adjustment
          </button>
        </form>
      </div>

      {adjustments.length > 0 && (
        <div className="mt-6">
          <h3 className="mb-2 text-xs font-bold uppercase tracking-wider text-zinc-400">Audit log</h3>
          <ul className="space-y-1.5 text-sm">
            {adjustments.map((a) => (
              <li key={a.id} className="flex flex-wrap items-baseline gap-x-3 rounded-lg bg-slate-800/50 px-3 py-2">
                <span className="font-semibold text-white">{a.team_name}</span>
                <span className={a.faab_delta >= 0 ? "text-pitch-green" : "text-brick-red"}>
                  {a.faab_delta >= 0 ? "+" : ""}${a.faab_delta} → ${a.faab_after}
                </span>
                <span className="text-zinc-400">{a.note}</span>
                <span className="ml-auto text-xs text-zinc-600">{a.created_at}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
