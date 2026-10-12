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
