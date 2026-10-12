"""Playoffs: read-model projection of the P2-L6 bracket (P4-W6).

The playoff engine (api/engine/playoff_engine.py) owns the bracket
rules; this endpoint projects them from SQL state so the playoffs page
renders something real at every point of the season:

  * Seeds are the top 4 of the REGULAR-SEASON standings (weeks 1–6
    finals only — playoff results never move a seed), ordered wins,
    then points-for, then team id desc, matching services'
    standings_best_first. Until every week-6 game is final the seeds
    are a live projection (``seeds_final`` is False).
  * Semifinals are the engine's fixed pairings: 1v4, 2v3 in week 7.
  * Week-7/8 matchup rows don't exist yet (scoring lands through the
    admin seam); when they do, games adopt the rows' scores/status and
    winners are derived — a tied playoff game goes to the better seed,
    the engine's documented tiebreak. Unmatched week-7/8 rows (e.g. a
    future consolation game) are ignored by the bracket.
  * The final pairs the semifinal winners, the third-place game the
    losers; until the semis are final both show as placeholders.
"""

import sqlite3

from fastapi import APIRouter, Depends

from .. import schemas
from ..database import get_db
from ..engine.playoff_engine import FINAL_WEEK, SEMIFINAL_WEEK
from . import get_league

router = APIRouter()

REGULAR_SEASON_LAST_WEEK = 6  # D9: 6 round-robin weeks, playoffs 7–8


def _regular_season_records(con: sqlite3.Connection, league_id: int) -> list[dict]:
    """All teams with W-L-T / points-for from weeks 1–6 finals, best first."""
    out = []
    for t in con.execute(
        "SELECT id, name FROM teams WHERE league_id = ?", (league_id,)
    ):
        w = con.execute(
            """SELECT
                 SUM(CASE WHEN (team_a_id = ? AND score_a > score_b) OR (team_b_id = ? AND score_b > score_a) THEN 1 ELSE 0 END),
                 SUM(CASE WHEN (team_a_id = ? AND score_a < score_b) OR (team_b_id = ? AND score_b < score_a) THEN 1 ELSE 0 END),
                 SUM(CASE WHEN score_a = score_b AND (team_a_id = ? OR team_b_id = ?) THEN 1 ELSE 0 END),
                 SUM(CASE WHEN team_a_id = ? THEN score_a WHEN team_b_id = ? THEN score_b ELSE 0 END)
               FROM matchups
               WHERE league_id = ? AND status = 'final' AND week_no <= ?""",
            (t["id"], t["id"], t["id"], t["id"], t["id"], t["id"], t["id"], t["id"],
             league_id, REGULAR_SEASON_LAST_WEEK),
        ).fetchone()
        out.append({
            "team_id": t["id"], "team_name": t["name"],
            "wins": w[0] or 0, "losses": w[1] or 0, "ties": w[2] or 0,
            "points_for": w[3] or 0.0,
        })
    out.sort(key=lambda r: (-r["wins"], -r["points_for"], -r["team_id"]))
    return out


def _regular_season_complete(con: sqlite3.Connection, league_id: int) -> bool:
    row = con.execute(
        "SELECT COUNT(*) AS n, SUM(CASE WHEN status = 'final' THEN 1 ELSE 0 END) AS f"
        " FROM matchups WHERE league_id = ? AND week_no = ?",
        (league_id, REGULAR_SEASON_LAST_WEEK),
    ).fetchone()
    return bool(row["n"]) and row["f"] == row["n"]


def _week_rows(con: sqlite3.Connection, league_id: int, week_no: int) -> list:
    return con.execute(
        "SELECT * FROM matchups WHERE league_id = ? AND week_no = ?",
        (league_id, week_no),
    ).fetchall()


def _winner(row, seed_rank: dict[int, int]) -> int | None:
    """Winner of a final matchup row; a tie goes to the better seed."""
    if row["status"] != "final":
        return None
    if row["score_a"] > row["score_b"]:
        return row["team_a_id"]
    if row["score_b"] > row["score_a"]:
        return row["team_b_id"]
    a, b = row["team_a_id"], row["team_b_id"]
    return a if seed_rank.get(a, 99) <= seed_rank.get(b, 99) else b


def _game(label: str, week_no: int,
          a: tuple[int | None, str], b: tuple[int | None, str],
          row, names: dict[int, str],
          seed_rank: dict[int, int]) -> schemas.PlayoffGameOut:
    """One bracket game. ``a``/``b`` are the projected (team_id, label)
    pair used until a real matchup row exists; a row's own orientation
    and scores win once it does."""
    if row is not None:
        return schemas.PlayoffGameOut(
            label=label, week_no=week_no,
            team_a_id=row["team_a_id"], team_a_label=names[row["team_a_id"]],
            team_b_id=row["team_b_id"], team_b_label=names[row["team_b_id"]],
            score_a=row["score_a"], score_b=row["score_b"],
            status="final" if row["status"] == "final" else "scheduled",
            winner_team_id=_winner(row, seed_rank),
        )
    status = "scheduled" if (a[0] is not None and b[0] is not None) else "projected"
    return schemas.PlayoffGameOut(
        label=label, week_no=week_no,
        team_a_id=a[0], team_a_label=a[1],
        team_b_id=b[0], team_b_label=b[1], status=status,
    )


@router.get("/{league_id}/playoffs", response_model=schemas.PlayoffsOut)
def get_playoffs(league_id: int, con: sqlite3.Connection = Depends(get_db)):
    get_league(con, league_id)  # 404 if missing
    records = _regular_season_records(con, league_id)
    names = {r["team_id"]: r["team_name"] for r in records}
    seeds = [schemas.PlayoffSeedOut(seed=i + 1, **r)
             for i, r in enumerate(records[:4])]
    seed_rank = {s.team_id: s.seed for s in seeds}
    rs_done = _regular_season_complete(con, league_id)

    semifinals: list[schemas.PlayoffGameOut] = []
    sf_winners: list[int | None] = [None, None]
    sf_losers: list[int | None] = [None, None]
    final = third = None
    champion_id = None
    if len(seeds) == 4:
        pairings = [(seeds[0], seeds[3]), (seeds[1], seeds[2])]  # engine: 1v4, 2v3
        rows7 = _week_rows(con, league_id, SEMIFINAL_WEEK)
        for i, (sa, sb) in enumerate(pairings):
            row = next(
                (r for r in rows7
                 if {r["team_a_id"], r["team_b_id"]} == {sa.team_id, sb.team_id}),
                None,
            )
            game = _game(
                f"Semifinal {i + 1}", SEMIFINAL_WEEK,
                (sa.team_id, sa.team_name), (sb.team_id, sb.team_name),
                row, names, seed_rank,
            )
            semifinals.append(game)
            if game.winner_team_id is not None:
                sf_winners[i] = game.winner_team_id
                sf_losers[i] = (
                    sb.team_id if game.winner_team_id == sa.team_id else sa.team_id
                )

        rows8 = _week_rows(con, league_id, FINAL_WEEK)

        def _row_for(pair) -> object:
            if pair[0] is None or pair[1] is None:
                return None
            return next(
                (r for r in rows8
                 if {r["team_a_id"], r["team_b_id"]} == {pair[0], pair[1]}),
                None,
            )

        final = _game(
            "Final", FINAL_WEEK,
            (sf_winners[0], names.get(sf_winners[0], "Winner of Semifinal 1")),
            (sf_winners[1], names.get(sf_winners[1], "Winner of Semifinal 2")),
            _row_for((sf_winners[0], sf_winners[1])), names, seed_rank,
        )
        champion_id = final.winner_team_id
        third = _game(
            "Third-place game", FINAL_WEEK,
            (sf_losers[0], names.get(sf_losers[0], "Loser of Semifinal 1")),
            (sf_losers[1], names.get(sf_losers[1], "Loser of Semifinal 2")),
            _row_for((sf_losers[0], sf_losers[1])), names, seed_rank,
        )

    if not rs_done:
        stage = "regular_season"
    elif not all(g.status == "final" for g in semifinals):
        stage = "semifinals"
    elif final is None or final.status != "final":
        stage = "final"
    else:
        stage = "complete"

    return schemas.PlayoffsOut(
        league_id=league_id, stage=stage, seeds_final=rs_done, seeds=seeds,
        semifinals=semifinals, final=final, third_place=third,
        champion_team_id=champion_id,
        champion_team_name=names.get(champion_id) if champion_id else None,
    )
