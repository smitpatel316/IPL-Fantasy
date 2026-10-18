"""Team notifications inbox (P5-W20): "For you" feed per team.

A claim-aware, per-team inbox backed by a read projection over events
already persisted in the DB, plus one persisted read marker
(notification_reads: league+team -> last_read_at):

  * trades proposed TO your team (still 'proposed'),
  * outcomes of trades you proposed or were offered: accepted /
    executed / vetoed for either party, rejected / expired for the
    proposer,
  * your own waiver claims won/lost once a run resolves them,
  * commissioner adjustments (FAAB / roster fiat) touching your team.

HARD CONSTRAINTS: persisted events only (no transient draft-clock
events); D6-safe — only the requesting team's own RESOLVED claim
outcomes ever appear, never another team's pending bid or amount,
and a losing claim carries no amount anywhere. Reads and mark-as-read
are gated by require_team_actor (P4-W18): once a team is claimed,
only its claim code can see or mark its inbox.
"""

import json
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from .. import schemas
from ..database import get_db
from . import get_league, get_team, require_team_actor

router = APIRouter()

ENSURE_SQL = """
CREATE TABLE IF NOT EXISTS notification_reads (
    league_id    INTEGER NOT NULL REFERENCES leagues(id) ON DELETE CASCADE,
    team_id      INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    last_read_at TEXT NOT NULL,
    PRIMARY KEY (league_id, team_id)
);
"""


def _ensure(con: sqlite3.Connection) -> None:
    con.execute(ENSURE_SQL)


def _entries(con: sqlite3.Connection, league_id: int,
             team_id: int) -> list[dict]:
    teams = {r["id"]: r["name"] for r in con.execute(
        "SELECT id, name FROM teams WHERE league_id = ?", (league_id,))}
    players = {r["id"]: r["name"] for r in con.execute(
        "SELECT id, name FROM players")}
    me = teams.get(team_id, f"Team {team_id}")
    out: list[dict] = []

    def names(ids_json: str) -> str:
        return ", ".join(
            players.get(p, "Unknown player") for p in json.loads(ids_json or "[]"))

    # --- trades involving this team ---
    for r in con.execute(
            """SELECT * FROM trades WHERE league_id = ?
               AND (from_team_id = ? OR to_team_id = ?)""",
            (league_id, team_id, team_id)):
        frm = teams.get(r["from_team_id"], f"Team {r['from_team_id']}")
        to = teams.get(r["to_team_id"], f"Team {r['to_team_id']}")
        other = to if r["from_team_id"] == team_id else frm
        swap = f"{names(r['gives'])} for {names(r['receives'])}"
        status = r["status"]
        kind = text = occurred = None
        if status == "proposed" and r["to_team_id"] == team_id:
            kind = "trade_proposed"
            text = f"{frm} proposed a trade to you: {swap}"
            occurred = r["proposed_at"] or r["created_at"]
        elif status in ("accepted", "executed"):
            kind = "trade_executed" if r["executed_at"] else "trade_accepted"
            verb = "executed" if r["executed_at"] else "accepted"
            text = f"Trade between {frm} and {to} was {verb}: {swap}"
            occurred = r["executed_at"] or r["accepted_at"] or r["created_at"]
        elif status == "vetoed":
            kind = "trade_vetoed"
            text = f"Trade between {frm} and {to} was vetoed ({r['veto_count']} vetoes): {swap}"
            occurred = r["vetoed_at"] or r["created_at"]
        elif status == "rejected" and r["from_team_id"] == team_id:
            kind = "trade_rejected"
            text = f"{other} rejected your trade proposal: {swap}"
            occurred = r["created_at"]
        elif status == "expired" and r["from_team_id"] == team_id:
            kind = "trade_expired"
            text = f"Your trade proposal to {other} expired: {swap}"
            occurred = r["created_at"]
        if kind:
            out.append({"id": f"trade-{r['id']}-{kind}", "kind": kind,
                        "text": text, "occurred_at": occurred})

    # --- own resolved waiver claims only (D6) ---
    for r in con.execute(
            """SELECT * FROM waiver_claims WHERE league_id = ? AND team_id = ?
               AND status IN ('won', 'lost')""", (league_id, team_id)):
        add = players.get(r["add_player_id"], "Unknown player")
        if r["status"] == "won":
            text = f"You won {add} on waivers for ${r['bid']} — week {r['week_no']}"
            if r["drop_player_id"]:
                text += f" (dropped {players.get(r['drop_player_id'], 'Unknown player')})"
            out.append({"id": f"waiver-{r['id']}", "kind": "waiver_won",
                        "text": text, "amount": r["bid"],
                        "occurred_at": r["created_at"]})
        else:
            out.append({"id": f"waiver-{r['id']}", "kind": "waiver_lost",
                        "text": f"Your waiver claim for {add} did not win — week {r['week_no']}",
                        "occurred_at": r["created_at"]})

    # --- commissioner adjustments touching this team ---
    for r in con.execute(
            """SELECT * FROM league_adjustments
               WHERE league_id = ? AND team_id = ?""", (league_id, team_id)):
        if r["kind"] == "roster_add":
            text = f"Commissioner added {r['player_name']} to your team — {r['note']}"
        elif r["kind"] == "roster_drop":
            text = f"Commissioner dropped {r['player_name']} from your team — {r['note']}"
        elif r["kind"] == "lineup_set":
            # P5-W42: commissioner set this team's lineup with an audit note.
            text = f"Commissioner set your lineup — {r['note']}"
        else:
            delta = r["faab_delta"]
            text = (f"Commissioner adjusted your FAAB by "
                    f"{'+' if delta >= 0 else ''}{delta} (now ${r['faab_after']}) — {r['note']}")
        out.append({"id": f"adj-{r['id']}", "kind": f"commissioner_{r['kind']}",
                    "text": text, "occurred_at": r["created_at"]})

    out.sort(key=lambda e: (e["occurred_at"], e["id"]), reverse=True)
    return out


def _last_read(con: sqlite3.Connection, league_id: int, team_id: int):
    row = con.execute(
        "SELECT last_read_at FROM notification_reads"
        " WHERE league_id = ? AND team_id = ?",
        (league_id, team_id)).fetchone()
    return row["last_read_at"] if row else None


def _check_team(con, league_id: int, team_id: int, request) -> dict:
    get_league(con, league_id)
    team = require_team_actor(con, team_id, request)
    if team["league_id"] != league_id:
        raise HTTPException(422, f"team {team_id} is not in league {league_id}")
    return team


@router.get("/{league_id}/notifications",
            response_model=schemas.NotificationsOut)
def get_notifications(league_id: int, team_id: int = Query(...),
                      request: Request = None,
                      con: sqlite3.Connection = Depends(get_db)):
    """This team's inbox, newest first, with per-entry read flags."""
    _ensure(con)
    _check_team(con, league_id, team_id, request)
    last_read = _last_read(con, league_id, team_id)
    entries = []
    unread = 0
    for e in _entries(con, league_id, team_id):
        read = last_read is not None and e["occurred_at"] <= last_read
        if not read:
            unread += 1
        entries.append(schemas.NotificationEntryOut(
            id=e["id"], kind=e["kind"], text=e["text"],
            amount=e.get("amount"), occurred_at=e["occurred_at"],
            read=read))
    return schemas.NotificationsOut(
        league_id=league_id, team_id=team_id, total=len(entries),
        unread_count=unread, entries=entries)


@router.post("/{league_id}/notifications/read",
             response_model=schemas.NotificationsOut)
def mark_read(league_id: int, team_id: int = Query(...),
              request: Request = None,
              con: sqlite3.Connection = Depends(get_db)):
    """Claim-gated mark-as-read: stamps the marker at the newest
    event's timestamp (or now when the inbox is empty), so the unread
    count flips to zero and later events become unread again."""
    _ensure(con)
    _check_team(con, league_id, team_id, request)
    entries = _entries(con, league_id, team_id)
    marker = entries[0]["occurred_at"] if entries else None
    if marker is None:
        marker = con.execute("SELECT datetime('now') AS n").fetchone()["n"]
    con.execute(
        """INSERT INTO notification_reads (league_id, team_id, last_read_at)
           VALUES (?, ?, ?)
           ON CONFLICT (league_id, team_id)
           DO UPDATE SET last_read_at = excluded.last_read_at""",
        (league_id, team_id, marker))
    con.commit()
    return get_notifications(league_id, team_id, request, con)
