"use client";

/* P5-W2: per-team player watchlist.
   Shared hook + star toggle used by the players list, the waiver-wire
   table, and the "Watched" section on the players page. The watchlist
   is scoped to the managing-as team (P4-W18 identity: writes carry the
   team's claim header automatically via the api client). Toggles are
   optimistic — the star flips instantly and reverts if the API
   rejects (e.g. a claimed team this browser hasn't claimed). */

import { useCallback, useEffect, useMemo, useState } from "react";
import { Star } from "lucide-react";
import { api } from "@/lib/api";
import { ApiError, type WatchlistEntryOut } from "@/lib/types";

export interface UseWatchlist {
  entries: WatchlistEntryOut[];
  watchedIds: Set<number>;
  toggle: (playerId: number) => Promise<void>;
  error: string;
  loading: boolean;
}

export function useWatchlist(leagueId: number, teamId: number | null): UseWatchlist {
  const [entries, setEntries] = useState<WatchlistEntryOut[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const reload = useCallback(async () => {
    if (teamId == null) {
      setEntries([]);
      return;
    }
    setLoading(true);
    try {
      setEntries(await api.listWatchlist(leagueId, teamId));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "watchlist load failed");
    } finally {
      setLoading(false);
    }
  }, [leagueId, teamId]);

  useEffect(() => {
    reload();
  }, [reload]);

  const watchedIds = useMemo(() => new Set(entries.map((e) => e.id)), [entries]);

  const toggle = useCallback(
    async (playerId: number) => {
      if (teamId == null) return;
      setError("");
      const wasWatched = watchedIds.has(playerId);
      // Optimistic flip so add/remove reflects instantly.
      setEntries((prev) =>
        wasWatched
          ? prev.filter((e) => e.id !== playerId)
          : prev,
      );
      try {
        if (wasWatched) {
          await api.unstarPlayer(leagueId, teamId, playerId);
        } else {
          const entry = await api.starPlayer({
            league_id: leagueId,
            team_id: teamId,
            player_id: playerId,
          });
          setEntries((prev) =>
            prev.some((e) => e.id === entry.id) ? prev : [entry, ...prev],
          );
        }
      } catch (e) {
        setError(e instanceof ApiError ? e.message : "watch toggle failed");
        reload();
      }
    },
    [leagueId, teamId, watchedIds, reload],
  );

  return { entries, watchedIds, toggle, error, loading };
}

/** Star button rendered in player rows (players list + waiver wire). */
export function WatchToggle({
  watched,
  onToggle,
  playerName,
}: {
  watched: boolean;
  onToggle: () => void;
  playerName: string;
}) {
  return (
    <button
      type="button"
      onClick={(e) => {
        e.preventDefault();
        e.stopPropagation();
        onToggle();
      }}
      aria-label={watched ? `Unwatch ${playerName}` : `Watch ${playerName}`}
      title={watched ? "Remove from watchlist" : "Add to watchlist"}
      className={`rounded-md p-1.5 transition ${
        watched
          ? "text-trophy-gold hover:bg-trophy-gold/10"
          : "text-zinc-600 hover:bg-slate-800 hover:text-zinc-300"
      }`}
    >
      <Star className={`h-4 w-4 ${watched ? "fill-trophy-gold" : ""}`} />
    </button>
  );
}
