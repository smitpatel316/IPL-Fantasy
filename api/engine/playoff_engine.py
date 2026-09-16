"""IPL Fantasy — P2-L6 playoff engine.

Single-elimination bracket for fantasy weeks 7–8 (D9: top-4 playoffs,
semis + final). Sandbox-first, stdlib-only, deterministic.

Format (6-team league):
  Week 7: championship semifinals 1v4, 2v3; consolation game 5v6.
  Week 8: championship final (semi winners); 3rd-place game (semi losers).
Final placements 1st–6th are fully determined.

Seeds come from ``Season.playoff_seeds()`` (P2-L5) — this engine takes
only the ordered seeds, keeping the bracket decoupled from the
scheduler.

Tiebreak: a tied playoff game is won by the HIGHER (better)
regular-season seed. Rationale: rewards the regular season and matches
the most common fantasy-platform rule. No D-item covers playoff ties;
flagged for Smit/Atlas review in the P2-L6 report.

Reseeding: ``reseed=True`` lists week-8 pairings higher-seed-first
("home" team). With 4 teams / 2 weeks this never changes who plays
whom — documented honestly; the flag exists so the format can grow
(e.g. byes) without changing the call signature.

Fail-closed, mirroring the scheduler: ``record_week`` raises on unknown
teams, missing totals (a score of 0.0 is valid; MISSING is an error —
the engine never invents a score), double-recording a week, or
recording week 8 before week 7 decided the finalists. Only fantasy
weeks 7 and 8 are playable (matchup_scheduler.FANTASY_WEEKS).

JSON contract: ``to_dict()`` / ``from_dict()`` round-trip the bracket
(config + recorded weeks).
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from .matchup_scheduler import FANTASY_WEEKS

CHAMPIONSHIP_WEEKS = (7, 8)   # D9: semis week 7, final week 8
SEMIFINAL_WEEK = 7
FINAL_WEEK = 8


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class PlayoffError(Exception):
    """Base class for all playoff-engine errors."""


class BadSeeds(PlayoffError):
    """Seeds are not 4 unique team ids (or consolation is not 0/2 ids)."""


class UnknownTeam(PlayoffError):
    """A team id is not part of this bracket."""


class WeekOutOfRange(PlayoffError):
    """Week number is not a playoff week (7 or 8)."""


class MissingWeeklyTotal(PlayoffError):
    """A participating team's weekly total was not supplied — fail closed."""


class WeekAlreadyFinal(PlayoffError):
    """This playoff week's results were already recorded."""


class BracketNotReady(PlayoffError):
    """Week 8 cannot be recorded before week 7 decided the finalists."""


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PlayoffConfig:
    """Playoff bracket setup.

    seeds: 4 ordered team_ids, best regular-season record first
           (from Season.playoff_seeds()).
    consolation: 2 ordered team_ids [5th seed, 6th seed] for the week-7
           5v6 game; empty tuple disables consolation games (placements
           then cover 1st–4th only).
    reseed: list week-8 pairings higher-seed-first (pairing-neutral for
           the 4-team format; see module docstring).
    team_names: team_id -> display name (reporting only).
    """
    seeds: tuple
    consolation: tuple = ()
    reseed: bool = False
    team_names: tuple = ()          # ((team_id, name), ...) — tuple for hashability


# ---------------------------------------------------------------------------
# Bracket
# ---------------------------------------------------------------------------

class PlayoffBracket:
    """Weeks 7–8 single-elimination bracket + consolation.

    Record week 7 (semis + 5v6) then week 8 (final + 3rd-place game).
    """

    def __init__(self, config: PlayoffConfig, clock=None):
        seeds = tuple(config.seeds)
        if len(seeds) != 4 or len(set(seeds)) != 4:
            raise BadSeeds(
                f"need exactly 4 unique seeds, got {seeds!r}")
        cons = tuple(config.consolation)
        if len(cons) not in (0, 2) or len(set(cons)) != len(cons):
            raise BadSeeds(
                f"consolation must be 0 or 2 unique team ids, got {cons!r}")
        if set(seeds) & set(cons):
            raise BadSeeds("a team cannot be both a seed and consolation")
        self.config = config
        self.clock = clock or time.time
        self.team_names = dict(config.team_names)
        self._seed_rank = {tid: i for i, tid in enumerate(seeds)}  # lower = better
        self._all_teams = set(seeds) | set(cons)
        self.finalized: dict[int, dict] = {}   # week_no -> result record

    # -- validation --------------------------------------------------------
    def _require_team(self, team_id):
        if team_id not in self._all_teams:
            raise UnknownTeam(f"unknown team_id {team_id!r}")

    def _better_seed(self, team_a, team_b):
        """The team with the better regular-season seed (lower rank).

        Consolation teams have no championship seed; between two of
        them the 5th seed (listed first) counts as better.
        """
        rank_a = self._seed_rank.get(team_a, 4 + self._cons_rank(team_a))
        rank_b = self._seed_rank.get(team_b, 4 + self._cons_rank(team_b))
        return team_a if rank_a <= rank_b else team_b

    def _cons_rank(self, team_id):
        cons = list(self.config.consolation)
        return cons.index(team_id) if team_id in cons else 99

    # -- pairings ----------------------------------------------------------
    def semifinal_pairings(self) -> list[tuple]:
        """Week-7 championship semifinals: 1v4, 2v3 (fixed bracket)."""
        s = self.config.seeds
        return [(s[0], s[3]), (s[1], s[2])]

    def consolation_pairings(self) -> list[tuple]:
        """Week-7 consolation game: 5v6 (empty if consolation disabled)."""
        cons = self.config.consolation
        return [(cons[0], cons[1])] if cons else []

    def week7_pairings(self) -> list[tuple]:
        return self.semifinal_pairings() + self.consolation_pairings()

    def _week7_winners_losers(self):
        """(semi_winners, semi_losers, consolation_winner) from week 7."""
        record = self.finalized.get(SEMIFINAL_WEEK)
        if record is None:
            raise BracketNotReady("week 7 must be recorded first")
        by_pair = {(m["team_a"], m["team_b"]): m for m in record["matchups"]}
        semi_winners, semi_losers = [], []
        for a, b in self.semifinal_pairings():
            m = by_pair[(a, b)]
            semi_winners.append(m["winner"])
            semi_losers.append(b if m["winner"] == a else a)
        consolation_winner = None
        for a, b in self.consolation_pairings():
            m = by_pair[(a, b)]
            consolation_winner = m["winner"]
        return semi_winners, semi_losers, consolation_winner

    def final_pairings(self) -> list[tuple]:
        """Week-8 pairings: final + 3rd-place game.

        Requires week 7 recorded. With reseed=True the higher seed is
        listed first in each pairing (pairing-neutral for 4 teams).
        """
        semi_winners, semi_losers, _ = self._week7_winners_losers()
        final = (semi_winners[0], semi_winners[1])
        third = (semi_losers[0], semi_losers[1])
        if self.config.reseed:
            final = self._seed_first(final)
            third = self._seed_first(third)
        return [final, third]

    def _seed_first(self, pair):
        a, b = pair
        return (a, b) if self._better_seed(a, b) == a else (b, a)

    # -- recording ---------------------------------------------------------
    def _participants(self, week_no) -> list[tuple]:
        if week_no == SEMIFINAL_WEEK:
            return self.week7_pairings()
        if week_no == FINAL_WEEK:
            return self.final_pairings()  # raises BracketNotReady if w7 missing
        raise WeekOutOfRange(
            f"week {week_no} is not a playoff week {CHAMPIONSHIP_WEEKS}")

    def record_week(self, week_no: int, points: dict) -> dict:
        """Grade one playoff week's games from per-team point totals.

        Ties are won by the higher regular-season seed (documented in
        the module docstring; flagged for review).
        """
        if week_no not in FANTASY_WEEKS:
            raise WeekOutOfRange(
                f"week {week_no} is not a defined fantasy week")
        if week_no in self.finalized:
            raise WeekAlreadyFinal(f"week {week_no} already recorded")
        pairings = self._participants(week_no)  # validates week + readiness

        totals = {}
        for a, b in pairings:
            for tid in (a, b):
                if tid not in points:
                    raise MissingWeeklyTotal(
                        f"no weekly total for team {tid!r} "
                        f"(fail closed — pass 0.0 explicitly)")
                value = points[tid]
                if not isinstance(value, (int, float)) or isinstance(value, bool):
                    raise PlayoffError(
                        f"weekly total for team {tid!r} must be a number, "
                        f"got {value!r}")
                if value < 0:
                    raise PlayoffError(
                        f"weekly total for team {tid!r} is negative ({value})")
                totals[tid] = float(value)
        for tid in points:
            self._require_team(tid)

        matchups = []
        for team_a, team_b in pairings:
            pa, pb = totals[team_a], totals[team_b]
            if pa > pb:
                winner = team_a
            elif pb > pa:
                winner = team_b
            else:
                winner = self._better_seed(team_a, team_b)  # tie: higher seed
            matchups.append({
                "team_a": team_a, "team_b": team_b,
                "score_a": pa, "score_b": pb, "winner": winner,
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

    # -- outcomes ----------------------------------------------------------
    def champion(self):
        """Champion team_id, or None if the final is not recorded."""
        record = self.finalized.get(FINAL_WEEK)
        if record is None:
            return None
        final = self.final_pairings()[0]
        m = next(m for m in record["matchups"]
                 if {m["team_a"], m["team_b"]} == set(final))
        return m["winner"]

    def placements(self) -> dict:
        """{1: team_id, ..., 6: team_id} once week 8 is recorded.

        1st = final winner, 2nd = final loser, 3rd/4th = 3rd-place game,
        5th/6th = consolation game (only with consolation teams).
        """
        if FINAL_WEEK not in self.finalized:
            raise BracketNotReady("week 8 must be recorded first")
        semi_winners, semi_losers, consolation_winner = \
            self._week7_winners_losers()
        final = self.final_pairings()[0]
        third = self.final_pairings()[1]
        record = self.finalized[FINAL_WEEK]
        by_teams = {(m["team_a"], m["team_b"]): m for m in record["matchups"]}

        def winner_of(pair):
            m = by_teams.get(pair) or by_teams.get((pair[1], pair[0]))
            return m["winner"]

        champ = winner_of(final)
        runner_up = final[1] if champ == final[0] else final[0]
        third_winner = winner_of(third)
        fourth = third[1] if third_winner == third[0] else third[0]
        places = {1: champ, 2: runner_up, 3: third_winner, 4: fourth}
        if self.config.consolation:
            loser = [t for t in self.config.consolation
                     if t != consolation_winner][0]
            places[5] = consolation_winner
            places[6] = loser
        return places

    # -- JSON contract -----------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "config": {
                "seeds": list(self.config.seeds),
                "consolation": list(self.config.consolation),
                "reseed": self.config.reseed,
                "team_names": [[tid, name]
                               for tid, name in self.team_names.items()],
            },
            "finalized": {
                str(w): record for w, record in self.finalized.items()
            },
        }

    @classmethod
    def from_dict(cls, state: dict, clock=None) -> "PlayoffBracket":
        cfg = state["config"]
        config = PlayoffConfig(
            seeds=tuple(cfg["seeds"]),
            consolation=tuple(cfg.get("consolation", ())),
            reseed=cfg.get("reseed", False),
            team_names=tuple((t[0], t[1]) for t in cfg.get("team_names", [])),
        )
        bracket = cls(config, clock=clock)
        bracket.finalized = {
            int(w): record for w, record in state["finalized"].items()
        }
        return bracket
