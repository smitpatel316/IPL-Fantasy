"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Trophy, Menu, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "@/lib/theme";
import { api } from "@/lib/api";
import { useLeague } from "@/lib/league-context";
import type { LeagueSummaryOut } from "@/lib/types";

function Brand({ onClick }: { onClick?: () => void }) {
  return (
    <Link href="/" onClick={onClick} className="flex shrink-0 items-center gap-2.5">
      <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-gold-500 text-on-gold shadow-[0_4px_16px_-4px_rgb(245_158_11/0.6)]">
        <Trophy className="h-4.5 w-4.5" strokeWidth={2.25} />
      </span>
      <span className="text-[17px] font-extrabold tracking-tight text-white">
        IPL<span className="text-zinc-500"> </span>
        <span className="font-semibold text-zinc-400">Fantasy</span>
      </span>
    </Link>
  );
}

export default function Nav() {
  const pathname = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const { leagueId, setLeagueId } = useLeague();
  const [leagues, setLeagues] = useState<LeagueSummaryOut[]>([]);

  useEffect(() => {
    api.listLeagues().then(setLeagues).catch(() => {});
  }, []);

  const LINKS = [
    { href: `/league/${leagueId}`, label: "League", match: "league" },
    { href: `/draft-room/${leagueId}`, label: "Draft", match: "draft-room" },
    { href: "/lineup", label: "Lineup", match: "lineup" },
    { href: "/players", label: "Players", match: "players" },
    { href: "/waivers", label: "Waivers", match: "waivers" },
    { href: "/trades", label: "Trades", match: "trades" },
    { href: "/matchup", label: "Matchup", match: "matchup" },
    { href: "/schedule", label: "Schedule", match: "schedule" },
    { href: "/playoffs", label: "Playoffs", match: "playoffs" },
    { href: "/help", label: "How to play", match: "help" },
  ];

  const isActive = (match: string) =>
    pathname === `/${match}` || pathname.startsWith(`/${match}/`);

  /** Switch the current league; on a league-scoped route, navigate to
   *  the same view for the newly selected league. */
  function switchLeague(id: number) {
    setLeagueId(id);
    const m = pathname.match(/^\/(league|draft-room)\/\d+/);
    if (m) router.push(`/${m[1]}/${id}`);
  }

  const switcher = (
    <label className="flex items-center gap-2 text-xs text-zinc-500">
      <span className="hidden font-semibold uppercase tracking-wide xl:inline">League</span>
      <select
        aria-label="Current league"
        className="max-w-44 rounded-lg border border-slate-700 bg-ink-950 px-2 py-1.5 text-[13px] text-white focus:border-trophy-gold focus:outline-none"
        value={leagueId}
        onChange={(e) => switchLeague(Number(e.target.value))}
      >
        {leagues.length === 0 && <option value={leagueId}>League {leagueId}</option>}
        {leagues.map((l) => (
          <option key={l.id} value={l.id}>
            {l.name}
          </option>
        ))}
      </select>
    </label>
  );

  return (
    <header className="sticky top-0 z-40 border-b hairline bg-ink-950/85 backdrop-blur-md">
      <div className="mx-auto flex w-full max-w-6xl items-center gap-4 px-4 py-3">
        <Brand />

        {/* Desktop links */}
        <nav className="hidden flex-1 items-center gap-1 lg:flex">
          {LINKS.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className={cn(
                "relative rounded-lg px-3 py-2 text-[13.5px] font-medium text-zinc-400 transition-colors hover:text-white",
                isActive(l.match) && "text-white",
              )}
            >
              {l.label}
              {isActive(l.match) && (
                <span className="absolute inset-x-3 -bottom-[13px] h-0.5 rounded-full bg-gold-500" />
              )}
            </Link>
          ))}
        </nav>

        <div className="ml-auto hidden items-center gap-3 lg:flex">
          {switcher}
          <ThemeToggle />
          <span className="badge-gold">IPL 2027</span>
        </div>

        {/* Mobile theme toggle + menu */}
        <ThemeToggle className="ml-auto lg:hidden" />
        <button
          className="btn-ghost btn-sm px-2.5 lg:hidden"
          onClick={() => setOpen((v) => !v)}
          aria-label={open ? "Close menu" : "Open menu"}
          aria-expanded={open}
        >
          {open ? <X className="h-4.5 w-4.5" /> : <Menu className="h-4.5 w-4.5" />}
        </button>
      </div>

      {/* Mobile menu */}
      {open && (
        <nav className="border-t hairline bg-ink-950/95 px-4 pb-5 pt-3 backdrop-blur-md lg:hidden">
          <div className="grid grid-cols-2 gap-1.5">
            {LINKS.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                onClick={() => setOpen(false)}
                className={cn(
                  "rounded-xl border px-3.5 py-2.5 text-sm font-medium transition-colors",
                  isActive(l.match)
                    ? "border-gold-500/40 bg-gold-500/10 text-gold-300"
                    : "hairline bg-white/[0.02] text-zinc-300 active:bg-white/[0.06]",
                )}
              >
                {l.label}
              </Link>
            ))}
          </div>
          <div className="mt-3 flex items-center justify-center gap-3">
            {switcher}
            <span className="badge-gold">IPL 2027 Season</span>
          </div>
        </nav>
      )}
    </header>
  );
}
