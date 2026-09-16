"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Trophy, Menu, X } from "lucide-react";
import { cn } from "@/lib/utils";

const LINKS = [
  { href: "/league/1", label: "League", match: "league" },
  { href: "/draft-room/1", label: "Draft", match: "draft-room" },
  { href: "/lineup", label: "Lineup", match: "lineup" },
  { href: "/players", label: "Players", match: "players" },
  { href: "/waivers", label: "Waivers", match: "waivers" },
  { href: "/trades", label: "Trades", match: "trades" },
  { href: "/matchup", label: "Matchup", match: "matchup" },
  { href: "/playoffs", label: "Playoffs", match: "playoffs" },
];

function Brand({ onClick }: { onClick?: () => void }) {
  return (
    <Link href="/" onClick={onClick} className="flex shrink-0 items-center gap-2.5">
      <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-gold-500 text-ink-950 shadow-[0_4px_16px_-4px_rgb(245_158_11/0.6)]">
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
  const [open, setOpen] = useState(false);

  const isActive = (match: string) =>
    pathname === `/${match}` || pathname.startsWith(`/${match}/`);

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

        <div className="ml-auto hidden items-center lg:flex">
          <span className="badge-gold">IPL 2027</span>
        </div>

        {/* Mobile toggle */}
        <button
          className="btn-ghost btn-sm ml-auto px-2.5 lg:hidden"
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
          <div className="mt-3 flex justify-center">
            <span className="badge-gold">IPL 2027 Season</span>
          </div>
        </nav>
      )}
    </header>
  );
}
