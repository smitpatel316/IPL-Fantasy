"""Season-start checklist / draft-day readiness (P5-W10).

GET /api/leagues/{id}/readiness derives every item from real DB
state at request time — no stored flags, no writes:

  league_created    the league row exists (this endpoint 404s before)
  teams_filled      teams joined vs the league's target size:
                    settings.num_teams when the commissioner set one,
                    else the draft's team count once a draft exists,
                    else still open (detail says how many have joined)
  teams_claimed     every team has a claim code (P4-W18 identity)
  custom_ranks      at least one team's pre_draft_ranks order differs
                    from the league consensus order (i.e. a manager
                    actually customized instead of taking defaults)
  draft_started     a draft row exists for the league
  draft_complete    the draft is complete (or the league is in season)
  week1_lineups     every team has a saved week-1 lineup
  waiver_armed      settings carry a waiver_run_weekday — the exact
                    key the in-app waiver scheduler (P4-W16) reads

Each item carries a fix_href to the surface that resolves it.
"""

import sqlite3

from fastapi import APIRouter, Depends

from .. import schemas
from ..database import get_db
from . import get_league

router = APIRouter()


def _items(con: sqlite3.Connection, league: dict) -> list[schemas.ReadinessItemOut]:
    lid = league["id"]
    settings = league.get("settings") or {}
    teams = con.execute(
        "SELECT id, name, claim_code FROM teams WHERE league_id = ?"
        " ORDER BY id", (lid,)).fetchall()
    team_ids = [t["id"] for t in teams]
    items: list[schemas.ReadinessItemOut] = []

    items.append(schemas.ReadinessItemOut(
        key="league_created", label="League created", done=True,
        detail=f"{league['name']} · season {league['season']} · status {league['status']}",
        fix_href=f"/league/{lid}"))

    draft = con.execute(
        "SELECT id, status, draft_order FROM drafts WHERE league_id = ?"
        " ORDER BY id DESC LIMIT 1", (lid,)).fetchone()
    target = settings.get("num_teams")
    if not target and draft:
        try:
            import json
            target = len(json.loads(draft["draft_order"] or "[]")) or None
        except (ValueError, TypeError):
            target = None
    if target:
        filled = len(team_ids) >= int(target)
        detail = f"{len(team_ids)}/{target} teams joined"
    else:
        filled = False
        detail = (f"{len(team_ids)} team(s) joined so far — share the invite"
                  " code; the draft can start once your managers are in")
    items.append(schemas.ReadinessItemOut(
        key="teams_filled", label="All team slots filled", done=filled,
        detail=detail, fix_href=f"/league/{lid}"))

    claimed = sum(1 for t in teams if t["claim_code"])
    items.append(schemas.ReadinessItemOut(
        key="teams_claimed", label="Every team claimed by its manager",
        done=bool(teams) and claimed == len(teams),
        detail=f"{claimed}/{len(teams)} teams claimed (claim codes set)",
        fix_href=f"/league/{lid}"))

    custom = 0
    if team_ids:
        consensus = [
            r["player_id"] for r in con.execute(
                """SELECT r.player_id FROM pre_draft_ranks r
                   JOIN teams t ON t.id = r.team_id
                   WHERE t.league_id = ? GROUP BY r.player_id
                   ORDER BY MIN(r.rank)""", (lid,))
        ]
        for tid in team_ids:
            mine = [
                r["player_id"] for r in con.execute(
                    "SELECT player_id FROM pre_draft_ranks"
                    " WHERE team_id = ? ORDER BY rank", (tid,))
            ]
            if mine and mine != consensus[:len(mine)]:
                custom += 1
    items.append(schemas.ReadinessItemOut(
        key="custom_ranks", label="Custom pre-draft ranks set",
        done=custom >= 1,
        detail=(f"{custom} team(s) have customized their ranks"
                if custom else "No team has customized its ranks yet — "
                "auto-picks will follow the league consensus"),
        fix_href=f"/draft-room/{lid}"))

    items.append(schemas.ReadinessItemOut(
        key="draft_started", label="Draft started", done=draft is not None,
        detail=(f"Draft is {draft['status']}" if draft
                else "No draft yet — start it from the draft room"),
        fix_href=f"/draft-room/{lid}"))

    complete = bool(draft and draft["status"] == "complete") \
        or league["status"] in ("in_season", "complete")
    items.append(schemas.ReadinessItemOut(
        key="draft_complete", label="Draft complete", done=complete,
        detail=("Draft finished — rosters are set" if complete
                else "Draft has not finished yet"),
        fix_href=f"/draft-room/{lid}"))

    with_lineup = 0
    for tid in team_ids:
        n = con.execute(
            "SELECT COUNT(*) FROM roster_slots"
            " WHERE team_id = ? AND week_no = 1", (tid,)).fetchone()[0]
        if n > 0:
            with_lineup += 1
    items.append(schemas.ReadinessItemOut(
        key="week1_lineups", label="Week-1 lineups saved for every team",
        done=bool(teams) and with_lineup == len(teams),
        detail=f"{with_lineup}/{len(teams)} teams have a saved week-1 lineup",
        fix_href="/lineup"))

    weekday = settings.get("waiver_run_weekday")
    items.append(schemas.ReadinessItemOut(
        key="waiver_armed", label="Waiver schedule armed",
        done=bool(weekday),
        detail=(f"Weekly FAAB runs on {weekday} (~3am PT, in-app scheduler)"
                if weekday else
                "No waiver_run_weekday in league settings — the Wednesday"
                " run will not fire"),
        fix_href="/waivers"))

    return items


@router.get("/{league_id}/readiness", response_model=schemas.ReadinessOut)
def get_readiness(league_id: int, con: sqlite3.Connection = Depends(get_db)):
    league = get_league(con, league_id)  # 404 if missing
    items = _items(con, league)
    return schemas.ReadinessOut(
        league_id=league_id,
        ready_count=sum(1 for i in items if i.done),
        total_count=len(items), items=items)
