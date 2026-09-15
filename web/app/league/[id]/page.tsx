"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { ApiError, type LeagueDetailOut } from "@/lib/types";
import { PageHeader, ErrorBox } from "@/components/ui";

export default function LeaguePage({ params }: { params: Promise<{ id: string }> }) {
  const [id, setId] = useState<string | null>(null);
  const [league, setLeague] = useState<LeagueDetailOut | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    params.then((p) => setId(p.id));
  }, [params]);

  useEffect(() => {
    if (!id) return;
    api
      .getLeague(id)
      .then(setLeague)
      .catch((e) => setErr(e instanceof ApiError ? e.message : "load failed"));
  }, [id]);

  if (err) return <div className="pt-8"><ErrorBox message={err} /></div>;
  if (!league) return <p className="pt-8 text-sm text-slate-500">Loading league…</p>;

  return (
    <div>
      <PageHeader
        title={league.name}
        sub={`Season ${league.season} · Invite code ${league.invite_code} · ${league.status}`}
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 rounded-xl border border-slate-800 bg-midnight-soft p-5">
          <h2 className="mb-3 font-semibold text-white">Standings</h2>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase text-slate-500">
                <th className="py-2">Team</th>
                <th className="py-2">Manager</th>
                <th className="py-2 text-right">W</th>
                <th className="py-2 text-right">L</th>
                <th className="py-2 text-right">T</th>
                <th className="py-2 text-right">PF</th>
                <th className="py-2 text-right">FAAB</th>
              </tr>
            </thead>
            <tbody>
              {league.standings.map((s) => (
                <tr key={s.team_id} className="border-t border-slate-800/60">
                  <td className="py-2 font-medium text-white">{s.team_name}</td>
                  <td className="py-2 text-slate-400">{s.owner_name}</td>
                  <td className="py-2 text-right text-pitch-green">{s.wins}</td>
                  <td className="py-2 text-right text-brick-red">{s.losses}</td>
                  <td className="py-2 text-right text-slate-400">{s.ties}</td>
                  <td className="py-2 text-right text-slate-300">{s.points_for.toFixed(1)}</td>
                  <td className="py-2 text-right text-trophy-gold">${s.faab_remaining}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="space-y-4">
          <div className="rounded-xl border border-slate-800 bg-midnight-soft p-5">
            <h2 className="mb-2 font-semibold text-white">League settings</h2>
            <dl className="space-y-1 text-sm">
              {[
                ["Draft", `${league.settings.draft_type} · ${league.settings.rounds} rounds`],
                ["Scoring", league.settings.scoring_table_version],
                ["Overseas cap", `${league.settings.overseas_cap} starters`],
                ["FAAB budget", `$${league.settings.faab_budget}`],
                ["Playoffs", `Top ${league.settings.playoff_teams} · weeks 7–8`],
                ["Trade deadline", `End of week ${league.settings.trade_deadline_week}`],
              ].map(([k, v]) => (
                <div key={k} className="flex justify-between gap-4">
                  <dt className="text-slate-500">{k}</dt>
                  <dd className="text-right text-slate-200">{v}</dd>
                </div>
              ))}
            </dl>
          </div>
          <Link
            href={`/draft-room/${league.id}`}
            className="block rounded-xl border border-trophy-gold/30 bg-trophy-gold/10 p-5 text-center text-sm font-semibold text-trophy-gold hover:bg-trophy-gold/20"
          >
            Enter draft room →
          </Link>
        </div>
      </div>
    </div>
  );
}
