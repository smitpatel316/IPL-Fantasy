"use client";

/* Current-league selection (P4-W7). Every tab used to hardcode
   league 1; pages now read the selected league from this context.
   The selection persists in localStorage and defaults to league 1
   (the sandbox league) until the user picks another — creating or
   joining a league on the home page, opening a /league/[id] or
   /draft-room/[id] route, or using the Nav switcher all set it. */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

const STORAGE_KEY = "ipl.leagueId";

interface LeagueCtx {
  leagueId: number;
  setLeagueId: (id: number) => void;
}

const Ctx = createContext<LeagueCtx>({ leagueId: 1, setLeagueId: () => {} });

export function LeagueProvider({ children }: { children: ReactNode }) {
  const [leagueId, setLeagueIdState] = useState(1);

  useEffect(() => {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    const n = raw ? Number(raw) : NaN;
    if (Number.isFinite(n) && n > 0) setLeagueIdState(n);
  }, []);

  const setLeagueId = useCallback((id: number) => {
    setLeagueIdState(id);
    try {
      window.localStorage.setItem(STORAGE_KEY, String(id));
    } catch {
      /* storage unavailable (private mode) — selection still applies */
    }
  }, []);

  return <Ctx.Provider value={{ leagueId, setLeagueId }}>{children}</Ctx.Provider>;
}

export function useLeague(): LeagueCtx {
  return useContext(Ctx);
}
