export function PageHeader({ title, sub }: { title: string; sub?: string }) {
  return (
    <div className="mb-6">
      <h1 className="text-2xl font-bold tracking-tight text-white">{title}</h1>
      {sub && <p className="mt-1 text-sm text-slate-400">{sub}</p>}
    </div>
  );
}

export function EngineStub({ track, what }: { track: string; what: string }) {
  return (
    <div className="rounded-lg border border-dashed border-slate-700 bg-midnight-soft/50 p-6 text-center">
      <p className="text-sm font-medium text-slate-300">{what} — engine not wired yet</p>
      <p className="mt-1 text-xs text-slate-500">
        Owned by <span className="font-mono text-trophy-gold">{track}</span> (league-core track).
        This shell holds the place; the UI contract is final.
      </p>
    </div>
  );
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="rounded-lg border border-brick-red/40 bg-brick-red/10 p-4 text-sm text-red-200">
      <p>{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-2 rounded-md bg-brick-red/20 px-3 py-1 text-xs font-medium hover:bg-brick-red/30"
        >
          Retry
        </button>
      )}
    </div>
  );
}
