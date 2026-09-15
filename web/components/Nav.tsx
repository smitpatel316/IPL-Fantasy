"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Trophy } from "lucide-react";
import { cn } from "@/lib/utils";

const LINKS = [
  { href: "/league/1", label: "League" },
  { href: "/draft-room/1", label: "Draft" },
  { href: "/lineup", label: "Lineup" },
  { href: "/players", label: "Players" },
  { href: "/waivers", label: "Waivers" },
  { href: "/trades", label: "Trades" },
  { href: "/matchup", label: "Matchup" },
  { href: "/playoffs", label: "Playoffs" },
];

export default function Nav() {
  const pathname = usePathname();
  return (
    <header className="sticky top-0 z-40 border-b border-slate-800 bg-midnight/90 backdrop-blur">
      <div className="mx-auto flex w-full max-w-6xl items-center gap-6 px-4 py-3">
        <Link href="/" className="flex items-center gap-2 text-trophy-gold">
          <Trophy className="h-5 w-5" />
          <span className="text-lg font-bold tracking-tight">IPL Fantasy</span>
        </Link>
        <nav className="flex flex-1 flex-wrap items-center gap-1">
          {LINKS.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className={cn(
                "rounded-md px-3 py-1.5 text-sm text-slate-300 hover:bg-slate-800 hover:text-white",
                pathname.startsWith(l.href.split("/")[1] ? `/${l.href.split("/")[1]}` : "/") &&
                  pathname !== "/" &&
                  "bg-slate-800 text-white",
              )}
            >
              {l.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
