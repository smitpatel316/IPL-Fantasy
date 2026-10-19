/* Lightweight team identity (P4-W18): a team's claim code lives in
   this browser's localStorage. Once a team is claimed server-side,
   team-scoped mutations must present the code; the api client
   attaches it automatically for teams this browser has claimed. */

const key = (teamId: number) => `ipl-claim-${teamId}`;

export function getTeamClaim(teamId: number): string | null {
  try {
    return window.localStorage.getItem(key(teamId));
  } catch {
    return null;
  }
}

export function setTeamClaim(teamId: number, code: string): void {
  try {
    window.localStorage.setItem(key(teamId), code);
  } catch {
    /* storage unavailable — mutations for claimed teams will 403 */
  }
}

export function clearTeamClaim(teamId: number): void {
  try {
    window.localStorage.removeItem(key(teamId));
  } catch {
    /* ignore */
  }
}

/** Headers proving this browser acts for the team (empty when unclaimed here). */
export function claimHeaders(teamId: number): Record<string, string> {
  const code = getTeamClaim(teamId);
  return code ? { "X-Team-Claim": code } : {};
}

/** P5-W45: every team id this browser holds a claim code for — the
 *  visitor's teams, found by scanning localStorage for the P4-W18 keys. */
export function myClaimedTeamIds(): number[] {
  const ids: number[] = [];
  try {
    for (let i = 0; i < window.localStorage.length; i++) {
      const k = window.localStorage.key(i);
      if (!k || !k.startsWith("ipl-claim-")) continue;
      const n = Number(k.slice("ipl-claim-".length));
      if (Number.isFinite(n) && n > 0 && !ids.includes(n)) ids.push(n);
    }
  } catch {
    /* storage unavailable — no claims */
  }
  return ids;
}
