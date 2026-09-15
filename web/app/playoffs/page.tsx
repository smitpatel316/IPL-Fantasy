import { PageHeader, EngineStub } from "@/components/ui";

export default function PlayoffsPage() {
  return (
    <div>
      <PageHeader title="Playoffs" sub="Top 4 · fantasy weeks 7–8 · semis + final (D9)" />
      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-xl border border-slate-800 bg-midnight-soft p-5">
          <h2 className="mb-3 font-semibold text-white">Semifinals <span className="text-xs font-normal text-slate-500">Week 7</span></h2>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between rounded-md bg-slate-800/60 px-3 py-2">
              <span className="text-slate-400">Seed 1 vs Seed 4</span><span className="text-slate-600">–</span>
            </div>
            <div className="flex justify-between rounded-md bg-slate-800/60 px-3 py-2">
              <span className="text-slate-400">Seed 2 vs Seed 3</span><span className="text-slate-600">–</span>
            </div>
          </div>
        </div>
        <div className="rounded-xl border border-trophy-gold/30 bg-midnight-soft p-5">
          <h2 className="mb-3 font-semibold text-trophy-gold">Final <span className="text-xs font-normal text-slate-500">Week 8</span></h2>
          <div className="rounded-md bg-slate-800/60 px-3 py-2 text-sm text-slate-400">
            Winners meet for the trophy
          </div>
        </div>
      </div>
      <div className="mt-6">
        <EngineStub track="P2-L6" what="Playoff engine (seeding, bracket, consolation)" />
      </div>
      <p className="mt-4 text-xs text-slate-600">
        The fantasy season ends before the real IPL playoffs — the player pool shrinks to 4 teams
        (blueprint §9, Yahoo's "end before dead rubbers" principle).
      </p>
    </div>
  );
}
