"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ApiError, type TradeOut } from "@/lib/types";
import { PageHeader, ErrorBox, EngineStub } from "@/components/ui";

export default function TradesPage() {
  const [trades, setTrades] = useState<TradeOut[]>([]);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.listTrades(1).then(setTrades).catch((e) => setErr(e instanceof ApiError ? e.message : "load failed"));
  }, []);

  return (
    <div>
      <PageHeader title="Trades" sub="Propose · accept/reject · commissioner review (2-day window) · deadline end of week 6 (D4)" />
      {err && <div className="mb-4"><ErrorBox message={err} /></div>}
      <h2 className="mb-2 font-semibold text-white">Trade inbox</h2>
      {trades.length === 0 ? (
        <EngineStub track="P2-L4" what="Trade engine (proposals, legality checks, veto)" />
      ) : (
        <ul className="space-y-1">
          {trades.map((t) => (
            <li key={t.id} className="rounded-md border border-slate-800/60 px-3 py-2 text-sm text-slate-300">
              Team {t.from_team_id} → Team {t.to_team_id} · {t.status}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
