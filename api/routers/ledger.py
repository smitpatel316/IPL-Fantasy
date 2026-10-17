"""Per-team FAAB & transaction ledger (P5-W28).

GET /api/leagues/{id}/teams/{team_id}/ledger — the managing team's
own auditable money trail, chronological with running FAAB balances:
starting $100 (D6), own waiver claims won (winning bid deducted) and
lost (no deduction), commissioner FAAB adjustments (labelled, balance
resynced to the recorded faab_after), commissioner roster fiat, and
executed trades touching the team.

D6 HARD RULE: a pending claim appears only as an amount-free
"pending" marker for its owning team; the endpoint is claim-gated
(require_team_actor, P4-W18) exactly like the notifications inbox, so
no other team can read it at all. Read-only projection over persisted
rows; no engine changes.
"""

import json
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request

from .. import schemas
from ..constants import FAAB_BUDGET
from ..database import get_db
from . import get_league, require_team_actor

router = APIRouter()


@router.get("/{league_id}/teams/{team_id}/ledger",
            response_model=schemas.TeamLedgerOut)
def get_ledger(league_id: int, team_id: int, request: Request = None,
               con: sqlite3.Connection = Depends(get_db)):
    league = get_league(con, league_id)  # 404 if missing
    team = require_team_actor(con, team_id, request)  # claim gate (P4-W18)
    if team["league_id"] != league_id:
        raise HTTPException(422, f"team {team_id} is not in league {league_id}")
    players = {r["id"]: r["name"] for r in con.execute("SELECT id, name FROM players")}
    teams = {r["id"]: r["name"] for r in con.execute(
        "SELECT id, name FROM teams WHERE league_id = ?", (league_id,))}

    def pname(pid):
        return players.get(pid, "Unknown player")

    raw: list[dict] = []
    for r in con.execute(
            """SELECT * FROM waiver_claims WHERE league_id = ? AND team_id = ?
               ORDER BY created_at, id""", (league_id, team_id)):
        add = pname(r["add_player_id"])
        drop = (f" (dropped {pname(r['drop_player_id'])})"
                if r["drop_player_id"] else "")
        if r["status"] == "won":
            raw.append({"id": f"waiver-{r['id']}", "kind": "waiver_won",
                        "text": f"Won {add} on waivers for ${r['bid']} — week {r['week_no']}{drop}",
                        "occurred_at": r["created_at"], "amount": r["bid"],
                        "faab_delta": -r["bid"]})
        elif r["status"] == "lost":
            raw.append({"id": f"waiver-{r['id']}", "kind": "waiver_lost",
                        "text": f"Waiver claim for {add} did not win — week {r['week_no']}",
                        "occurred_at": r["created_at"], "amount": r["bid"],
                        "faab_delta": 0})
        elif r["status"] == "pending":
            raw.append({"id": f"waiver-{r['id']}", "kind": "waiver_pending",
                        "text": f"Pending claim for {add} — week {r['week_no']} (amount sealed until the run)",
                        "occurred_at": r["created_at"], "amount": None,
                        "faab_delta": 0})
    for r in con.execute(
            """SELECT * FROM league_adjustments WHERE league_id = ? AND team_id = ?
               ORDER BY created_at, id""", (league_id, team_id)):
        if r["kind"] == "faab":
            delta = r["faab_delta"]
            raw.append({"id": f"adj-{r['id']}", "kind": "commissioner_faab",
                        "text": (f"Commissioner FAAB adjustment "
                                 f"{'+' if delta >= 0 else ''}{delta} — {r['note']}"),
                        "occurred_at": r["created_at"], "amount": None,
                        "faab_delta": delta, "balance_after": r["faab_after"]})
        elif r["kind"] in ("roster_add", "roster_drop"):
            verb = "added" if r["kind"] == "roster_add" else "dropped"
            raw.append({"id": f"adj-{r['id']}", "kind": f"commissioner_{r['kind']}",
                        "text": f"Commissioner {verb} {r['player_name']} — {r['note']}",
                        "occurred_at": r["created_at"], "amount": None,
                        "faab_delta": 0})
    for r in con.execute(
            """SELECT * FROM trades WHERE league_id = ? AND status = 'executed'
               AND (from_team_id = ? OR to_team_id = ?) ORDER BY created_at, id""",
            (league_id, team_id, team_id)):
        gives = ", ".join(pname(p) for p in json.loads(r["gives"] or "[]"))
        receives = ", ".join(pname(p) for p in json.loads(r["receives"] or "[]"))
        raw.append({"id": f"trade-{r['id']}", "kind": "trade_executed",
                    "text": (f"Trade with {teams.get(r['to_team_id'] if r['from_team_id'] == team_id else r['from_team_id'], 'another team')}: "
                             f"gave {gives}, received {receives}"),
                    "occurred_at": r["executed_at"] or r["created_at"],
                    "amount": None, "faab_delta": 0})

    raw.sort(key=lambda e: (e["occurred_at"], e["id"]))
    balance = FAAB_BUDGET
    entries = [schemas.LedgerEntryOut(
        id="start", kind="starting_balance",
        text=f"Starting FAAB budget (D6: ${FAAB_BUDGET})",
        occurred_at=raw[0]["occurred_at"] if raw else league["created_at"],
        amount=None, faab_delta=0, balance_after=balance)]
    for e in raw:
        if e.get("balance_after") is not None:
            balance = e["balance_after"]  # recorded commissioner balance wins
        else:
            balance += e["faab_delta"]
        entries.append(schemas.LedgerEntryOut(
            id=e["id"], kind=e["kind"], text=e["text"],
            occurred_at=e["occurred_at"], amount=e["amount"],
            faab_delta=e["faab_delta"], balance_after=balance))
    return schemas.TeamLedgerOut(
        league_id=league_id, team_id=team_id, team_name=team["name"],
        starting_faab=FAAB_BUDGET, current_faab=team["faab_remaining"],
        entries=entries)
