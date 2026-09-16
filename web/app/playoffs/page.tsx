import { PageHeader, EngineStub } from "@/components/ui";
import { Trophy, Medal } from "lucide-react";

function SeedRow({ seed, label, highlight }: { seed: string; label: string; highlight?: boolean }) {
  return (
    <div
      className={
        "flex items-center justify-between rounded-lg px-3 py-2.5 text-sm " +
        (highlight ? "bg-trophy-gold/10 text-white" : "bg-slate-800/60 text-zinc-400")
      }
    >
      <span className="flex items-center gap-2">
        <span
          className={
            "flex h-6 w-6 items-center justify-center rounded-md text-[11px] font-extrabold " +
            (highlight ? "bg-trophy-gold text-midnight" : "bg-slate-700 text-zinc-300")
          }
        >
          {seed}
        </span>
        {label}
      </span>
    </div>
  );
}

export default function PlayoffsPage() {
  return (
    <div>
      <PageHeader title="Playoffs" sub="Top 4 · fantasy weeks 7–8 · semifinals + final" />

      <div className="grid items-stretch gap-4 lg:grid-cols-[1fr_auto_1fr]">
        {/* Semifinals */}
        <div className="space-y-4">
          <div className="rounded-xl border border-slate-800 bg-midnight-soft p-5">
            <h2 className="mb-1 flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-zinc-300">
              <Medal className="h-4 w-4 text-zinc-500" /> Semifinal 1
            </h2>
            <p className="mb-3 text-xs text-zinc-600">Week 7</p>
            <div className="space-y-2">
              <SeedRow seed="1" label="1st place" highlight />
              <SeedRow seed="4" label="4th place" />
            </div>
          </div>
          <div className="rounded-xl border border-slate-800 bg-midnight-soft p-5">
            <h2 className="mb-1 flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-zinc-300">
              <Medal className="h-4 w-4 text-zinc-500" /> Semifinal 2
            </h2>
            <p className="mb-3 text-xs text-zinc-600">Week 7</p>
            <div className="space-y-2">
              <SeedRow seed="2" label="2nd place" highlight />
              <SeedRow seed="3" label="3rd place" />
            </div>
          </div>
        </div>

        {/* Connector */}
        <div className="hidden items-center lg:flex" aria-hidden>
          <div className="flex flex-col items-center gap-1 text-zinc-700">
            <div className="h-16 w-px bg-slate-700" />
            <div className="h-px w-8 bg-slate-700" />
            <div className="h-16 w-px bg-slate-700" />
          </div>
        </div>

        {/* Final */}
        <div className="flex flex-col gap-4">
          <div className="flex-1 rounded-xl border border-trophy-gold/30 bg-midnight-soft p-5">
            <h2 className="mb-1 flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-trophy-gold">
              <Trophy className="h-4 w-4" /> Final
            </h2>
            <p className="mb-3 text-xs text-zinc-600">Week 8</p>
            <div className="space-y-2">
              <SeedRow seed="W1" label="Semifinal 1 winner" />
              <SeedRow seed="W2" label="Semifinal 2 winner" />
            </div>
          </div>
          <div className="rounded-xl border border-dashed border-trophy-gold/40 bg-trophy-gold/5 p-5 text-center">
            <Trophy className="mx-auto mb-2 h-8 w-8 text-trophy-gold" />
            <p className="text-sm font-bold text-trophy-gold">Champion</p>
            <p className="mt-1 text-xs text-zinc-500">Crowned after the week 8 final</p>
          </div>
        </div>
      </div>

      <div className="mt-6">
        <EngineStub track="P2-L6" what="Playoff engine (seeding, bracket, consolation)" />
      </div>
      <p className="mt-4 max-w-2xl text-xs leading-relaxed text-zinc-600">
        The fantasy season ends before the real IPL playoffs — the player pool shrinks to 4 teams,
        so fantasy playoffs finish while every IPL team is still alive (Yahoo's "end before dead
        rubbers" principle).
      </p>
    </div>
  );
}
