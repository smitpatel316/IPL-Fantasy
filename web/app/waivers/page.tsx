"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ApiError, type TeamOut, type WaiverClaimOut } from "@/lib/types";
import { PageHeader, ErrorBox, EngineStub } from "@/components/ui";

export default function WaiversPage() {
  const [teams, setTeams] = useState<TeamOut[]>([]);
  const [claims, setClaims] = useState<WaiverClaimOut[]>([]);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.listTeams(1).then(setTeams).catch(() => {});
    api.pendingClaims(1, 1).then(setClaims).catch((e) => {
      if (!(e instanceof ApiError && e.status === 501)) setErr(e instanceof ApiError ? e.message : "load failed");
    });
  }, []);

  return (
    <div>
      <PageHeader title="Waivers" sub="Weekly blind FAAB · $100 season budget · runs Wednesday ~3am PT (D6)" />
      {err && <div className="mb-4"><ErrorBox message={err} /></div>}

      <div className="mb-6 rounded-xl border border-slate-800 bg-midnight-soft p-5">
        <h2 className="mb-3 font-semibold text-white">FAAB remaining</h2>
        <div className="flex flex-wrap gap-2">
          {teams.map((t) => (
            <span key={t.id} className="rounded-md bg-slate-800 px-3 py-1.5 text-sm">
              <span className="text-slate-300">{t.name}</span>{" "}
              <span className="font-semibold text-trophy-gold">${t.faab_remaining}</span>
            </span>
          ))}
        </div>
      </div>

      <h2 className="mb-2 font-semibold text-white">This week's claims</h2>
      {claims.length === 0 ? (
        <EngineStub track="P2-L3" what="Waiver claims (blind bids, reverse-standings tiebreak)" />
      ) : (
        <ul className="space-y-1">
          {claims.map((c) => (
            <li key={c.id} className="rounded-md border border-slate-800/60 px-3 py-2 text-sm text-slate-300">
              Team {c.team_id} bids ${c.bid} for player {c.add_player_id}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
