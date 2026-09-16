"use client";

import styles from "@/app/draft-room/draft-room.module.css";

export interface DraftFeedItem {
  key: string;
  text: string;
  auto?: boolean;
}

/** Live pick feed. Newest first, slide-in animation, AUTO picks tinted. */
export function DraftFeed({ items }: { items: DraftFeedItem[] }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-midnight-soft/70 p-4">
      <h2 className="mb-3 font-semibold text-white">Pick feed</h2>
      <div className="max-h-[320px] space-y-1.5 overflow-y-auto pr-1 text-sm">
        {items.length === 0 && <p className="text-xs text-slate-600">Picks will appear here live.</p>}
        {items.map((f) => (
          <p
            key={f.key}
            className={`${styles.feedItem} rounded-md px-2 py-1 ${
              f.auto ? "bg-amber-950/40 text-amber-200/90" : "text-slate-300"
            }`}
          >
            {f.auto && (
              <span className="mr-1.5 rounded bg-amber-800/60 px-1 py-px text-[10px] font-bold uppercase">Auto</span>
            )}
            {f.text}
          </p>
        ))}
      </div>
    </div>
  );
}
