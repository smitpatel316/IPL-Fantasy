import type { Availability } from "@/lib/types";
import { cn } from "@/lib/utils";

/**
 * P5-W6: availability dots (blueprint §12 steal #1). The state comes
 * from the API, which derives it from the curated player_roles.status
 * until the live poller lands (Feb 2027) — copy stays honest about
 * that in the legend below.
 *   active  → green  (available)
 *   out     → red    (injured / expected to miss a game; IL-eligible)
 *   retired → grey   (retired from the registry)
 */
export const AVAILABILITY_META: Record<
  Availability,
  { dot: string; label: string; text: string }
> = {
  active: { dot: "bg-pitch-green", label: "Available", text: "text-pitch-green" },
  out: { dot: "bg-red-400", label: "Out — injured / expected to miss", text: "text-red-300" },
  retired: { dot: "bg-zinc-500", label: "Retired", text: "text-zinc-500" },
};

export function AvailabilityDot({
  availability,
  className,
}: {
  availability: Availability | null | undefined;
  className?: string;
}) {
  const meta = AVAILABILITY_META[availability ?? "active"];
  return (
    <span
      role="img"
      aria-label={meta.label}
      title={meta.label}
      className={cn("inline-block h-2 w-2 shrink-0 rounded-full", meta.dot, className)}
    />
  );
}

export function AvailabilityLegend({ className }: { className?: string }) {
  return (
    <div className={cn("flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-zinc-500", className)}>
      {(Object.keys(AVAILABILITY_META) as Availability[]).map((a) => (
        <span key={a} className="inline-flex items-center gap-1.5">
          <AvailabilityDot availability={a} />
          {AVAILABILITY_META[a].label}
        </span>
      ))}
      <span>Availability from the curated registry until live squads import.</span>
    </div>
  );
}
