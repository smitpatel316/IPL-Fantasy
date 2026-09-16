"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Trophy,
  Users,
  CalendarDays,
  ArrowLeftRight,
  Gavel,
  ChevronRight,
  Sparkles,
} from "lucide-react";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/types";
import { Card, Badge, ErrorBox } from "@/components/ui";

const STATS = [
  { k: "15", v: "roster spots" },
  { k: "11", v: "starters weekly" },
  { k: "$100", v: "FAAB budget" },
  { k: "Top 4", v: "make playoffs" },
];

const FEATURES = [
  {
    icon: <Users className="h-5 w-5" />,
    title: "Snake draft",
    text: "14 rounds with a pick clock, auto-pick, custom ranks and do-not-draft lists. Draft from your phone.",
  },
  {
    icon: <CalendarDays className="h-5 w-5" />,
    title: "Weekly head-to-head",
    text: "Mon–Sun matchup periods with a weekly lineup lock. Set it once — no 7am alarms.",
  },
  {
    icon: <Gavel className="h-5 w-5" />,
    title: "FAAB waivers",
    text: "$100 season budget, blind bids processed every Wednesday. Outbid your rivals, don't outspend yourself.",
  },
  {
    icon: <ArrowLeftRight className="h-5 w-5" />,
    title: "Trades & playoffs",
    text: "Propose deals with commissioner review, a week-6 trade deadline, then a top-4 playoff bracket.",
  },
];

const STEPS = [
  { n: "01", t: "Draft", d: "Snake draft your 15-man squad in March, before the season starts." },
  { n: "02", t: "Set lineups", d: "Pick your 11 starters each week — max 4 overseas in the XI." },
  { n: "03", t: "Work the wire", d: "FAAB bids and trades keep your squad sharp through the season." },
  { n: "04", t: "Playoffs", d: "Top 4 battle it out over the final two fantasy weeks." },
];

export default function Home() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [commish, setCommish] = useState("");
  const [joinId, setJoinId] = useState("1");
  const [code, setCode] = useState("");
  const [teamName, setTeamName] = useState("");
  const [owner, setOwner] = useState("");
  const [err, setErr] = useState("");

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    try {
      const league = await api.createLeague(name, commish);
      router.push(`/league/${league.id}`);
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "create failed");
    }
  }

  async function join(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    try {
      await api.joinLeague(joinId, code, teamName, owner);
      router.push(`/league/${joinId}`);
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "join failed");
    }
  }

  return (
    <div>
      {/* ------------------------------ Hero ------------------------------ */}
      <section className="pb-10 pt-8 text-center sm:pt-14">
        <Badge tone="gold" className="mb-5">
          <Sparkles className="h-3 w-3" /> Season-long fantasy cricket · IPL 2027
        </Badge>
        <h1 className="display mx-auto max-w-3xl text-[42px] sm:text-6xl lg:text-7xl">
          Your league. Your rivals.
          <br />
          <span className="text-gold-400">One trophy.</span>
        </h1>
        <p className="lede mx-auto mt-5 max-w-xl text-base">
          Snake draft, weekly head-to-head matchups, FAAB waivers, trades and playoffs —
          the season-long game you know from fantasy basketball, built for the IPL.
        </p>
        <div className="mt-7 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <a href="#start" className="btn-gold w-full sm:w-auto">
            Create a league <ChevronRight className="h-4 w-4" />
          </a>
          <a href="/league/1" className="btn-ghost w-full sm:w-auto">
            Explore the demo league
          </a>
        </div>

        {/* Stat strip */}
        <dl className="mx-auto mt-10 grid max-w-2xl grid-cols-2 gap-px overflow-hidden rounded-2xl border hairline bg-white/[0.04] sm:grid-cols-4">
          {STATS.map((s) => (
            <div key={s.v} className="bg-ink-950/90 px-4 py-4">
              <dt className="sr-only">{s.v}</dt>
              <dd className="tnum text-xl font-extrabold text-white">{s.k}</dd>
              <dd className="mt-0.5 text-[11px] font-medium uppercase tracking-[0.08em] text-zinc-500">
                {s.v}
              </dd>
            </div>
          ))}
        </dl>
      </section>

      {err && (
        <div className="mx-auto mb-6 max-w-3xl">
          <ErrorBox message={err} />
        </div>
      )}

      {/* --------------------------- Create / Join --------------------------- */}
      <section id="start" className="mx-auto grid max-w-3xl scroll-mt-24 gap-4 md:grid-cols-2">
        <Card className="p-6">
          <p className="eyebrow mb-1">Commissioner</p>
          <h2 className="mb-4 text-lg font-bold text-white">Create a league</h2>
          <form onSubmit={create} className="space-y-3">
            <div>
              <label className="field-label" htmlFor="league-name">League name</label>
              <input
                id="league-name"
                className="input"
                placeholder="e.g. Backyard Legends"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>
            <div>
              <label className="field-label" htmlFor="commish">Your name</label>
              <input
                id="commish"
                className="input"
                placeholder="Commissioner"
                value={commish}
                onChange={(e) => setCommish(e.target.value)}
                required
              />
            </div>
            <button className="btn-gold w-full">Create league</button>
          </form>
        </Card>

        <Card className="p-6">
          <p className="eyebrow mb-1">Have an invite?</p>
          <h2 className="mb-4 text-lg font-bold text-white">Join with a code</h2>
          <form onSubmit={join} className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="field-label" htmlFor="join-id">League ID</label>
                <input
                  id="join-id"
                  className="input"
                  value={joinId}
                  onChange={(e) => setJoinId(e.target.value)}
                  required
                />
              </div>
              <div>
                <label className="field-label" htmlFor="join-code">Code</label>
                <input
                  id="join-code"
                  className="input"
                  placeholder="Invite code"
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  required
                />
              </div>
            </div>
            <div>
              <label className="field-label" htmlFor="team-name">Team name</label>
              <input
                id="team-name"
                className="input"
                placeholder="e.g. Yorker Kings"
                value={teamName}
                onChange={(e) => setTeamName(e.target.value)}
                required
              />
            </div>
            <div>
              <label className="field-label" htmlFor="owner">Your name</label>
              <input
                id="owner"
                className="input"
                placeholder="Manager"
                value={owner}
                onChange={(e) => setOwner(e.target.value)}
                required
              />
            </div>
            <button className="btn-dark w-full">Join league</button>
          </form>
        </Card>
      </section>

      {/* ------------------------------ Features ------------------------------ */}
      <section className="mx-auto mt-16 max-w-5xl">
        <p className="eyebrow text-center">The format</p>
        <h2 className="mt-2 text-center text-2xl font-extrabold tracking-tight text-white sm:text-3xl">
          Everything a season needs
        </h2>
        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {FEATURES.map((f) => (
            <Card key={f.title} hover className="p-5">
              <div className="icon-tile mb-4">{f.icon}</div>
              <h3 className="font-bold text-white">{f.title}</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-zinc-400">{f.text}</p>
            </Card>
          ))}
        </div>
      </section>

      {/* --------------------------- How it flows --------------------------- */}
      <section className="mx-auto mt-16 max-w-5xl">
        <Card className="overflow-hidden p-0">
          <div className="grid sm:grid-cols-2 lg:grid-cols-4">
            {STEPS.map((s, i) => (
              <div
                key={s.n}
                className={
                  "p-6 " + (i > 0 ? "border-t hairline sm:border-t-0 sm:border-l" : "")
                }
              >
                <p className="tnum text-sm font-extrabold text-gold-500">{s.n}</p>
                <h3 className="mt-2 font-bold text-white">{s.t}</h3>
                <p className="mt-1 text-sm leading-relaxed text-zinc-400">{s.d}</p>
              </div>
            ))}
          </div>
        </Card>
      </section>

      {/* -------------------------------- Footnote -------------------------------- */}
      <section className="mx-auto mt-14 max-w-xl text-center">
        <div className="icon-tile mb-3">
          <Trophy className="h-5 w-5" />
        </div>
        <p className="text-sm text-zinc-500">
          Exploring? The demo league (ID 1) is a full sandbox — draft, set lineups, run
          waivers. Scoring uses the standard T20 fantasy points table.
        </p>
      </section>
    </div>
  );
}
