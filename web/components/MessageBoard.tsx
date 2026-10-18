"use client";

/* P5-W5: league message board — persistent trash talk, separate from
   the draft room's in-memory chat. Anyone can read; posting acts as
   the "managing as" team and rides the P4-W18 claim gate (the api
   client attaches the stored claim code automatically). The
   commissioner's team gets a remove button (server soft-deletes).
   P5-W39: the commissioner's team can pin ONE of its own posts — it
   renders in a pinned strip above the feed instead of feed order;
   pinning a new one unpins the old; deleting a pinned post clears
   the strip. Pin/unpin controls are hidden for non-commissioners. */

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ApiError, type MessageOut } from "@/lib/types";
import { cn } from "@/lib/utils";
import { MessagesSquare, Pin, PinOff, Send, Trash2 } from "lucide-react";

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
  const [pinned, setPinned] = useState<MessageOut | null>(null);
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
        setPinned(board.pinned_message);
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
      // reload the board: the pinned strip must clear when a pinned
      // post is deleted (server excludes soft-deleted pins).
      await load(0);
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "remove failed");
    }
  }

  async function pin(id: number) {
    if (myTeamId == null) return;
    setErr("");
    try {
      await api.pinMessage(leagueId, id, myTeamId);
      await load(0); // new pin unpins the old one server-side
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "pin failed");
    }
  }

  async function unpin(id: number) {
    if (myTeamId == null) return;
    setErr("");
    try {
      await api.unpinMessage(leagueId, id, myTeamId);
      await load(0); // unpinned post returns to feed order
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "unpin failed");
    }
  }

  const isCommissioner = myTeamId != null && myTeamId === commissionerTeamId;

  return (
    <section
      aria-label="Message board"
      className="mb-5 rounded-xl border border-slate-800 bg-midnight-soft p-5"
    >
      <h2 className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-zinc-300">
        <MessagesSquare className="h-4 w-4 text-trophy-gold" /> Message board
        <span className="text-[11px] font-medium normal-case tracking-normal text-zinc-500">
          {total} post{total === 1 ? "" : "s"} · trash talk responsibly
        </span>
      </h2>

      {err && <p className="mt-2 text-xs text-brick-red">{err}</p>}

      {/* P5-W39: pinned commissioner announcement — strip above the feed */}
      {pinned && (
        <div
          aria-label="Pinned announcement"
          className="mt-4 rounded-lg border border-trophy-gold/40 bg-trophy-gold/[0.06] px-3 py-2.5"
        >
          <p className="flex items-center justify-between text-[11px] font-bold uppercase tracking-wider text-trophy-gold">
            <span className="flex items-center gap-1.5">
              <Pin className="h-3.5 w-3.5" /> Pinned announcement
            </span>
            {isCommissioner && (
              <button
                type="button"
                onClick={() => unpin(pinned.id)}
                aria-label="Unpin announcement"
                title="Unpin (commissioner)"
                className="flex items-center gap-1 rounded-md px-1.5 py-1 text-[11px] font-semibold normal-case tracking-normal text-zinc-400 transition hover:bg-slate-800 hover:text-zinc-200"
              >
                <PinOff className="h-3.5 w-3.5" /> Unpin
              </button>
            )}
          </p>
          <p className="mt-1 text-xs text-zinc-500">
            <span className="font-semibold text-zinc-300">{pinned.team_name}</span>{" "}
            · {pinned.created_at} UTC
          </p>
          <p className="mt-0.5 whitespace-pre-wrap text-sm text-zinc-200">{pinned.body}</p>
        </div>
      )}

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
                      m.team_id === myTeamId ? "text-trophy-gold" : "text-zinc-300",
                    )}
                  >
                    {m.team_name}
                  </span>{" "}
                  · {m.created_at} UTC
                </p>
                <p className="mt-0.5 whitespace-pre-wrap text-sm text-zinc-200">{m.body}</p>
              </div>
              {isCommissioner && (
                <div className="flex shrink-0 items-start gap-1">
                  {/* P5-W39: only the commissioner's own posts are pinnable;
                      pinning a new one unpins the old one */}
                  {m.team_id === myTeamId && (
                    <button
                      type="button"
                      onClick={() => pin(m.id)}
                      aria-label={`Pin post by ${m.team_name}`}
                      title="Pin as announcement (commissioner)"
                      className="rounded-md p-1.5 text-zinc-600 transition hover:bg-slate-800 hover:text-trophy-gold"
                    >
                      <Pin className="h-4 w-4" />
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => remove(m.id)}
                    aria-label={`Remove post by ${m.team_name}`}
                    title="Remove post (commissioner)"
                    className="rounded-md p-1.5 text-zinc-600 transition hover:bg-slate-800 hover:text-red-300"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
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
