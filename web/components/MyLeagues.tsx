"use client";

/* P5-W45: "My leagues" — the visitor's claimed teams (found by scanning
   this browser's P4-W18 claim codes) across every league, each with its
   league name, season, team name, and W-L record from finalized
   matchups. Full card for the home page; compact strip for the league
   page. Viewing a /league/[id] route makes it the current league
   everywhere (P4-W7), so plain Links swap context. */

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeftRight } from "lucide-react";
import { api } from "@/lib/api";
import { myClaimedTeamIds } from "@/lib/identity";
import type { MyLeagueTeamOut } from "@/lib/types";
import { Card, ErrorBox } from "@/components/ui";

export function useMyLeagues(): {
  entries: MyLeagueTeamOut[] | null;
  err: string;
} {
  const [entries, setEntries] = useState<MyLeagueTeamOut[] | null>(null);
  const [err, setErr] = useState("");
  useEffect(() => {
    api
      .myLeagues(myClaimedTeamIds())
      .then((es) => setEntries(es))
      .catch((e) => {
        /* The endpoint skips teams deleted from another device; only
           transport failures land here. */
        setErr(e instanceof Error ? e.message : "load failed");
        setEntries([]);
      });
  }, []);
  return { entries, err };
}

function record(e: MyLeagueTeamOut): string {
  return `${e.wins}–${e.losses}${e.ties ? `–${e.ties}` : ""}`;
}

/** Full card: leagues this browser's teams live in. Null (renders
 *  nothing) until loaded, and nothing at all when the visitor holds no
 *  claims — the create/join home stays the default view. */
export function MyLeaguesCard() {
  const { entries, err } = useMyLeagues();
  if (entries === null || entries.length === 0) return null;
  return (
    <section aria-label="My leagues" className="mx-auto mb-8 max-w-3xl">
      <Card className="p-6">
        <div className="mb-4 flex items-center gap-2">
          <ArrowLeftRight className="h-4 w-4 text-gold-400" />
          <h2 className="text-lg font-bold text-white">My leagues</h2>
        </div>
        {err && <ErrorBox message={err} />}
        <ul className="divide-y hairline">
          {entries.map((e) => (
            <li key={`${e.league_id}-${e.team_id}`}>
              <Link
                href={`/league/${e.league_id}`}
                className="flex items-center gap-4 py-3 transition-colors hover:bg-white/[0.03] -mx-2 px-2 rounded-lg"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate font-semibold text-white">
                    {e.league_name}
                    <span className="ml-2 text-xs font-medium text-zinc-500">
                      {e.season}
                    </span>
                  </p>
                  <p className="truncate text-sm text-zinc-400">
                    {e.team_name} · {e.league_status}
                  </p>
                </div>
                <p className="tnum shrink-0 text-sm font-bold text-white">
                  {record(e)}
                </p>
              </Link>
            </li>
          ))}
        </ul>
      </Card>
    </section>
  );
}

/** Compact strip for the league page: jump between this browser's
 *  leagues without opening the Nav switcher. */
export function MyLeaguesStrip({ currentLeagueId }: { currentLeagueId: number }) {
  const { entries } = useMyLeagues();
  if (entries === null || entries.length <= 1) return null;
  const others = entries.filter((e) => e.league_id !== currentLeagueId);
  if (others.length === 0) return null;
  return (
    <div className="mb-5 flex flex-wrap items-center gap-2" aria-label="My other leagues">
      <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
        My leagues
      </span>
      {others.map((e) => (
        <Link
          key={`${e.league_id}-${e.team_id}`}
          href={`/league/${e.league_id}`}
          className="rounded-full border hairline bg-white/[0.03] px-3 py-1.5 text-xs font-semibold text-zinc-300 transition-colors hover:border-gold-500/40 hover:text-white"
        >
          {e.league_name} · {e.team_name} ({record(e)})
        </Link>
      ))}
    </div>
  );
}
