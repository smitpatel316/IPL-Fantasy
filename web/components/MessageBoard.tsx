"use client";

/* P5-W5: league message board — persistent trash talk, separate from
   the draft room's in-memory chat. Anyone can read; posting acts as
   the "managing as" team and rides the P4-W18 claim gate (the api
   client attaches the stored claim code automatically). The
   commissioner's team gets a remove button (server soft-deletes). */

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ApiError, type MessageOut } from "@/lib/types";
import { cn } from "@/lib/utils";
import { MessagesSquare, Send, Trash2 } from "lucide-react";

const PAGE = 50;

export function MessageBoard({
  leagueId,
  myTeamId,
  myTeamName,
}: {
  leagueId: number;
  myTeamId: number | null;
  myTeamName: string | null;
}) {
  const [messages, setMessages] = useState<MessageOut[]>([]);
  const [total, setTotal] = useState(0);
  const [commissionerTeamId, setCommissionerTeamId] = useState<number | null>(null);
  const [draft, setDraft] = useState("");
  const [err, setErr] = useState("");
  const [posting, setPosting] = useState(false);

  const load = useCallback(
    async (offset: number) => {
      try {
        const board = await api.getMessageBoard(leagueId, PAGE, offset);
        setTotal(board.total);
        setCommissionerTeamId(board.commissioner_team_id);
        setMessages((prev) =>
          offset === 0 ? board.messages : [...prev, ...board.messages],
        );
      } catch (e) {
        setErr(e instanceof ApiError ? e.message : "board load failed");
      }
    },
    [leagueId],
  );

  useEffect(() => {
    load(0);
  }, [load]);

  async function post() {
    const body = draft.trim();
    if (!body || myTeamId == null) return;
    setPosting(true);
    setErr("");
    try {
      const msg = await api.postMessage(leagueId, myTeamId, body);
      setMessages((prev) => [msg, ...prev]);
      setTotal((t) => t + 1);
      setDraft("");
    } catch (e) {
      setErr(
        e instanceof ApiError
          ? e.message
          : "post failed — if this team is claimed, claim it in Standings first",
      );
    } finally {
      setPosting(false);
    }
  }

  async function remove(id: number) {
    if (myTeamId == null) return;
    setErr("");
    try {
      await api.deleteMessage(leagueId, id, myTeamId);
      setMessages((prev) => prev.filter((m) => m.id !== id));
      setTotal((t) => Math.max(0, t - 1));
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "remove failed");
    }
  }

  const isCommissioner = myTeamId != null && myTeamId === commissionerTeamId;

  return (
    <section
      aria-label="Message board"
      className="mb-5 rounded-xl border border-slate-800 bg-midnight-soft p-5"
    >
      <h2 className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-zinc-300">
        <MessagesSquare className="h-4 w-4 text-gold-ink" /> Message board
        <span className="text-[11px] font-medium normal-case tracking-normal text-zinc-500">
          {total} post{total === 1 ? "" : "s"} · trash talk responsibly
        </span>
      </h2>

      {err && <p className="mt-2 text-xs text-loss-ink">{err}</p>}

      <div className="mt-3 flex gap-2">
        <textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          maxLength={500}
          rows={2}
          disabled={myTeamId == null}
          placeholder={
            myTeamId == null
              ? "Pick a team above to post."
              : `Post as ${myTeamName ?? "your team"}…`
          }
          className="flex-1 resize-none rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white placeholder:text-slate-500 disabled:opacity-50"
        />
        <button
          type="button"
          onClick={post}
          disabled={posting || myTeamId == null || draft.trim() === ""}
          className="flex items-center gap-1.5 self-end rounded-md bg-trophy-gold px-3 py-2 text-sm font-bold text-midnight transition hover:bg-trophy-gold/90 disabled:opacity-50"
        >
          <Send className="h-4 w-4" /> Post
        </button>
      </div>

      {messages.length === 0 ? (
        <p className="mt-4 text-sm text-zinc-500">
          No posts yet — open the trash talk. First manager to post sets the tone.
        </p>
      ) : (
        <ul className="mt-4 divide-y divide-slate-800/60">
          {messages.map((m) => (
            <li key={m.id} className="group flex items-start gap-3 py-2.5">
              <div className="min-w-0 flex-1">
                <p className="text-xs text-zinc-500">
                  <span
                    className={cn(
                      "font-semibold",
                      m.team_id === myTeamId ? "text-gold-ink" : "text-zinc-300",
                    )}
                  >
                    {m.team_name}
                  </span>{" "}
                  · {m.created_at} UTC
                </p>
                <p className="mt-0.5 whitespace-pre-wrap text-sm text-zinc-200">{m.body}</p>
              </div>
              {isCommissioner && (
                <button
                  type="button"
                  onClick={() => remove(m.id)}
                  aria-label={`Remove post by ${m.team_name}`}
                  title="Remove post (commissioner)"
                  className="rounded-md p-1.5 text-zinc-600 transition hover:bg-slate-800 hover:text-red-300"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              )}
            </li>
          ))}
        </ul>
      )}

      {messages.length < total && (
        <button
          type="button"
          onClick={() => load(messages.length)}
          className="mt-3 rounded-md border border-slate-700 px-3 py-1.5 text-xs font-semibold text-zinc-300 transition hover:bg-slate-800"
        >
          Load older posts ({total - messages.length} more)
        </button>
      )}
    </section>
  );
}
