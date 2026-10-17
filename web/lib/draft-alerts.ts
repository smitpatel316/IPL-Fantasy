/* P5-W32: draft-room on-the-clock alerts — pure decision logic.
 *
 * Given the latest draft-room state and the set of alert keys that
 * have already fired, decide which alerts fire NOW. Keys are
 * `${draftId}:${pickNo}:${kind}`, so an alert fires exactly once
 * per pick: WebSocket reconnects and state resends recompute the
 * same key and are suppressed, and a new draft (new draftId)
 * re-arms cleanly. The caller owns the fired set (a ref that lives
 * as long as the draft-room page) and the side effects
 * (Notification + chime); this module is side-effect free apart
 * from recording the keys it returns into `fired`.
 */

export type DraftAlertKind = "on_clock" | "final_10";

export interface DraftAlertState {
  draftId: number;
  status: string;
  currentPickNo: number;
  onClockTeamId: number | null;
  myTeamId: number | null;
  /** Seconds left on the current pick clock, or null when unset. */
  secsLeft: number | null;
}

export const FINAL_SECONDS = 10;

export function draftAlertKinds(
  state: DraftAlertState,
  fired: Set<string>,
): DraftAlertKind[] {
  if (state.status !== "live") return [];
  if (state.myTeamId == null || state.onClockTeamId !== state.myTeamId) {
    return [];
  }
  const kinds: DraftAlertKind[] = [];
  const base = `${state.draftId}:${state.currentPickNo}`;
  const onClockKey = `${base}:on_clock`;
  if (!fired.has(onClockKey)) {
    fired.add(onClockKey);
    kinds.push("on_clock");
  }
  if (
    state.secsLeft != null &&
    state.secsLeft <= FINAL_SECONDS &&
    state.secsLeft > 0
  ) {
    const finalKey = `${base}:final_10`;
    if (!fired.has(finalKey)) {
      fired.add(finalKey);
      kinds.push("final_10");
    }
  }
  return kinds;
}
