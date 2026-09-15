"""Admin: scoring trigger. The scorer itself is the data track's phase1/scorer.py
(Dream11-official §3, QA-cleared); this endpoint is the idempotent trigger seam.

SEAM (data track, Phase 3): wire score-match to the scorecard poller — fetch the
completed match's ball-by-ball, run score_player_match per player, upsert into
player_match_stats with breakdown JSON. Must stay idempotent (re-running a
match never double-counts)."""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from .. import schemas
from ..database import get_db

router = APIRouter()


@router.post("/score-match", response_model=schemas.NotImplementedOut, status_code=501)
def score_match(body: schemas.ScoreMatchIn, con: sqlite3.Connection = Depends(get_db)):
    if not con.execute("SELECT 1 FROM matches WHERE id = ?", (body.match_id,)).fetchone():
        raise HTTPException(404, f"match {body.match_id} not found")
    # Phase 3 (data track): poller -> scorer -> player_match_stats upsert.
    return schemas.NotImplementedOut(
        detail="scoring job not wired in scaffold; scorer lives in phase1/scorer.py",
        track="P3-data",
    )
