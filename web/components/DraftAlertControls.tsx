"use client";

/* P5-W32: opt-in draft-room alerts. A per-browser toggle (persisted
 * in localStorage) that, when on AND notification permission is
 * granted, fires a browser Notification + a short WebAudio chime
 * when the managing-as team goes on the clock and again when its
 * pick clock enters the final 10 seconds. Exactly once per pick —
 * the fired-key set lives in a ref for the page's lifetime, so
 * WebSocket reconnects / state resends never re-fire (decision
 * logic: web/lib/draft-alerts.ts). Off, denied, or unsupported =
 * silent and inert, with honest inline copy for each case.
 */

import { useEffect, useRef, useState } from "react";
import { draftAlertKinds } from "@/lib/draft-alerts";
import type { DraftRoomState } from "@/lib/types";

const STORAGE_KEY = "ipl-draft-alerts-enabled";

type PermState = "unsupported" | NotificationPermission;

function chime() {
  try {
    const Ctx =
      window.AudioContext ??
      (window as unknown as { webkitAudioContext?: typeof AudioContext })
        .webkitAudioContext;
    if (!Ctx) return;
    const ctx = new Ctx();
    void ctx.resume().catch(() => {});
    const gain = ctx.createGain();
    gain.connect(ctx.destination);
    const now = ctx.currentTime;
    gain.gain.setValueAtTime(0.0001, now);
    gain.gain.exponentialRampToValueAtTime(0.18, now + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.45);
    [880, 1318].forEach((freq, i) => {
      const osc = ctx.createOscillator();
      osc.type = "sine";
      osc.frequency.value = freq;
      osc.connect(gain);
      osc.start(now + i * 0.16);
      osc.stop(now + i * 0.16 + 0.18);
    });
    window.setTimeout(() => void ctx.close().catch(() => {}), 700);
  } catch {
    /* audio is best-effort — never let it break the draft room */
  }
}

export function DraftAlertControls({
  snap,
  myTeamId,
  clockLeft,
}: {
  snap: DraftRoomState | null;
  myTeamId: number | null;
  clockLeft: number | null;
}) {
  const [enabled, setEnabled] = useState(false);
  const [perm, setPerm] = useState<PermState>("default");
  const firedRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    setEnabled(localStorage.getItem(STORAGE_KEY) === "1");
    setPerm(
      "Notification" in window ? Notification.permission : "unsupported",
    );
  }, []);

  const effective = enabled && perm === "granted";

  useEffect(() => {
    if (!effective || !snap) return;
    const kinds = draftAlertKinds(
      {
        draftId: snap.draft.id,
        status: snap.draft.status,
        currentPickNo: snap.current_pick_no,
        onClockTeamId: snap.on_clock_team_id,
        myTeamId,
        secsLeft: clockLeft,
      },
      firedRef.current,
    );
    if (kinds.length === 0) return;
    chime();
    for (const kind of kinds) {
      try {
        new Notification(
          kind === "on_clock"
            ? "You're on the clock 🏏"
            : "10 seconds left ⏰",
          {
            body:
              kind === "on_clock"
                ? `Pick ${snap.current_pick_no} — it's your turn in the draft.`
                : `Pick ${snap.current_pick_no} — your clock is almost out; auto-pick is next.`,
            tag: `ipl-draft-${snap.draft.id}-${snap.current_pick_no}-${kind}`,
          },
        );
      } catch {
        /* notification construction is best-effort */
      }
    }
  }, [effective, snap, myTeamId, clockLeft]);

  async function toggle() {
    const next = !enabled;
    setEnabled(next);
    localStorage.setItem(STORAGE_KEY, next ? "1" : "0");
    if (next && "Notification" in window && Notification.permission === "default") {
      try {
        setPerm(await Notification.requestPermission());
      } catch {
        /* permission prompt dismissed — copy below stays honest */
      }
    }
  }

  const copy =
    perm === "unsupported"
      ? "This browser doesn't support notifications, so draft alerts stay off."
      : !enabled
        ? "Off — turn on for a notification + chime when your pick is up."
        : perm === "denied"
          ? "On, but notification permission is denied — allow notifications for this site in your browser settings; until then alerts stay silent."
          : perm === "default"
            ? "On — allow notifications when your browser asks; until then alerts stay silent."
            : "On — a notification + chime fires when you're on the clock and at 10 seconds left.";

  return (
    <span className="inline-flex flex-wrap items-center gap-2">
      <button
        type="button"
        role="switch"
        aria-checked={enabled}
        onClick={toggle}
        className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs transition ${
          enabled
            ? "border-trophy-gold/60 bg-trophy-gold/10 text-trophy-gold"
            : "border-slate-700 bg-slate-800/50 text-slate-400 hover:text-slate-200"
        }`}
      >
        <span aria-hidden="true">🔔</span> Draft alerts {enabled ? "on" : "off"}
      </button>
      <span className="text-xs text-slate-500">{copy}</span>
    </span>
  );
}
