"""P5-L1: POST /api/mock-draft/{league_id} — ephemeral practice drafts.

Read-only against the live league: the universe, role metadata, and
consensus ranks are SELECTed from the league's own tables; the draft
itself runs entirely in memory via api/engine/mock_draft.py and NOTHING
is written back (no drafts/teams/players rows, no engine_state). The
live league cannot be touched by a mock draft by construction.

Bot difficulties are the locked two-level ladder ("casual" | "sharp");
the engine rejects anything else. Default bots = 8, alternating
sharp/casual starting sharp, so the difficulty-divergence acceptance
holds out of the box. Default seed = 42 (deterministic); pass an
explicit seed to rerun a variant.
"""

import random
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query

from .. import schemas
from ..constants import DRAFT_ROUNDS
from ..database import get_db
from ..engine import mock_draft
from ..engine.draft_engine import DraftError
from .. import schedule_games
from . import get_league

router = APIRouter()

DEFAULT_BOT_COUNT = 8
DEFAULT_SEED = 42
WEIGHT_WEEKS = (1, 2, 3)


def _consensus_pool(con: sqlite3.Connection, league_id: int,
                    season: str) -> tuple[list, dict, dict, dict]:
    """(pool, roles, ipl_team_of, names) — pool best-first by consensus rank.

    Consensus rank = MIN(pre_draft_ranks.rank) across the league's teams
    (the league ADP proxy); name tiebreak. Only players with role
    metadata join the pool so bots draft D8-legal rosters.
    """
    league_teams = [r[0] for r in con.execute(
        "SELECT id FROM teams WHERE league_id = ?", (league_id,)).fetchall()]
    if not league_teams:
        raise HTTPException(422, f"league {league_id} has no teams to rank from")
    placeholders = ",".join("?" for _ in league_teams)
    rank_rows = con.execute(
        f"""SELECT r.player_id, MIN(r.rank) AS c_rank
            FROM pre_draft_ranks r
            JOIN teams t ON t.id = r.team_id
            WHERE t.league_id = ? GROUP BY r.player_id""",
        (league_id,)).fetchall()
    consensus = {r[0]: r[1] for r in rank_rows}
    meta = {}
    for pid, role, os_, code, name in con.execute(
        """SELECT p.id, pr.role, pr.is_overseas, pr.ipl_team_code, p.name
           FROM players p JOIN player_roles pr ON pr.player_id = p.id
           WHERE p.season = ? AND pr.season = ?""",
        (season, season)).fetchall():
        if pid in consensus:
            meta[pid] = (role, bool(os_), code, name)
    pool = sorted(meta, key=lambda pid: (consensus[pid], meta[pid][3]))
    roles = {pid: {"role": m[0], "is_overseas": m[1]} for pid, m in meta.items()}
    ipl_team_of = {pid: m[2] for pid, m in meta.items() if m[2]}
    names = {pid: m[3] for pid, m in meta.items()}
    return pool, roles, ipl_team_of, names


def _schedule_games(con: sqlite3.Connection, season: str) -> dict:
    """ipl_team_code -> total games over the sharp-weight weeks."""
    totals: dict = {}
    for w in WEIGHT_WEEKS:
        data = schedule_games.fetch_week(con, season, w)
        for g in data.get("games", []):
            totals[g["ipl_team_code"]] = totals.get(g["ipl_team_code"], 0) + g["games"]
    return totals


@router.post("/{league_id}", response_model=schemas.MockDraftOut)
def run_mock_draft(league_id: int, body: schemas.MockDraftIn,
                   con: sqlite3.Connection = Depends(get_db)):
    """Spawn an ephemeral mock draft for league_id. SELECT-only + memory."""
    league = get_league(con, league_id)  # 404 if missing
    season = league.get("season") or "2027"

    bots = body.bots
    if not bots:
        bots = [schemas.MockBotIn(
            name=f"Bot {i + 1}",
            difficulty="sharp" if i % 2 == 0 else "casual")
            for i in range(DEFAULT_BOT_COUNT)]
    names_in = [b.name.strip() for b in bots]
    if any(not n for n in names_in):
        raise HTTPException(422, "bot names must be non-empty")
    if len(set(names_in)) != len(names_in):
        raise HTTPException(422, "bot names must be unique")
    if not 2 <= len(bots) <= 10:
        raise HTTPException(422, "mock draft needs 2-10 bots")
    difficulties = dict(zip(names_in, (b.difficulty for b in bots)))
    # Fail fast on an invalid difficulty with a 422 (engine would too).
    bad = [n for n, d in difficulties.items() if d not in mock_draft.BOT_DIFFICULTIES]
    if bad:
        raise HTTPException(
            422,
            f"invalid difficulty for bot(s) {bad}: locked ladder is "
            f"{list(mock_draft.BOT_DIFFICULTIES)}")

    pool, roles, ipl_team_of, pnames = _consensus_pool(con, league_id, season)
    needed = len(bots) * DRAFT_ROUNDS
    if len(pool) < needed:
        raise HTTPException(
            422,
            f"not enough ranked role-metadata players for a mock draft: "
            f"{len(pool)} available, {needed} needed ({len(bots)} bots x "
            f"{DRAFT_ROUNDS} rounds)")

    games = _schedule_games(con, season)
    seed = body.seed if body.seed is not None else DEFAULT_SEED
    teams = [(n, n) for n in names_in]
    try:
        report = mock_draft.run_mock_draft(
            pool=pool, roles=roles, teams=teams, difficulties=difficulties,
            rounds=DRAFT_ROUNDS, seed=seed,
            ipl_team_of=ipl_team_of, games_per_team=games)
    except DraftError as e:
        raise HTTPException(422, str(e))

    key_by_name = {t["name"]: t for t in report["teams"]}
    out_teams = [
        schemas.MockTeamOut(
            name=t["name"], difficulty=t["difficulty"],
            avg_consensus_rank=report["avg_consensus_rank"][t["name"]],
            roster={slot: [pnames[pid] for pid in pids]
                    for slot, pids in report["rosters"][t["name"]].items()})
        for t in report["teams"]
    ]
    out_picks = [
        schemas.MockPickOut(
            pick_no=p["pick_no"], round_no=p["round_no"],
            team_name=p["team_key"], difficulty=difficulties[p["team_key"]],
            player_id=p["player_id"], player_name=pnames[p["player_id"]],
            slot=p["slot"])
        for p in report["picks"]
    ]
    return schemas.MockDraftOut(
        league_id=league_id, seed=seed, rounds=DRAFT_ROUNDS,
        draft_order=report["draft_order"], teams=out_teams,
        picks=out_picks, schedule_weighted=bool(games))
