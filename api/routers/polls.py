"""League polls (P5-W24): quick advisory votes, companion to the
P5-W5 message board — the league can talk AND take a vote (e.g. on a
draft date before the Mar-2027 draft).

Any claimed team can create a poll (question + 2–6 options); each
team gets ONE vote and may change it while the poll is open; voting
is claim-aware per P4-W18 (require_team_actor — a second team cannot
vote as the first). Results are counts + percentages of votes cast.
The creator or the commissioner can close a poll; closed polls
reject further votes (422). ADVISORY ONLY: nothing in this router
writes outside the polls/poll_options/poll_votes tables — a result
never mutates league settings or any other state.
"""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from .. import schemas
from ..database import get_db
from . import get_league, require_team_actor
from .message_board import _commissioner_team_id

router = APIRouter()


def _poll_out(con: sqlite3.Connection, row: sqlite3.Row,
              viewer_team_id: int | None) -> schemas.PollOut:
    options = []
    total = 0
    counts = {
        r["option_id"]: r["n"]
        for r in con.execute(
            "SELECT option_id, COUNT(*) AS n FROM poll_votes"
            " WHERE poll_id = ? GROUP BY option_id", (row["id"],))
    }
    for o in con.execute(
            "SELECT * FROM poll_options WHERE poll_id = ?"
            " ORDER BY position, id", (row["id"],)):
        n = counts.get(o["id"], 0)
        total += n
        options.append(schemas.PollOptionOut(id=o["id"], label=o["label"],
                                             votes=n))
    for o in options:
        o.pct = round(100.0 * o.votes / total, 1) if total else 0.0
    my_option_id = None
    if viewer_team_id is not None:
        v = con.execute(
            "SELECT option_id FROM poll_votes WHERE poll_id = ? AND team_id = ?",
            (row["id"], viewer_team_id)).fetchone()
        if v:
            my_option_id = v["option_id"]
    creator = con.execute(
        "SELECT name FROM teams WHERE id = ?", (row["team_id"],)).fetchone()
    return schemas.PollOut(
        id=row["id"], league_id=row["league_id"], team_id=row["team_id"],
        team_name=creator["name"] if creator else "",
        question=row["question"], options=options, total_votes=total,
        my_option_id=my_option_id, closed=row["closed_at"] is not None,
        created_at=row["created_at"], closed_at=row["closed_at"])


def _get_poll(con: sqlite3.Connection, league_id: int,
              poll_id: int) -> sqlite3.Row:
    row = con.execute(
        "SELECT * FROM polls WHERE id = ? AND league_id = ?",
        (poll_id, league_id)).fetchone()
    if not row:
        raise HTTPException(404, f"poll {poll_id} not found")
    return row


@router.get("/{league_id}/polls", response_model=schemas.PollsOut)
def list_polls(league_id: int, team_id: int | None = Query(None),
               con: sqlite3.Connection = Depends(get_db)):
    """Newest first. Reads are open; passing team_id only marks that
    team's own vote in each poll (my_option_id) — it never gates."""
    league = get_league(con, league_id)  # 404 if missing
    rows = con.execute(
        "SELECT * FROM polls WHERE league_id = ? ORDER BY id DESC",
        (league_id,)).fetchall()
    return schemas.PollsOut(
        league_id=league_id,
        commissioner_team_id=_commissioner_team_id(con, league),
        total=len(rows),
        polls=[_poll_out(con, r, team_id) for r in rows])


@router.post("/{league_id}/polls", status_code=201,
             response_model=schemas.PollOut)
def create_poll(league_id: int, body: schemas.PollCreate,
                request: Request,
                con: sqlite3.Connection = Depends(get_db)):
    """Create a poll as a team. Claim-aware: a claimed team needs
    its code (P4-W18). Options are trimmed, non-empty, de-duplicated."""
    get_league(con, league_id)  # 404 if missing
    team = require_team_actor(con, body.team_id, request)
    if team["league_id"] != league_id:
        raise HTTPException(
            422, f"team {body.team_id} is not in league {league_id}")
    question = body.question.strip()
    if not question:
        raise HTTPException(422, "poll question must not be empty")
    labels: list[str] = []
    for raw in body.options:
        label = raw.strip()
        if label and label not in labels:
            labels.append(label)
    if not 2 <= len(labels) <= 6:
        raise HTTPException(422, "a poll needs 2-6 distinct options")
    cur = con.execute(
        "INSERT INTO polls (league_id, team_id, question) VALUES (?, ?, ?)",
        (league_id, body.team_id, question))
    poll_id = cur.lastrowid
    for i, label in enumerate(labels):
        con.execute(
            "INSERT INTO poll_options (poll_id, label, position)"
            " VALUES (?, ?, ?)", (poll_id, label, i))
    con.commit()
    return _poll_out(con, _get_poll(con, league_id, poll_id), body.team_id)


@router.post("/{league_id}/polls/{poll_id}/vote",
             response_model=schemas.PollOut)
def vote_poll(league_id: int, poll_id: int, body: schemas.PollVoteIn,
              request: Request,
              con: sqlite3.Connection = Depends(get_db)):
    """Cast or change the acting team's vote. One row per team
    (UNIQUE(poll_id, team_id)); re-voting replaces the choice.
    Claim-aware; closed polls reject votes with 422."""
    get_league(con, league_id)  # 404 if missing
    poll = _get_poll(con, league_id, poll_id)
    team = require_team_actor(con, body.team_id, request)
    if team["league_id"] != league_id:
        raise HTTPException(
            422, f"team {body.team_id} is not in league {league_id}")
    if poll["closed_at"] is not None:
        raise HTTPException(422, "poll is closed")
    opt = con.execute(
        "SELECT id FROM poll_options WHERE id = ? AND poll_id = ?",
        (body.option_id, poll_id)).fetchone()
    if not opt:
        raise HTTPException(404, f"option {body.option_id} not found in poll {poll_id}")
    con.execute(
        """INSERT INTO poll_votes (poll_id, team_id, option_id)
           VALUES (?, ?, ?)
           ON CONFLICT(poll_id, team_id) DO UPDATE SET
             option_id = excluded.option_id,
             updated_at = datetime('now')""",
        (poll_id, body.team_id, body.option_id))
    con.commit()
    return _poll_out(con, _get_poll(con, league_id, poll_id), body.team_id)


@router.post("/{league_id}/polls/{poll_id}/close",
             response_model=schemas.PollOut)
def close_poll(league_id: int, poll_id: int, request: Request,
               team_id: int = Query(...),
               con: sqlite3.Connection = Depends(get_db)):
    """Close a poll: the creator's team or the commissioner's team
    only (both behind the P4-W18 claim gate). Idempotent — closing
    an already-closed poll returns it unchanged."""
    league = get_league(con, league_id)  # 404 if missing
    poll = _get_poll(con, league_id, poll_id)
    actor = require_team_actor(con, team_id, request)
    if actor["league_id"] != league_id:
        raise HTTPException(
            422, f"team {team_id} is not in league {league_id}")
    if team_id != poll["team_id"] and \
            team_id != _commissioner_team_id(con, league):
        raise HTTPException(
            403, "only the poll's creator or the commissioner can close it")
    if poll["closed_at"] is None:
        con.execute(
            "UPDATE polls SET closed_at = datetime('now') WHERE id = ?",
            (poll_id,))
        con.commit()
        poll = _get_poll(con, league_id, poll_id)
    return _poll_out(con, poll, team_id)
