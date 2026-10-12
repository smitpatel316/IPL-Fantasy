"""Custom pre-draft ranks (P4-W17): per-team ordered player lists the
draft engine's auto-pick follows. Read/write here; the engine reads
them at draft build/revive, and a write during a live draft refreshes
the running draft's in-memory ranks (services.set_team_ranks)."""

import sqlite3

from fastapi import APIRouter, Depends

from .. import schemas, services
from ..database import get_db

router = APIRouter()


@router.get("/teams/{team_id}/ranks", response_model=schemas.RanksOut)
def get_ranks(team_id: int, con: sqlite3.Connection = Depends(get_db)):
    return schemas.RanksOut(
        team_id=team_id, player_ids=services.get_team_ranks(con, team_id))


@router.put("/teams/{team_id}/ranks", response_model=schemas.RanksOut)
def set_ranks(team_id: int, body: schemas.RanksIn,
              con: sqlite3.Connection = Depends(get_db)):
    return schemas.RanksOut(**services.set_team_ranks(con, team_id, body.player_ids))
