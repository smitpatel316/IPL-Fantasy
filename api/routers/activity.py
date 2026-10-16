"""League activity feed (P5-W8): read-only chronological projection.

GET /api/leagues/{id}/activity projects events already recorded in
the DB into one newest-first feed: completed draft picks, waiver-run
outcomes, executed/vetoed trades, and commissioner adjustments
(league_adjustments audit rows). No new event writes — if an event
was never recorded, it cannot appear here (IL moves, for instance,
leave no timestamped record in the schema, so they are absent by
design rather than fabricated).

HARD INVARIANT (D6, the P4-W2 lesson): pending waiver claims never
appear at all, and neither do losing bids' amounts — a bid becomes
public only when its claim WINS the Wednesday run, so won entries
carry the winning bid and lost entries carry no amount anywhere.
"""

import json
import sqlite3

from fastapi import APIRouter, Depends, Query

from .. import schemas
from ..database import get_db
from . import get_league

router = APIRouter()


def _entries(con: sqlite3.Connection,
             league_id: int) -> list[schemas.ActivityEntryOut]:
    teams = {r["id"]: r["name"] for r in con.execute(
        "SELECT id, name FROM teams WHERE league_id = ?", (league_id,))}
    players = {r["id"]: r["name"] for r in con.execute(
        "SELECT id, name FROM players")}
    out: list[schemas.ActivityEntryOut] = []

    # --- completed draft picks (drafts carry the league) ---
    for r in con.execute(
            """SELECT dp.id, dp.pick_no, dp.round_no, dp.team_id,
                      dp.player_id, dp.is_auto, dp.picked_at
               FROM draft_picks dp JOIN drafts d ON d.id = dp.draft_id
               WHERE d.league_id = ?""", (league_id,)):
        team = teams.get(r["team_id"], f"Team {r['team_id']}")
        player = players.get(r["player_id"], "Unknown player")
        text = (f"{team} drafted {player} — pick {r['pick_no']}"
                f" (round {r['round_no']})")
        if r["is_auto"]:
            text += " · auto-pick"
        out.append(schemas.ActivityEntryOut(
            id=f"pick-{r['id']}", kind="draft_pick", text=text,
            team_id=r["team_id"], team_name=team,
            player_id=r["player_id"], player_name=player,
            occurred_at=r["picked_at"]))

    # --- waiver-run outcomes (resolved claims only; pending = sealed)
    for r in con.execute(
            """SELECT id, week_no, team_id, add_player_id,
                      drop_player_id, bid, status, created_at
               FROM waiver_claims
               WHERE league_id = ? AND status IN ('won', 'lost')""",
            (league_id,)):
        team = teams.get(r["team_id"], f"Team {r['team_id']}")
        add = players.get(r["add_player_id"], "Unknown player")
        if r["status"] == "won":
            text = f"{team} won {add} on waivers for ${r['bid']}"
            if r["drop_player_id"]:
                drop = players.get(r["drop_player_id"], "Unknown player")
                text += f" (dropped {drop})"
            text += f" — week {r['week_no']}"
            out.append(schemas.ActivityEntryOut(
                id=f"waiver-{r['id']}", kind="waiver_won", text=text,
                team_id=r["team_id"], team_name=team,
                player_id=r["add_player_id"], player_name=add,
                amount=r["bid"], occurred_at=r["created_at"]))
        else:
            # No amount: losing bids stay sealed even after the run.
            text = f"{team}'s waiver claim for {add} did not win — week {r['week_no']}"
            out.append(schemas.ActivityEntryOut(
                id=f"waiver-{r['id']}", kind="waiver_lost", text=text,
                team_id=r["team_id"], team_name=team,
                player_id=r["add_player_id"], player_name=add,
                occurred_at=r["created_at"]))

    # --- executed / vetoed trades (lifecycle timestamps, P4-W1) ---
    for r in con.execute(
            """SELECT id, from_team_id, to_team_id, gives, receives,
                      status, veto_count, vetoed_at, executed_at
               FROM trades WHERE league_id = ?
                 AND status IN ('executed', 'vetoed')""", (league_id,)):
        frm = teams.get(r["from_team_id"], f"Team {r['from_team_id']}")
        to = teams.get(r["to_team_id"], f"Team {r['to_team_id']}")

        def names(ids_json: str) -> str:
            return ", ".join(
                players.get(p, "Unknown player") for p in json.loads(ids_json))

        if r["status"] == "executed" and r["executed_at"]:
            text = (f"Trade executed: {frm} sent {names(r['gives'])} to {to}"
                    f" for {names(r['receives'])}")
            out.append(schemas.ActivityEntryOut(
                id=f"trade-{r['id']}", kind="trade_executed", text=text,
                team_id=r["from_team_id"], team_name=frm,
                occurred_at=r["executed_at"]))
        elif r["status"] == "vetoed" and r["vetoed_at"]:
            text = (f"Trade vetoed ({r['veto_count']} vetoes): {frm} ↔ {to}"
                    f" — {names(r['gives'])} for {names(r['receives'])}")
            out.append(schemas.ActivityEntryOut(
                id=f"trade-{r['id']}", kind="trade_vetoed", text=text,
                team_id=r["from_team_id"], team_name=frm,
                occurred_at=r["vetoed_at"]))

    # --- commissioner adjustments (audit rows, P4-W15/W25) ---
    for r in con.execute(
            """SELECT id, team_id, kind, faab_delta, faab_after,
                      player_id, player_name, note, created_at
               FROM league_adjustments WHERE league_id = ?""", (league_id,)):
        team = teams.get(r["team_id"], f"Team {r['team_id']}")
        if r["kind"] == "roster_add":
            text = f"Commissioner added {r['player_name']} to {team} — {r['note']}"
        elif r["kind"] == "roster_drop":
            text = f"Commissioner dropped {r['player_name']} from {team} — {r['note']}"
        else:
            delta = r["faab_delta"]
            text = (f"Commissioner adjusted {team}'s FAAB by "
                    f"{'+' if delta >= 0 else ''}{delta} "
                    f"(now ${r['faab_after']}) — {r['note']}")
        out.append(schemas.ActivityEntryOut(
            id=f"adj-{r['id']}", kind=f"commissioner_{r['kind']}", text=text,
            team_id=r["team_id"], team_name=team,
            player_id=r["player_id"], player_name=r["player_name"],
            occurred_at=r["created_at"]))

    # Newest first; row id within a kind breaks same-second ties so
    # the order is deterministic for a given DB state.
    out.sort(key=lambda e: (e.occurred_at, e.id), reverse=True)
    return out


@router.get("/{league_id}/activity", response_model=schemas.ActivityOut)
def get_activity(league_id: int, limit: int = Query(50, ge=1, le=100),
                 offset: int = Query(0, ge=0),
                 con: sqlite3.Connection = Depends(get_db)):
    """Newest-first league activity. `total` counts every projected
    event so the UI can page older entries in."""
    get_league(con, league_id)  # 404 if missing
    entries = _entries(con, league_id)
    return schemas.ActivityOut(
        league_id=league_id, total=len(entries),
        entries=entries[offset:offset + limit])
