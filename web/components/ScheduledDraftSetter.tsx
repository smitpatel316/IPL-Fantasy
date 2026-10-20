"use client";

/* P5-W53: commissioner "Scheduled draft" datetime control. It lives on
   the league page beside the DraftCountdown until the P5-W50 settings
   editor merges — then it should be folded into the settings form.

   Commissioner-gated with the P5-W50 pattern (commissioner_team_id +
   getTeamClaim from localStorage); the server 403s non-commissioners
   anyway (P5-W51). Writes PATCH /api/leagues/{id}/settings with
   draft_scheduled_at + team_id/claim headers via lib/api
   patchLeagueSettings (P5-W51's convention): an ISO 8601 instant
   carrying the browser's timezone offset (the backend normalizes to
   UTC and 422s naive/garbled input — surfaced as an inline error),
   and "" to clear the schedule. */

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/types";
import { CalendarClock } from "lucide-react";

const pad = (n: number) => String(n).padStart(2, "0");

/** datetime-local value -> ISO 8601 instant carrying the browser's own
    timezone offset, e.g. "2027-03-01T14:00" -> "2027-03-01T14:00-05:00".
    null when the value doesn't look like a datetime-local. */
export function toOffsetIso(local: string): string | null {
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?$/.test(local)) return null;
  const d = new Date(local); // datetime-local is local wall time
  if (Number.isNaN(d.getTime())) return null;
  const offMin = -d.getTimezoneOffset();
  const sign = offMin >= 0 ? "+" : "-";
  const a = Math.abs(offMin);
  return `${local.slice(0, 16)}${sign}${pad(Math.floor(a / 60))}:${pad(a % 60)}`;
}

/** Stored UTC ISO instant -> datetime-local value for prefilling the
    input in the browser's timezone. */
export function toDatetimeLocal(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return (
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` +
    `T${pad(d.getHours())}:${pad(d.getMinutes())}`
  );
}

export function ScheduledDraftSetter({
  leagueId,
  leagueStatus,
  claimedTeams,
  onSaved,
}: {
  leagueId: number;
  leagueStatus: string;
  /** This browser's claimed team ids (P4-W18); refreshes on claim/release. */
  claimedTeams: Set<number>;
  /** Fires after a successful save/clear so the page can refresh the
      countdown off the new schedule. */
  onSaved: () => void;
}) {
  const [commissionerTeamId, setCommissionerTeamId] = useState<number | null>(null);
  const [value, setValue] = useState("");
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  // P5-W43 pattern: commissioner identity via the message board out.
  useEffect(() => {
    api
      .getMessageBoard(leagueId, 1)
      .then((b) => setCommissionerTeamId(b.commissioner_team_id))
      .catch(() => {});
  }, [leagueId]);

  // Prefill from the stored (UTC-normalized) instant, if any.
  useEffect(() => {
    api
      .getLeague(leagueId)
      .then((l) => {
        const at = l.settings.draft_scheduled_at;
        setValue(at ? toDatetimeLocal(at) : "");
      })
      .catch(() => {});
  }, [leagueId]);

  const canEdit =
    leagueStatus === "setup" &&
    commissionerTeamId != null &&
    claimedTeams.has(commissionerTeamId);
  if (!canEdit) return null;

  async function save(clear: boolean) {
    setErr("");
    setMsg("");
    let instant = "";
    if (!clear) {
      const iso = toOffsetIso(value);
      if (!iso) {
        setErr("Enter a valid date and time for the draft.");
        return;
      }
      instant = iso;
    }
    setBusy(true);
    try {
      // P5-W52 request shape: commissioner_team_id in the body + the
      // commissioner's claim header (server-gated); "" clears the schedule.
      const updated = await api.patchLeagueSettings(
        leagueId,
        commissionerTeamId!,
        { draft_scheduled_at: instant },
      );
      const stored = updated.settings.draft_scheduled_at;
      setValue(stored ? toDatetimeLocal(stored) : "");
      setMsg(
        clear
          ? "Draft schedule cleared."
          : "Draft scheduled — the countdown and the .ics feed use the new instant.",
      );
      onSaved();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "schedule save failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section
      aria-label="Schedule draft"
      className="rounded-xl border border-slate-800 bg-midnight-soft p-5"
    >
      <h2 className="mb-2 flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-zinc-300">
        <CalendarClock className="h-4 w-4 text-gold-ink" /> Schedule draft
      </h2>
      <p className="mb-3 text-xs text-zinc-500">
        Commissioner only — the countdown counts down to this instant. The
        date and time are entered in your browser&apos;s timezone.
      </p>
      <div className="flex flex-col gap-2">
        <input
          type="datetime-local"
          aria-label="Scheduled draft date and time"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white focus:border-trophy-gold focus:outline-none"
        />
        <div className="flex gap-2">
          <button
            type="button"
            disabled={busy}
            onClick={() => void save(false)}
            className="rounded-lg bg-trophy-gold px-4 py-2 text-sm font-bold text-midnight transition hover:brightness-110 disabled:opacity-50"
          >
            {busy ? "Saving…" : "Save schedule"}
          </button>
          <button
            type="button"
            disabled={busy || !value}
            onClick={() => void save(true)}
            className="rounded-lg border border-slate-700 px-4 py-2 text-sm font-semibold text-zinc-200 transition hover:border-trophy-gold hover:text-white disabled:opacity-50"
          >
            Clear
          </button>
        </div>
      </div>
      {err && (
        <p role="alert" className="mt-2 text-xs text-loss-ink">
          {err}
        </p>
      )}
      {msg && <p className="mt-2 text-xs text-win-ink">{msg}</p>}
    </section>
  );
}
