"""League strengths heatmap (P5-W33): role-by-role roster value
for every team — the at-a-glance scouting view before proposing
trades.

Read-only projection; no engine changes, no new valuation model.
Values use the exact P5-W9 power-rankings convention: consensus
pre_draft_ranks (MIN rank over the league's teams), pool of N
ranked players, value = N + 1 - rank (unranked = 0). Starters are
selected by the same seam as power rankings (saved week-1 lineup's
non-BN/IL slots when one exists, else the construction roster's
top 11 by value), so each row's total — the sum over ALL its
starters — is identical to the power-rankings roster_value for
the same DB state. Cells group those starters by their registered
role (a UTIL starter counts under his real role); a starter with
no registered role counts toward the total only.

Shade (pinned; fixture-tested): ratio = cell value / league
average at that role. >= 1.50 -> 2, >= 1.15 -> 1, <= 0.50 -> -2,
<= 0.85 -> -1, else 0. A league average of 0 shades every cell 0.
"""

import sqlite3

from fastapi import APIRouter, Depends

from .. import schemas
from ..database import get_db
from . import get_league, player_roles_map

router = APIRouter()

ROLES = ("WK", "BAT", "AR", "BOWL")


def _shade(value: int, average: float) -> int:
    if average <= 0:
        return 0
    ratio = value / average
    if ratio >= 1.50:
        return 2
    if ratio >= 1.15:
        return 1
    if ratio <= 0.50:
        return -2
    if ratio <= 0.85:
        return -1
    return 0


@router.get("/{league_id}/strengths",
            response_model=schemas.StrengthsOut)
def get_strengths(league_id: int,
                  con: sqlite3.Connection = Depends(get_db)):
    league = get_league(con, league_id)  # 404 if missing
    roles = player_roles_map(con, league["season"])
    ranks = {
        r["player_id"]: r["rank"]
        for r in con.execute(
            """SELECT r.player_id, MIN(r.rank) AS rank
               FROM pre_draft_ranks r JOIN teams t ON t.id = r.team_id
               WHERE t.league_id = ? GROUP BY r.player_id""", (league_id,))
    }
    pool = len(ranks)

    def value(pid: int) -> int:
        return pool + 1 - ranks[pid] if pid in ranks else 0

    teams = con.execute(
        "SELECT id, name FROM teams WHERE league_id = ?",
        (league_id,)).fetchall()
    drafted = bool(con.execute(
        """SELECT 1 FROM roster_slots rs JOIN teams t ON t.id = rs.team_id
           WHERE t.league_id = ? LIMIT 1""", (league_id,)).fetchone())

    per_team: list[tuple[int, str, dict[str, int], int]] = []
    for t in teams:
        tid = t["id"]
        starters = [
            r["player_id"] for r in con.execute(
                """SELECT player_id FROM roster_slots
                   WHERE team_id = ? AND week_no = 1
                     AND slot NOT IN ('BN', 'IL')""", (tid,))
        ]
        if not starters:
            roster = [
                r["player_id"] for r in con.execute(
                    "SELECT player_id FROM roster_slots"
                    " WHERE team_id = ? AND week_no IS NULL", (tid,))
            ]
            starters = sorted(roster, key=lambda p: -value(p))[:11]
        cells = {role: 0 for role in ROLES}
        total = 0
        for pid in starters:
            v = value(pid)
            total += v
            role = (roles.get(pid) or {}).get("role")
            if role in cells:
                cells[role] += v
        per_team.append((tid, t["name"], cells, total))

    n = len(per_team) or 1
    averages = {
        role: round(sum(c[role] for _, _, c, _ in per_team) / n, 4)
        for role in ROLES
    }
    rows = [
        schemas.StrengthRowOut(
            team_id=tid, team_name=name, total=total,
            cells=[schemas.StrengthCellOut(
                role=role, value=cells[role],
                shade=_shade(cells[role], averages[role]))
                for role in ROLES])
        for tid, name, cells, total in per_team
    ]
    rows.sort(key=lambda r: (-r.total, r.team_name.casefold(), r.team_id))
    return schemas.StrengthsOut(
        league_id=league_id, drafted=drafted,
        averages=averages, rows=rows)
