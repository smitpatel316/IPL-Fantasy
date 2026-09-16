"""IPL Fantasy — P2-L5 matchup scheduler + standings.

Sandbox-first, stdlib-only, deterministic H2H scheduling, scoring and
standings for the IPL fantasy league app (D4 weekly H2H Mon–Sun,
D9 top-4 playoffs weeks 7–8, D10 no appearance cap v1).

Fantasy weeks vs IPL 2027 calendar (tentative, DECISIONS.md key dates):
the IPL season runs Wed Mar 10 – Sat May 15, 2027. Fantasy weeks are
Mon–Sun calendar periods; week 1 opens Mon Mar 8 so the season start
lands inside it.

    Week 1:  2027-03-08 .. 2027-03-14   (regular season, round-robin)
    Week 2:  2027-03-15 .. 2027-03-21   (round-robin)
    Week 3:  2027-03-22 .. 2027-03-28   (round-robin)
    Week 4:  2027-03-29 .. 2027-04-04   (round-robin)
    Week 5:  2027-04-05 .. 2027-04-11   (round-robin)
    Week 6:  2027-04-12 .. 2027-04-18   (rivalry/rematch week — see below)
    Week 7:  2027-04-19 .. 2027-04-25   (playoff semifinals, D9)
    Week 8:  2027-04-26 .. 2027-05-02   (playoff final, D9)
    Week 9:  2027-05-03 .. 2027-05-09   (dark — Yahoo's "end before dead
                                         rubbers"; IPL playoffs May 10–15)

Scheduler design:
- Round-robin via the classic circle method over a seeded shuffle of
  the teams (``random.Random(seed)``). For n teams this yields n-1
  rounds; every pair meets exactly once, no team plays itself.
- Weeks 1–5 carry the single round-robin (5 rounds for 6 teams).
- Week 6 = the start of the second cycle: the circle rotation returns
  to round-1 pairings, so every week-6 matchup is a rematch of the same
  fixture in week 1 ("rivalry week"). Deliberate and deterministic —
  no fresh random draw, no new pairings.
- Team count must be even (odd counts raise OddTeamCount — no fake
  byes are invented; the league always has an even team count).

Scoring hook:
- The scorer / live-data feed is another team's job. The caller passes
  per-team weekly fantasy point totals as a plain dict
  (``{team_id: points}``); ``record_week`` grades every matchup:
  win = more points, loss = fewer, tie = equal.
- D10: there is no appearance cap and no minimum — a team that scores
  0.0 points still gets a result. 0 is a valid score; MISSING is an
  error (see fail-closed below).
- Fail-closed: ``record_week`` raises MissingWeeklyTotal if any team is
  absent from the totals dict (it never invents a score), UnknownTeam
  for team ids outside the league, and WeekAlreadyFinal if the week
  was already recorded. Week numbers outside the defined fantasy weeks
  raise WeekOutOfRange.

Standings tiebreak order (documented, applied in sequence):
1. most wins
2. fewest losses
3. highest total points-for
4. head-to-head record among the tied teams (win% across all their
   meetings this season — every pair meets at least once in weeks 1–5)
5. seeded deterministic coin-flip (a stable per-team random key from the
   league seed; independent of dict ordering or call order)

``standings()`` returns the table as a list of dicts:
(team_id, team_name, W, L, T, points_for, points_against).

``playoff_seeds()`` returns the ordered top-4 team ids after week 6
(D9); the bracket itself is P2-L6's job.

Determinism: schedule generation and all tiebreaks derive from the
league ``seed``. The clock is injectable (defaults to ``time.time``)
and is used only for ``finalized_at`` timestamps.

JSON contract: ``to_dict()`` / ``from_dict()`` round-trip the full
season state (config, schedule, recorded weeks, records).
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Fantasy week calendar (IPL 2027, tentative — DECISIONS.md key dates).
# ---------------------------------------------------------------------------

# week_no -> (start_date, end_date) as ISO "YYYY-MM-DD" strings, Mon–Sun.
FANTASY_WEEKS = {
    1: ("2027-03-08", "2027-03-14"),
    2: ("2027-03-15", "2027-03-21"),
    3: ("2027-03-22", "2027-03-28"),
    4: ("2027-03-29", "2027-04-04"),
    5: ("2027-04-05", "2027-04-11"),
    6: ("2027-04-12", "2027-04-18"),
    7: ("2027-04-19", "2027-04-25"),
    8: ("2027-04-26", "2027-05-02"),
    9: ("2027-05-03", "2027-05-09"),   # dark week (D9)
}

REGULAR_SEASON_WEEKS = (1, 2, 3, 4, 5, 6)
PLAYOFF_WEEKS = (7, 8)
PLAYOFF_TEAMS = 4                      # D9: top 4
MIN_REGULAR_WEEK = min(REGULAR_SEASON_WEEKS)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ScheduleError(Exception):
    """Base class for all scheduler/standings errors."""


class OddTeamCount(ScheduleError):
    """Team count is odd — round-robin needs an even count (fail closed)."""


class DuplicateTeam(ScheduleError):
    """The same team id was listed twice."""


class UnknownTeam(ScheduleError):
    """A team id is not part of this league."""


class WeekOutOfRange(ScheduleError):
    """Week number is not a defined fantasy week."""


class MissingWeeklyTotal(ScheduleError):
    """A team's weekly total was not supplied — fail closed, never invent."""


class WeekAlreadyFinal(ScheduleError):
    """This week's results were already recorded."""


class WeekNotFinalized(ScheduleError):
    """Operation requires the week (or all regular-season weeks) finalized."""


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ScheduleConfig:
    """League scheduling setup.

    teams: sequence of (team_id, team_name). The schedule order is a
    seeded shuffle of these teams; pass an explicit ``team_order`` to
    fix it (tests use this to hand-derive expected pairings).
    """
    teams: tuple                    # ((team_id, team_name), ...)
    seed: int | None = 42
    team_order: tuple | None = None  # explicit order overrides the shuffle

    @property
    def team_ids(self) -> tuple:
        return tuple(t[0] for t in self.teams)

    @property
    def num_teams(self) -> int:
        return len(self.teams)

    def resolved_order(self) -> tuple:
        if self.team_order is not None:
            return tuple(self.team_order)
        rng = random.Random(self.seed)
        order = list(self.team_ids)
        rng.shuffle(order)
        return tuple(order)


def _circle_rounds(team_order: list) -> list[list[tuple]]:
    """Circle-method round-robin rounds for an even team list.

    Returns n-1 rounds; each round is a list of (team_a, team_b) pairs.
    Round i+1 rotates the list so every pair meets exactly once.
    """
    n = len(team_order)
    order = list(team_order)
    rounds = []
    for _ in range(n - 1):
        half = n // 2
        pairs = [
            (order[i], order[n - 1 - i])
            for i in range(half)
        ]
        rounds.append(pairs)
        # Rotate: keep the first fixed, move the last to position 1.
        order = [order[0]] + [order[-1]] + order[1:-1]
    return rounds


def generate_schedule(config: ScheduleConfig) -> dict:
    """Build the regular-season matchup schedule.

    Returns {week_no: [(team_a_id, team_b_id), ...]} for weeks 1–6.
    Weeks 1–5 carry the single round-robin; week 6 replays week 1's
    pairings (rivalry/rematch week — start of the second cycle).
    """
    n = config.num_teams
    if n < 2:
        raise OddTeamCount(f"need at least 2 teams, got {n}")
    if n % 2 != 0:
        raise OddTeamCount(
            f"round-robin requires an even team count, got {n}"
        )
    if len(set(config.team_ids)) != n:
        raise DuplicateTeam("duplicate team ids in league teams")
    order = config.resolved_order()
    if set(order) != set(config.team_ids) or len(order) != n:
        raise ScheduleError("team_order must be a permutation of the team ids")

    rounds = _circle_rounds(list(order))
    schedule = {}
    for week in REGULAR_SEASON_WEEKS:
        if week <= n - 1:
            # Weeks 1..(n-1): the single round-robin.
            pairs = rounds[week - 1]
        else:
            # Week 6 (and any week beyond the round-robin for larger
            # leagues): second cycle starts — replay round-1 pairings
            # (rivalry/rematch week), not a fresh random draw.
            pairs = rounds[0]
        schedule[week] = [(a, b) for a, b in pairs]
    return schedule


def week_dates(week_no: int) -> tuple[str, str]:
    """(start_date, end_date) ISO strings for a fantasy week (Mon–Sun)."""
    if week_no not in FANTASY_WEEKS:
        raise WeekOutOfRange(f"week {week_no} is not a defined fantasy week")
    return FANTASY_WEEKS[week_no]


# ---------------------------------------------------------------------------
# Season state machine
# ---------------------------------------------------------------------------

class Season:
    """Regular-season H2H state: schedule, weekly results, standings.

    Call ``record_week(week_no, {team_id: points})`` once per fantasy
    week (in any order — weeks need not be recorded sequentially, but
    each week may only be recorded once).
    """

    def __init__(self, config: ScheduleConfig, clock=None):
        self.config = config
        self.clock = clock or time.time
        self.team_names = {tid: name for tid, name in config.teams}
        self.schedule = generate_schedule(config)   # week_no -> [(a, b)]
        self.finalized: dict[int, dict] = {}        # week_no -> result record
        # Seeded deterministic coin-flip keys for the final tiebreak step.
        # Assigned in sorted(team_id) order so the keys never depend on
        # dict ordering or call order.
        rng = random.Random(config.seed)
        self._tiebreak_keys = {tid: rng.random() for tid in sorted(config.team_ids)}

    # -- validation --------------------------------------------------------
    def _require_team(self, team_id):
        if team_id not in self.team_names:
            raise UnknownTeam(f"unknown team_id {team_id!r}")

    def _require_week(self, week_no):
        if week_no not in FANTASY_WEEKS:
            raise WeekOutOfRange(f"week {week_no} is not a defined fantasy week")

    # -- recording ---------------------------------------------------------
    def record_week(self, week_no: int, points: dict) -> dict:
        """Grade one fantasy week's matchups from per-team point totals.

        ``points`` maps every league team id to its fantasy points for
        the week (floats). A total of 0.0 is a valid result (D10 — no
        appearance cap). A MISSING team raises MissingWeeklyTotal: the
        engine never invents a score.
        """
        self._require_week(week_no)
        if week_no not in self.schedule:
            raise WeekNotFinalized(
                f"week {week_no} has no scheduled matchups "
                f"(regular season is weeks {REGULAR_SEASON_WEEKS})"
            )
        if week_no in self.finalized:
            raise WeekAlreadyFinal(f"week {week_no} already recorded")

        totals = {}
        for tid in self.config.team_ids:
            if tid not in points:
                raise MissingWeeklyTotal(
                    f"no weekly total supplied for team {tid!r} "
                    f"(fail closed — pass 0.0 explicitly if the team "
                    f"scored nothing)"
                )
            value = points[tid]
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise ScheduleError(
                    f"weekly total for team {tid!r} must be a number, "
                    f"got {value!r}"
                )
            if value < 0:
                raise ScheduleError(
                    f"weekly total for team {tid!r} is negative ({value})"
                )
            totals[tid] = float(value)
        for tid in points:
            self._require_team(tid)

        matchups = []
        for team_a, team_b in self.schedule[week_no]:
            pa, pb = totals[team_a], totals[team_b]
            if pa > pb:
                winner = team_a
            elif pb > pa:
                winner = team_b
            else:
                winner = None            # tie
            matchups.append({
                "team_a": team_a,
                "team_b": team_b,
                "score_a": pa,
                "score_b": pb,
                "winner": winner,
            })

        record = {
            "week_no": week_no,
            "week_start": FANTASY_WEEKS[week_no][0],
            "week_end": FANTASY_WEEKS[week_no][1],
            "status": "final",
            "finalized_at": self.clock(),
            "matchups": matchups,
        }
        self.finalized[week_no] = record
        return record

    @property
    def finalized_weeks(self) -> list[int]:
        return sorted(self.finalized)

    # -- records -----------------------------------------------------------
    def team_record(self, team_id) -> dict:
        """W-L-T, points_for, points_against for one team."""
        self._require_team(team_id)
        w = l = t = 0
        pf = pa = 0.0
        for record in self.finalized.values():
            for m in record["matchups"]:
                if team_id == m["team_a"]:
                    ours, theirs = m["score_a"], m["score_b"]
                elif team_id == m["team_b"]:
                    ours, theirs = m["score_b"], m["score_a"]
                else:
                    continue
                pf += ours
                pa += theirs
                if m["winner"] is None:
                    t += 1
                elif m["winner"] == team_id:
                    w += 1
                else:
                    l += 1
        return {
            "team_id": team_id,
            "team_name": self.team_names[team_id],
            "W": w, "L": l, "T": t,
            "points_for": pf,
            "points_against": pa,
        }

    def _head_to_head_pct(self, team_id, tied_group: set) -> float:
        """Win% of team_id against the other teams in the tied group.

        Ties count as half a win. No meetings (shouldn't happen once
        the round-robin is done) -> 0.0 so the seeded coin-flip decides.
        """
        wins = games = 0
        for record in self.finalized.values():
            for m in record["matchups"]:
                pair = {m["team_a"], m["team_b"]}
                if team_id not in pair or not pair <= tied_group:
                    continue
                games += 1
                if m["winner"] is None:
                    wins += 0.5
                elif m["winner"] == team_id:
                    wins += 1
        return wins / games if games else 0.0

    # -- standings ---------------------------------------------------------
    def standings(self) -> list[dict]:
        """Standings table, best first.

        Tiebreak order (applied in sequence):
        1. most wins
        2. fewest losses
        3. highest points-for
        4. head-to-head win% among the tied group
        5. seeded deterministic coin-flip
        """
        rows = [self.team_record(tid) for tid in self.config.team_ids]

        def sort_key(r):
            return (-r["W"], r["L"], -r["points_for"])

        rows.sort(key=sort_key)

        # Resolve exact ties on (W, L, PF) with steps 4–5.
        ordered: list[dict] = []
        i = 0
        while i < len(rows):
            j = i
            while (j < len(rows)
                   and rows[j]["W"] == rows[i]["W"]
                   and rows[j]["L"] == rows[i]["L"]
                   and rows[j]["points_for"] == rows[i]["points_for"]):
                j += 1
            group = rows[i:j]
            if len(group) > 1:
                tied = {r["team_id"] for r in group}
                group.sort(
                    key=lambda r: (
                        -self._head_to_head_pct(r["team_id"], tied),
                        -self._tiebreak_keys[r["team_id"]],
                    )
                )
            ordered.extend(group)
            i = j
        return ordered

    def playoff_seeds(self) -> list[str]:
        """Ordered top-4 team ids after the regular season (D9).

        The bracket itself is P2-L6's job — this only returns the seeds.
        """
        missing = [w for w in REGULAR_SEASON_WEEKS if w not in self.finalized]
        if missing:
            raise WeekNotFinalized(
                f"regular season incomplete — weeks {missing} not finalized"
            )
        return [r["team_id"] for r in self.standings()[:PLAYOFF_TEAMS]]

    # -- JSON contract -----------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "config": {
                "teams": [
                    {"id": tid, "name": name}
                    for tid, name in self.config.teams
                ],
                "seed": self.config.seed,
                "team_order": list(self.config.resolved_order()),
            },
            "schedule": {
                str(w): [[a, b] for a, b in pairs]
                for w, pairs in self.schedule.items()
            },
            "finalized": {
                str(w): record for w, record in self.finalized.items()
            },
        }

    @classmethod
    def from_dict(cls, state: dict, clock=None) -> "Season":
        """Rebuild a Season from a to_dict() snapshot."""
        cfg = state["config"]
        config = ScheduleConfig(
            teams=tuple((t["id"], t["name"]) for t in cfg["teams"]),
            seed=cfg.get("seed"),
            team_order=tuple(cfg["team_order"]),
        )
        season = cls(config, clock=clock)
        season.finalized = {
            int(w): record for w, record in state["finalized"].items()
        }
        return season
