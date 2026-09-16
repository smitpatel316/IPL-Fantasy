"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Trophy, Users, CalendarDays, ArrowLeftRight } from "lucide-react";
import { api } from "@/lib/api";
import { ApiError } from "@/lib/types";

function Card({ icon, title, text }: { icon: React.ReactNode; title: string; text: string }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-midnight-soft p-5">
      <div className="mb-3 text-trophy-gold">{icon}</div>
      <h3 className="font-semibold text-white">{title}</h3>
      <p className="mt-1 text-sm text-slate-400">{text}</p>
    </div>
  );
}

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

  const input =
    "w-full rounded-md border border-slate-700 bg-midnight px-3 py-2 text-sm text-white placeholder:text-slate-500 focus:border-ipl-blue-bright focus:outline-none";

  return (
    <div>
      <section className="py-10 text-center">
        <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-trophy-gold/30 bg-trophy-gold/10 px-4 py-1 text-xs font-medium text-trophy-gold">
          <Trophy className="h-3.5 w-3.5" /> Season-long fantasy cricket · IPL 2027
        </div>
        <h1 className="mx-auto max-w-2xl text-4xl font-extrabold tracking-tight text-white">
          Your league. Your rivals. <span className="text-trophy-gold">One trophy.</span>
        </h1>
        <p className="mx-auto mt-3 max-w-xl text-slate-400">
          Snake draft, weekly head-to-head matchups, FAAB waivers, trades and playoffs —
          the Yahoo-style season game, built for the IPL.
        </p>
      </section>

      {err && (
        <div className="mx-auto mb-6 max-w-3xl rounded-lg border border-brick-red/40 bg-brick-red/10 p-3 text-sm text-red-200">
          {err}
        </div>
      )}

      <section className="mx-auto grid max-w-3xl gap-4 md:grid-cols-2">
        <form onSubmit={create} className="rounded-xl border border-slate-800 bg-midnight-soft p-5">
          <h2 className="mb-3 font-semibold text-white">Create a league</h2>
          <div className="space-y-3">
            <input className={input} placeholder="League name" value={name} onChange={(e) => setName(e.target.value)} required />
            <input className={input} placeholder="Your name (commissioner)" value={commish} onChange={(e) => setCommish(e.target.value)} required />
            <button className="w-full rounded-md bg-ipl-blue px-4 py-2 text-sm font-semibold text-white hover:bg-ipl-blue-bright">
              Create league
            </button>
          </div>
        </form>
        <form onSubmit={join} className="rounded-xl border border-slate-800 bg-midnight-soft p-5">
          <h2 className="mb-3 font-semibold text-white">Join with invite code</h2>
          <div className="space-y-3">
            <div className="flex gap-2">
              <input className={input} placeholder="League ID" value={joinId} onChange={(e) => setJoinId(e.target.value)} required />
              <input className={input} placeholder="Code" value={code} onChange={(e) => setCode(e.target.value)} required />
            </div>
            <input className={input} placeholder="Team name" value={teamName} onChange={(e) => setTeamName(e.target.value)} required />
            <input className={input} placeholder="Your name" value={owner} onChange={(e) => setOwner(e.target.value)} required />
            <button className="w-full rounded-md bg-pitch-green px-4 py-2 text-sm font-semibold text-midnight hover:brightness-110">
              Join league
            </button>
          </div>
        </form>
      </section>

      <section className="mx-auto mt-10 grid max-w-5xl gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card icon={<Users className="h-5 w-5" />} title="Snake draft" text="15 rounds, pick clock with auto-pick, custom ranks and do-not-draft lists." />
        <Card icon={<CalendarDays className="h-5 w-5" />} title="Weekly H2H" text="Mon–Sun matchup periods, weekly lineup lock — no 7am alarms." />
        <Card icon={<Trophy className="h-5 w-5" />} title="FAAB waivers" text="$100 season budget, blind bids run every Wednesday." />
        <Card icon={<ArrowLeftRight className="h-5 w-5" />} title="Trades & playoffs" text="Commissioner review, deadline end of week 6, top-4 playoff bracket." />
      </section>

      <p className="mt-10 text-center text-xs text-slate-600">
        Sandbox mode — explore with the demo league (ID 1). Scoring: standard T20 fantasy table.
      </p>
    </div>
  );
}
