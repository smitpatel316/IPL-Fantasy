"""Commissioner full-league export (P5-W43).

GET /api/leagues/{league_id}/export.json — the complete offline backup
for a league: settings, teams + rosters + weekly lineups, draft picks,
trades, waiver history, ledger (rendered rows per team via the P5-W28
projection), polls, and messages.

Commissioner-only: the caller passes their team id (query) and the
P4-W18 claim gate applies to the commissioner's team, so anyone else
403s. Claim codes are never exported. Read-only.
"""

import json
import sqlite3
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ..database import get_db
from . import get_league
from .ledger import _collect_raw
from .message_board import _require_commissioner_actor

router = APIRouter()


def _rows(con: sqlite3.Connection, sql: str, *args) -> list[dict]:
    return [dict(r) for r in con.execute(sql, args)]


@router.get("/{league_id}/export.json")
def export_league(league_id: int, team_id: int = Query(...),
                  request: Request = None,
                  con: sqlite3.Connection = Depends(get_db)):
    league = get_league(con, league_id)  # 404 if missing
    comm_team = _require_commissioner_actor(
        con, league, team_id, request, "export league data")

    players = {r["id"]: r["name"] for r in
               con.execute("SELECT id, name FROM players")}

    teams = []
    team_ids = []
    for t in con.execute(
            "SELECT t.*, u.name AS owner_name FROM teams t"
            " LEFT JOIN users u ON u.id = t.owner_id"
            " WHERE t.league_id = ? ORDER BY t.id", (league_id,)):
        teams.append({
            "id": t["id"], "name": t["name"], "owner_name": t["owner_name"],
            "faab_remaining": t["faab_remaining"],
            "claimed": t["claim_code"] is not None,
            "created_at": t["created_at"],
        })
        team_ids.append(t["id"])

    # Rosters: week_no NULL = construction roster; else weekly snapshots.
    rosters: dict[str, list] = {}
    weekly_lineups: dict[str, dict] = {}
    for r in con.execute(
            "SELECT team_id, player_id, slot, week_no FROM roster_slots"
            " WHERE team_id IN (%s)" % ",".join("?" * len(team_ids)),
            team_ids):
        entry = {"player_id": r["player_id"],
                 "player_name": players.get(r["player_id"], "Unknown player"),
                 "slot": r["slot"]}
        if r["week_no"] is None:
            rosters.setdefault(str(r["team_id"]), []).append(entry)
        else:
            weekly_lineups.setdefault(str(r["team_id"]), {}).setdefault(
                str(r["week_no"]), []).append(entry)

    draft = con.execute(
        "SELECT * FROM drafts WHERE league_id = ? ORDER BY id DESC LIMIT 1",
        (league_id,)).fetchone()
    draft_out = None
    if draft:
        draft_out = {
            "id": draft["id"],
            "draft_order": json.loads(draft["draft_order"] or "[]"),
            "rounds": draft["rounds"], "status": draft["status"],
            "current_pick_no": draft["current_pick_no"],
            "created_at": draft["created_at"],
            "picks": [
                {"pick_no": p["pick_no"], "round_no": p["round_no"],
                 "team_id": p["team_id"], "player_id": p["player_id"],
                 "player_name": players.get(p["player_id"], "Unknown player")
                 if p["player_id"] else None,
                 "is_auto": bool(p["is_auto"]), "picked_at": p["picked_at"]}
                for p in con.execute(
                    "SELECT * FROM draft_picks WHERE draft_id = ?"
                    " ORDER BY pick_no", (draft["id"],))
            ],
        }

    trades = [
        {k: (json.loads(t[k]) if k in ("gives", "receives", "legs")
             and t[k] else t[k])
         for k in ("id", "from_team_id", "to_team_id", "gives", "receives",
                   "status", "created_at", "review_deadline", "veto_count",
                   "executed_at", "kind", "legs")}
        for t in con.execute(
            "SELECT * FROM trades WHERE league_id = ? ORDER BY id", (league_id,))
    ]
    waiver_claims = _rows(
        con, "SELECT * FROM waiver_claims WHERE league_id = ? ORDER BY id",
        league_id)
    adjustments = _rows(
        con, "SELECT * FROM league_adjustments WHERE league_id = ? ORDER BY id",
        league_id)

    ledger = {str(tid): _collect_raw(con, league_id, tid) for tid in team_ids}

    polls = []
    for p in con.execute(
            "SELECT * FROM polls WHERE league_id = ? ORDER BY id", (league_id,)):
        options = _rows(
            con, "SELECT id, label, position FROM poll_options"
                 " WHERE poll_id = ? ORDER BY position", p["id"])
        votes = _rows(
            con, "SELECT team_id, option_id, created_at, updated_at"
                 " FROM poll_votes WHERE poll_id = ?", p["id"])
        polls.append({
            "id": p["id"], "team_id": p["team_id"],
            "question": p["question"], "created_at": p["created_at"],
            "closed_at": p["closed_at"], "options": options, "votes": votes,
        })

    messages = _rows(
        con, "SELECT id, team_id, body, created_at, deleted_at, pinned_at"
             " FROM league_messages WHERE league_id = ? ORDER BY id",
        league_id)

    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "exported_by_team_id": comm_team["id"],
        "league": {
            "id": league["id"], "name": league["name"],
            "invite_code": league["invite_code"],
            "commissioner_id": league["commissioner_id"],
            "commissioner_team_id": comm_team["id"],
            "season": league["season"],
            "settings": league["settings"] or {},
            "status": league["status"], "created_at": league["created_at"],
        },
        "teams": teams,
        "rosters": rosters,
        "weekly_lineups": weekly_lineups,
        "draft": draft_out,
        "trades": trades,
        "waiver_claims": waiver_claims,
        "league_adjustments": adjustments,
        "ledger": ledger,
        "polls": polls,
        "messages": messages,
    }
