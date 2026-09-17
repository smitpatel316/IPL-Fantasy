"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { ApiError, type PlayerOut, type TeamOut, type TradeOut } from "@/lib/types";
import { PageHeader, ErrorBox } from "@/components/ui";
import { cn } from "@/lib/utils";
import { ArrowLeftRight, ArrowRight, Clock, Plus } from "lucide-react";

const STATUS_STYLE: Record<string, string> = {
  pending: "bg-trophy-gold/15 text-trophy-gold",
  proposed: "bg-trophy-gold/15 text-trophy-gold",
  accepted: "bg-pitch-green/15 text-pitch-green",
  executed: "bg-pitch-green/15 text-pitch-green",
  rejected: "bg-brick-red/15 text-brick-red",
  vetoed: "bg-brick-red/15 text-brick-red",
};

const input =
  "rounded-md border border-slate-700 bg-midnight px-3 py-2 text-sm text-white placeholder:text-slate-500 focus:border-ipl-blue-bright focus:outline-none";
const btnPrimary =
  "rounded-md bg-ipl-blue px-4 py-2 text-sm font-semibold text-white hover:bg-ipl-blue-bright disabled:opacity-40 disabled:cursor-not-allowed";
const btnGhost =
  "rounded-md border border-slate-700 px-4 py-2 text-sm text-slate-300 hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed";
const btnDanger =
  "rounded-md border border-brick-red/50 px-3 py-1.5 text-xs font-semibold text-brick-red hover:bg-brick-red/10 disabled:opacity-40 disabled:cursor-not-allowed";

function PlayerChips({ ids, names }: { ids: number[]; names: Map<number, string> }) {
  if (ids.length === 0) return <span className="text-xs text-zinc-600">—</span>;
  return (
    <div className="flex flex-wrap gap-1.5">
      {ids.map((id) => (
        <span
          key={id}
          className="rounded-lg border border-slate-700 bg-slate-800/60 px-2.5 py-1 text-xs font-medium text-zinc-100"
        >
          {names.get(id) ?? `Player #${id}`}
        </span>
      ))}
    </div>
  );
}

function TradeCard({
  trade,
  teamName,
  playerName,
  managingAs,
  onAction,
  busy,
}: {
  trade: TradeOut;
  teamName: Map<number, string>;
  playerName: Map<number, string>;
  managingAs: number | null;
  onAction: (action: "accept" | "reject" | "veto") => void;
  busy: boolean;
}) {
  const isOfferee = managingAs != null && trade.status === "proposed" && trade.to_team_id === managingAs;
  const isParty = managingAs != null && (trade.from_team_id === managingAs || trade.to_team_id === managingAs);
  const canVeto = managingAs != null && trade.status === "accepted" && !isParty;
  return (
    <li className="rounded-xl border border-slate-800 bg-midnight-soft p-4 sm:p-5">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <span className="inline-flex items-center gap-1.5 text-sm font-semibold text-white">
          <ArrowLeftRight className="h-4 w-4 text-trophy-gold" />
          {teamName.get(trade.from_team_id) ?? `Team ${trade.from_team_id}`}
        </span>
        <ArrowRight className="h-3.5 w-3.5 text-zinc-600" />
        <span className="text-sm font-semibold text-white">
          {teamName.get(trade.to_team_id) ?? `Team ${trade.to_team_id}`}
        </span>
        <span className={cn("ml-auto rounded px-1.5 py-0.5 text-[11px] font-bold uppercase", STATUS_STYLE[trade.status] ?? "bg-slate-800 text-zinc-400")}>
          {trade.status}
        </span>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-zinc-500">
            {teamName.get(trade.from_team_id) ?? `Team ${trade.from_team_id}`} gives
          </p>
          <PlayerChips ids={trade.gives} names={playerName} />
        </div>
        <div>
          <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-zinc-500">
            {teamName.get(trade.to_team_id) ?? `Team ${trade.to_team_id}`} gives
          </p>
          <PlayerChips ids={trade.receives} names={playerName} />
        </div>
      </div>
      {trade.review_deadline && trade.status === "accepted" && (
        <p className="mt-3 flex items-center gap-1.5 text-xs text-zinc-500">
          <Clock className="h-3.5 w-3.5" /> Commissioner review until {trade.review_deadline}
        </p>
      )}
      <div className="mt-3 flex flex-wrap gap-2">
        {isOfferee && (
          <>
            <button className={btnPrimary} onClick={() => onAction("accept")} disabled={busy}>
              Accept
            </button>
            <button className={btnGhost} onClick={() => onAction("reject")} disabled={busy}>
              Reject
            </button>
          </>
        )}
        {canVeto && (
          <button className={btnDanger} onClick={() => onAction("veto")} disabled={busy} title="Veto during the 2-day review window (one-third of non-party teams)">
            Veto trade
          </button>
        )}
      </div>
    </li>
  );
}

export default function TradesPage() {
  const [trades, setTrades] = useState<TradeOut[]>([]);
  const [teams, setTeams] = useState<TeamOut[]>([]);
  const [players, setPlayers] = useState<PlayerOut[]>([]);
  const [teamId, setTeamId] = useState<number | null>(null);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  // propose modal state
  const [proposeOpen, setProposeOpen] = useState(false);
  const [partnerId, setPartnerId] = useState("");
  const [gives, setGives] = useState<number[]>([]);
  const [receives, setReceives] = useState<number[]>([]);
  const [propErr, setPropErr] = useState("");
  const [propOk, setPropOk] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [busyAction, setBusyAction] = useState(false);
  const [actionErr, setActionErr] = useState("");

  async function load() {
    setLoading(true);
    setErr("");
    try {
      const [ts, ps, trs] = await Promise.all([
        api.listTeams(1),
        api.listPlayers({ league_id: 1 }),
        api.listTrades(1),
      ]);
      setTeams(ts);
      setPlayers(ps);
      setTrades(trs);
      if (teamId == null && ts.length > 0) setTeamId(ts[0].id);
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

  const teamName = useMemo(() => new Map(teams.map((t) => [t.id, t.name])), [teams]);
  const playerName = useMemo(() => new Map(players.map((p) => [p.id, p.name])), [players]);
  const myRoster = useMemo(() => players.filter((p) => p.owned_by_team_id === teamId), [players, teamId]);
  const partnerRoster = useMemo(
    () => players.filter((p) => partnerId !== "" && p.owned_by_team_id === Number(partnerId)),
    [players, partnerId]
  );
  const proposed = trades.filter((t) => t.status === "proposed");
  const history = trades.filter((t) => t.status !== "proposed");

  function toggle(setter: React.Dispatch<React.SetStateAction<number[]>>, id: number) {
    setter((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  function openPropose() {
    setProposeOpen(true);
    setPropErr("");
    setPropOk("");
    setGives([]);
    setReceives([]);
    const first = teams.find((t) => t.id !== teamId);
    setPartnerId(first ? String(first.id) : "");
  }

  async function submitPropose() {
    if (teamId == null) return;
    setPropErr("");
    setPropOk("");
    if (partnerId === "") {
      setPropErr("Pick a trade partner.");
      return;
    }
    if (gives.length === 0 || receives.length === 0) {
      setPropErr("Pick at least one player on each side.");
      return;
    }
    if (gives.length !== receives.length) {
      setPropErr("Trades must be N-for-N — same number of players each side.");
      return;
    }
    setSubmitting(true);
    try {
      const t = await api.proposeTrade({
        league_id: 1,
        from_team_id: teamId,
        to_team_id: Number(partnerId),
        gives,
        receives,
      });
      setPropOk(`Trade proposed to ${teamName.get(t.to_team_id) ?? "them"} — they have 3 days to accept or reject it.`);
      setProposeOpen(false);
      await load();
    } catch (e) {
      setPropErr(e instanceof ApiError ? e.message : "propose failed");
    } finally {
      setSubmitting(false);
    }
  }

  async function doAction(trade: TradeOut, action: "accept" | "reject" | "veto") {
    setActionErr("");
    setBusyAction(true);
    try {
      if (action === "accept") await api.tradeAccept(trade.id);
      else if (action === "reject") await api.tradeReject(trade.id);
      else await api.tradeVeto(trade.id, teamId!);
      await load();
    } catch (e) {
      setActionErr(e instanceof ApiError ? e.message : "action failed");
    } finally {
      setBusyAction(false);
    }
  }

  return (
    <div>
      <PageHeader
        title="Trades"
        sub="Propose · accept / reject · commissioner review (2-day window) · deadline end of week 6"
      />
      {err && <div className="mb-4"><ErrorBox message={err} onRetry={load} /></div>}
      {actionErr && <div className="mb-4"><ErrorBox message={actionErr} /></div>}

      <div className="mb-6 flex flex-wrap items-center gap-3">
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-400">Managing as</label>
          <select className={input} value={teamId ?? ""} onChange={(e) => setTeamId(Number(e.target.value))}>
            {teams.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
        </div>
        <button className={cn(btnPrimary, "ml-auto inline-flex items-center gap-1.5")} onClick={openPropose} disabled={loading}>
          <Plus className="h-4 w-4" /> Propose trade
        </button>
      </div>

      <h2 className="mb-3 text-sm font-bold uppercase tracking-wider text-zinc-300">Trade inbox</h2>
      {trades.length === 0 ? (
        <p className="text-sm text-slate-500">No trades yet — propose one to get things moving.</p>
      ) : (
        <>
          {proposed.length > 0 && (
            <ul className="mb-6 space-y-3">
              {proposed.map((t) => (
                <TradeCard
                  key={t.id}
                  trade={t}
                  teamName={teamName}
                  playerName={playerName}
                  managingAs={teamId}
                  busy={busyAction}
                  onAction={(a) => doAction(t, a)}
                />
              ))}
            </ul>
          )}
          {history.length > 0 && (
            <>
              <h2 className="mb-3 text-sm font-bold uppercase tracking-wider text-zinc-300">History</h2>
              <ul className="space-y-3">
                {history.map((t) => (
                  <TradeCard
                    key={t.id}
                    trade={t}
                    teamName={teamName}
                    playerName={playerName}
                    managingAs={teamId}
                    busy={busyAction}
                    onAction={(a) => doAction(t, a)}
                  />
                ))}
              </ul>
            </>
          )}
        </>
      )}

      {proposeOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={() => setProposeOpen(false)}>
          <div
            className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-xl border border-slate-700 bg-midnight-soft p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-lg font-semibold text-white">Propose trade</h3>
            <p className="mt-1 text-sm text-slate-400">
              N-for-N only · the other manager accepts or rejects · accepted trades face a 2-day review window (veto by one-third of the league)
            </p>
            <div className="mt-4">
              <label className="mb-1 block text-xs font-medium text-slate-400">Trade with</label>
              <select
                className={cn(input, "w-full")}
                value={partnerId}
                onChange={(e) => {
                  setPartnerId(e.target.value);
                  setReceives([]);
                }}
              >
                {teams
                  .filter((t) => t.id !== teamId)
                  .map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name}
                    </option>
                  ))}
              </select>
            </div>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <div>
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-zinc-400">You give ({gives.length})</p>
                <div className="max-h-64 space-y-1 overflow-y-auto rounded-lg border border-slate-800 p-2">
                  {myRoster.length === 0 && <p className="p-2 text-xs text-zinc-600">Your roster is empty.</p>}
                  {myRoster.map((p) => (
                    <label key={p.id} className="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-slate-800/60">
                      <input
                        type="checkbox"
                        className="accent-trophy-gold"
                        checked={gives.includes(p.id)}
                        onChange={() => toggle(setGives, p.id)}
                      />
                      <span className="text-zinc-200">{p.name}</span>
                      <span className="ml-auto text-xs text-zinc-500">{p.role ?? ""} {p.ipl_team_code ?? ""}</span>
                    </label>
                  ))}
                </div>
              </div>
              <div>
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-zinc-400">You get ({receives.length})</p>
                <div className="max-h-64 space-y-1 overflow-y-auto rounded-lg border border-slate-800 p-2">
                  {partnerRoster.length === 0 && <p className="p-2 text-xs text-zinc-600">Their roster is empty.</p>}
                  {partnerRoster.map((p) => (
                    <label key={p.id} className="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-slate-800/60">
                      <input
                        type="checkbox"
                        className="accent-trophy-gold"
                        checked={receives.includes(p.id)}
                        onChange={() => toggle(setReceives, p.id)}
                      />
                      <span className="text-zinc-200">{p.name}</span>
                      <span className="ml-auto text-xs text-zinc-500">{p.role ?? ""} {p.ipl_team_code ?? ""}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>
            {propErr && (
              <div className="mt-3">
                <ErrorBox message={propErr} />
              </div>
            )}
            {propOk && <p className="mt-3 text-sm text-green-300">{propOk}</p>}
            <div className="mt-5 flex justify-end gap-2">
              <button className={btnGhost} onClick={() => setProposeOpen(false)} disabled={submitting}>
                Cancel
              </button>
              <button className={btnPrimary} onClick={submitPropose} disabled={submitting}>
                {submitting ? "Sending…" : "Send proposal"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
