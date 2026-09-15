"""Matchups + scoreboard reads. Scheduling/finalization is P2-L5; scoring is the
data track's scorer (phase1/scorer.py) wired via POST /api/admin/score-match."""

import json
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query

from .. import schemas
from ..database import get_db
from . import get_league

router = APIRouter()


@router.get("", response_model=list[schemas.MatchupOut])
def list_matchups(league_id: int = Query(...), week_no: int = Query(...),
                  con: sqlite3.Connection = Depends(get_db)):
    get_league(con, league_id)
    out = []
    for r in con.execute(
        """SELECT m.*, ta.name AS a_name, tb.name AS b_name FROM matchups m
           JOIN teams ta ON ta.id = m.team_a_id
           JOIN teams tb ON tb.id = m.team_b_id
           WHERE m.league_id = ? AND m.week_no = ? ORDER BY m.id""",
        (league_id, week_no),
    ):
        out.append(schemas.MatchupOut(
            id=r["id"], week_no=r["week_no"], team_a_id=r["team_a_id"],
            team_b_id=r["team_b_id"], team_a_name=r["a_name"], team_b_name=r["b_name"],
            score_a=r["score_a"], score_b=r["score_b"], status=r["status"],
        ))
    return out


@router.get("/scoreboard/{match_id}", response_model=schemas.ScoreboardOut)
def scoreboard(match_id: int, con: sqlite3.Connection = Depends(get_db)):
    m = con.execute("SELECT * FROM matches WHERE id = ?", (match_id,)).fetchone()
    if not m:
        raise HTTPException(404, f"match {match_id} not found")
    scores = [
        schemas.PlayerScoreOut(
            player_name=r["player_name"], fantasy_points=r["fantasy_points"],
            breakdown=json.loads(r["breakdown"] or "{}"),
        )
        for r in con.execute(
            "SELECT player_name, fantasy_points, breakdown FROM player_match_stats"
            " WHERE match_id = ? ORDER BY fantasy_points DESC", (match_id,)
        )
    ]
    return schemas.ScoreboardOut(match_id=match_id, status=m["status"], scores=scores)
