"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useLeague } from "@/lib/league-context";
import { ApiError, type PlayerDetailOut, type TeamOut } from "@/lib/types";
import { PageHeader, ErrorBox } from "@/components/ui";
import { AvailabilityDot, AVAILABILITY_META } from "@/components/AvailabilityDot";
import { cn } from "@/lib/utils";
import { ArrowLeft, Lock, Plane, StickyNote } from "lucide-react";

/**
 * P5-W17: private note editor. Notes belong to ONE team and are gated
 * server-side by that team's claim code — a claimed team's notes 403
 * for everyone else, and this section says so honestly instead of
 * pretending the note is empty.
 */
function NoteEditor({ leagueId, playerId }: { leagueId: number; playerId: number }) {
  const [teams, setTeams] = useState<TeamOut[]>([]);
  const [teamId, setTeamId] = useState<number | null>(null);
  const [draft, setDraft] = useState("");
  const [saved, setSaved] = useState<string | null>(null);
  const [denied, setDenied] = useState(false);
  const [noteErr, setNoteErr] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api
      .listTeams(leagueId)
      .then((ts) => {
        setTeams(ts);
        setTeamId((prev) => prev ?? ts[0]?.id ?? null);
      })
      .catch(() => {});
  }, [leagueId]);

  useEffect(() => {
    if (teamId == null) return;
    setDenied(false);
    setNoteErr("");
    api
      .listPlayerNotes(leagueId, teamId)
      .then((notes) => {
        const mine = notes.find((n) => n.player_id === playerId);
        setSaved(mine?.note ?? null);
        setDraft(mine?.note ?? "");
      })
      .catch((e) => {
        if (e instanceof ApiError && e.status === 403) setDenied(true);
        setSaved(null);
        setDraft("");
      });
  }, [leagueId, teamId, playerId]);

  async function save() {
    if (teamId == null) return;
    setBusy(true);
    setNoteErr("");
    try {
      const out = await api.putPlayerNote({
        league_id: leagueId, team_id: teamId, player_id: playerId, note: draft,
      });
      setSaved(out.note);
      setDraft(out.note);
    } catch (e) {
      setNoteErr(e instanceof ApiError ? e.message : "save failed");
    } finally {
      setBusy(false);
    }
  }

  async function clear() {
    if (teamId == null) return;
    setBusy(true);
    setNoteErr("");
    try {
      await api.deletePlayerNote(leagueId, teamId, playerId);
      setSaved(null);
      setDraft("");
    } catch (e) {
      setNoteErr(e instanceof ApiError ? e.message : "delete failed");
    } finally {
      setBusy(false);
    }
  }

  const input =
    "rounded-lg border border-slate-700 bg-ink-950 px-3 py-2 text-sm text-white placeholder:text-zinc-600 focus:border-trophy-gold focus:outline-none";

  return (
    <section className="mt-5 rounded-xl border border-slate-800 bg-midnight-soft p-5">
      <h2 className="mb-1 flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-zinc-300">
        <StickyNote className="h-4 w-4 text-gold-ink" /> My private note
      </h2>
      <p className="mb-3 text-xs text-zinc-500">
        Private to the selected team — no other manager can read it, and it never
        appears in the activity feed or on the message board.
      </p>
      <label className="mb-3 flex flex-wrap items-center gap-2 text-xs font-medium text-slate-400">
        Team
        <select
          className={input}
          value={teamId ?? ""}
          onChange={(e) => setTeamId(Number(e.target.value))}
        >
          {teams.map((t) => (
            <option key={t.id} value={t.id}>{t.name}</option>
          ))}
        </select>
      </label>
      {denied ? (
        <p className="flex items-start gap-2 rounded-lg border border-slate-800 bg-ink-950 px-3 py-2.5 text-sm text-zinc-400">
          <Lock className="mt-0.5 h-4 w-4 shrink-0 text-zinc-500" />
          This team is claimed by its manager — its notes are private and stay
          hidden here. Claim your own team (League page → standings) to keep
          notes on your players.
        </p>
      ) : (
        <>
          <textarea
            className={cn(input, "min-h-20 w-full")}
            maxLength={500}
            placeholder="e.g. injury watch — check the team news before round 8"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
          />
          {noteErr && <p className="mt-2 text-xs text-loss-ink">{noteErr}</p>}
          <div className="mt-3 flex items-center gap-2">
            <button
              type="button"
              onClick={save}
              disabled={busy || teamId == null || !draft.trim()}
              className="rounded-lg bg-trophy-gold px-4 py-2 text-sm font-bold text-midnight transition hover:brightness-110 disabled:opacity-50"
            >
              {busy ? "Saving…" : saved ? "Update note" : "Save note"}
            </button>
            {saved && (
              <button
                type="button"
                onClick={clear}
                disabled={busy}
                className="rounded-lg border border-slate-700 px-4 py-2 text-sm font-semibold text-zinc-300 transition hover:border-brick-red hover:text-white disabled:opacity-50"
              >
                Delete note
              </button>
            )}
            {saved && <span className="text-xs text-win-ink">Saved — only this team can see it.</span>}
          </div>
        </>
      )}
    </section>
  );
}

const ROLE_BADGE: Record<string, string> = {
  WK: "bg-yellow-400/10 text-yellow-300",
  BAT: "bg-blue-400/10 text-blue-300",
  AR: "bg-purple-400/10 text-purple-300",
  BOWL: "bg-emerald-400/10 text-emerald-300",
};

export default function PlayerDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { leagueId } = useLeague();
  const [id, setId] = useState<string | null>(null);
  const [player, setPlayer] = useState<PlayerDetailOut | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    params.then((p) => setId(p.id));
  }, [params]);

  useEffect(() => {
    if (!id) return;
    api
      .getPlayer(id, leagueId)
      .then(setPlayer)
      .catch((e) => setErr(e instanceof ApiError ? e.message : "load failed"));
  }, [id, leagueId]);

  if (err) return <div className="pt-8"><ErrorBox message={err} /></div>;
  if (!player)
    return (
      <div className="space-y-3 pt-8" aria-label="Loading">
        {[0, 1].map((i) => (
          <div key={i} className="h-24 animate-pulse rounded-xl bg-midnight-soft" />
        ))}
      </div>
    );

  return (
    <div>
      <Link href="/players" className="mb-4 inline-flex items-center gap-1.5 text-sm text-zinc-400 hover:text-white">
        <ArrowLeft className="h-4 w-4" /> All players
      </Link>
      <PageHeader
        title={player.name}
        sub={`${player.ipl_team_code ?? "—"} · season ${player.season}`}
      />

      <div className="grid gap-5 lg:grid-cols-3">
        <section className="rounded-xl border border-slate-800 bg-midnight-soft p-5">
          <h2 className="mb-3 text-sm font-bold uppercase tracking-wider text-zinc-300">Profile</h2>
          <dl className="space-y-2 text-sm">
            <div className="flex items-baseline justify-between gap-4">
              <dt className="text-zinc-500">Role</dt>
              <dd>
                {player.role ? (
                  <span className={cn("rounded px-1.5 py-0.5 text-xs font-bold", ROLE_BADGE[player.role])}>
                    {player.role}
                  </span>
                ) : (
                  "—"
                )}
              </dd>
            </div>
            <div className="flex items-baseline justify-between gap-4">
              <dt className="text-zinc-500">IPL team</dt>
              <dd className="font-medium text-zinc-200">{player.ipl_team_code ?? "—"}</dd>
            </div>
            <div className="flex items-baseline justify-between gap-4">
              <dt className="text-zinc-500">Overseas</dt>
              <dd className="font-medium text-zinc-200">
                {player.is_overseas ? (
                  <span className="inline-flex items-center gap-1"><Plane className="h-3.5 w-3.5" /> Yes</span>
                ) : (
                  "No"
                )}
              </dd>
            </div>
            <div className="flex items-baseline justify-between gap-4">
              <dt className="text-zinc-500">Preseason rank</dt>
              <dd className="font-medium text-zinc-200">{player.preseason_rank ?? "—"}</dd>
            </div>
            <div className="flex items-baseline justify-between gap-4">
              <dt className="text-zinc-500">Availability</dt>
              <dd className="inline-flex items-center gap-1.5 font-medium text-zinc-200">
                <AvailabilityDot availability={player.availability} />
                {AVAILABILITY_META[player.availability].label}
              </dd>
            </div>
            <div className="flex items-baseline justify-between gap-4">
              <dt className="text-zinc-500">Ownership</dt>
              <dd className="font-medium text-zinc-200">
                {player.ownership_pct != null ? `${player.ownership_pct.toFixed(0)}% of leagues` : "—"}
              </dd>
            </div>
            <div className="flex items-baseline justify-between gap-4">
              <dt className="text-zinc-500">Avg points</dt>
              <dd className="font-medium text-zinc-200">
                {player.avg_points != null ? player.avg_points.toFixed(1) : "—"}
              </dd>
            </div>
          </dl>
        </section>

        <section className="rounded-xl border border-slate-800 bg-midnight-soft p-5">
          <h2 className="mb-3 text-sm font-bold uppercase tracking-wider text-zinc-300">Owned by</h2>
          {player.owners.length === 0 ? (
            <p className="text-sm text-win-ink">Free agent in every league.</p>
          ) : (
            <ul className="space-y-2 text-sm">
              {player.owners.map((o) => (
                <li key={`${o.league_id}-${o.team_id}`} className="flex items-baseline justify-between gap-4">
                  <span className="text-zinc-400">{o.league_name}</span>
                  <Link href={`/league/${o.league_id}`} className="font-medium text-zinc-100 hover:text-gold-ink">
                    {o.team_name}
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="rounded-xl border border-slate-800 bg-midnight-soft p-5">
          <h2 className="mb-3 text-sm font-bold uppercase tracking-wider text-zinc-300">Match log</h2>
          {player.match_log.length === 0 ? (
            <p className="text-sm text-zinc-500">
              No scored matches yet — match-by-match points land with the season scoring pipeline.
            </p>
          ) : (
            <>
              <p className="mb-3 text-sm text-zinc-400">
                {player.matches_played} matches · {player.total_points} total points
              </p>
              <ul className="space-y-1.5 text-sm">
                {player.match_log.map((m) => (
                  <li key={m.match_id} className="flex items-baseline justify-between gap-3">
                    <span className="text-zinc-400">
                      {m.home_code ?? "?"} v {m.away_code ?? "?"}
                      <span className="ml-2 text-[11px] text-zinc-600">
                        {m.week_no ? `Wk ${m.week_no} · ` : ""}{m.match_date_ist ?? ""}
                      </span>
                    </span>
                    <span className="font-semibold tabular-nums text-white">{m.fantasy_points}</span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </section>
      </div>

      <NoteEditor leagueId={leagueId} playerId={player.id} />
    </div>
  );
}
