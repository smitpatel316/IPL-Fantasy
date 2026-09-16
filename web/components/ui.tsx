import { cn } from "@/lib/utils";

/* ------------------------------------------------------------------
   Shared UI kit — monochrome + trophy-gold accent.
   EngineStub takes a manager-friendly `message`; internal track IDs
   live in code comments at the call sites, never in the UI.
   ------------------------------------------------------------------ */

export function PageHeader({
  title,
  sub,
  eyebrow,
}: {
  title: string;
  sub?: string;
  eyebrow?: string;
}) {
  return (
    <div className="mb-6">
      {eyebrow && <p className="eyebrow mb-2">{eyebrow}</p>}
      <h1 className="text-[26px] font-extrabold tracking-tight text-white sm:text-3xl">
        {title}
      </h1>
      {sub && <p className="lede mt-1.5 max-w-2xl">{sub}</p>}
    </div>
  );
}

export function Card({
  className,
  children,
  hover = false,
}: {
  className?: string;
  children: React.ReactNode;
  hover?: boolean;
}) {
  return <div className={cn(hover ? "card-hover" : "card", className)}>{children}</div>;
}

export function Badge({
  tone = "neutral",
  className,
  children,
}: {
  tone?: "gold" | "neutral" | "green" | "red";
  className?: string;
  children: React.ReactNode;
}) {
  const tones = {
    gold: "badge-gold",
    neutral: "badge-neutral",
    green: "badge-green",
    red: "badge-red",
  } as const;
  return <span className={cn(tones[tone], className)}>{children}</span>;
}

export function EmptyState({
  icon,
  title,
  sub,
  action,
}: {
  icon?: React.ReactNode;
  title: string;
  sub?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="card flex flex-col items-center px-6 py-12 text-center">
      {icon && <div className="icon-tile mb-4">{icon}</div>}
      <p className="font-semibold text-white">{title}</p>
      {sub && <p className="lede mt-1 max-w-sm text-sm">{sub}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function EngineStub({ message }: { message: string }) {
  return (
    <div className="card border-dashed p-8 text-center">
      <p className="text-sm font-semibold text-zinc-200">{message}</p>
      <p className="mt-1.5 text-xs text-zinc-500">
        This part of the app is still being built — check back soon.
      </p>
    </div>
  );
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="rounded-xl border border-clay-400/30 bg-clay-400/[0.07] p-4 text-sm text-red-200">
      <p>{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="btn-ghost btn-sm mt-3"
        >
          Retry
        </button>
      )}
    </div>
  );
}

/* Class-string helpers for pages that need raw classNames (Links etc.) */
export const btnGold = "btn-gold";
export const btnGhost = "btn-ghost";
export const btnDark = "btn-dark";
