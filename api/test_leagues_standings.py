"""P4-W27: league-detail standings are sorted by record, not alphabet.

Regression test for get_league_detail ordering teams ORDER BY t.name:
once results land, the dashboard (rank numbers, playoff highlighting /
cut line, my-matchup default = standings[0]) contradicted the playoffs
endpoint's record-based seeds.

Fabricated final matchups on a scratch in-memory DB. The expected
order exercises every step of the sort chain that the endpoint's
aggregates support:
  * wins desc        — Charlie (3 W) top; Zulu's 1 W keeps it in the
                       1-win group despite 5 losses.
  * losses asc       — Yankee (2-0) above Delta (2-1) even though
                       Delta's points-for (580) dwarf Yankee's (290);
                       Zulu (1-5) below Alpha (1-2) despite more PF.
  * points-for desc  — Bravo (1-2, 250 PF) above Alpha (1-2, 30 PF).
  * name asc         — full ties only (second test).

Plain unittest, stdlib only. Run from the repo root:
    python3 -m pytest api/test_leagues_standings.py
    python3 -m unittest api.test_leagues_standings
"""

import json
import sqlite3
import unittest
from pathlib import Path

from api.routers.leagues import get_league_detail

SCHEMA = (Path(__file__).resolve().parent / "schema.sql").read_text()


def _scratch_con() -> sqlite3.Connection:
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA)
    return con


def _league(con: sqlite3.Connection, name: str) -> int:
    owner = con.execute("INSERT INTO users (name) VALUES ('Commish')").lastrowid
    return con.execute(
        "INSERT INTO leagues (name, invite_code, commissioner_id, season,"
        " settings, status) VALUES (?, ?, ?, '2027', ?, 'in_season')",
        (name, f"CODE-{name}", owner, json.dumps({"playoff_teams": 4})),
    ).lastrowid


def _team(con: sqlite3.Connection, league_id: int, name: str) -> int:
    owner = con.execute("INSERT INTO users (name) VALUES (?)", (f"{name} owner",)).lastrowid
    return con.execute(
        "INSERT INTO teams (league_id, owner_id, name, faab_remaining)"
        " VALUES (?, ?, ?, 100)",
        (league_id, owner, name),
    ).lastrowid


def _final(con: sqlite3.Connection, league_id: int, week_no: int,
           a: int, b: int, score_a: float, score_b: float) -> None:
    con.execute(
        "INSERT INTO matchups (league_id, week_no, team_a_id, team_b_id,"
        " score_a, score_b, status) VALUES (?, ?, ?, ?, ?, ?, 'final')",
        (league_id, week_no, a, b, score_a, score_b),
    )


class TestStandingsSortedByRecord(unittest.TestCase):
    def test_order_follows_w_l_pf_not_alphabet(self):
        con = _scratch_con()
        league_id = _league(con, "Record League")
        # Insertion/alphabetical order: Alpha, Bravo, Charlie, Delta,
        # Yankee, Zulu — deliberately NOT the record order.
        alpha = _team(con, league_id, "Alpha")
        bravo = _team(con, league_id, "Bravo")
        charlie = _team(con, league_id, "Charlie")
        delta = _team(con, league_id, "Delta")
        yankee = _team(con, league_id, "Yankee")
        zulu = _team(con, league_id, "Zulu")

        games = [
            # (week, a, b, score_a, score_b)
            (1, charlie, zulu, 100, 10),
            (2, charlie, zulu, 100, 10),
            (3, charlie, yankee, 60, 60),    # tie
            (4, charlie, bravo, 80, 70),
            (1, delta, zulu, 200, 20),
            (2, delta, alpha, 200, 5),
            (3, yankee, delta, 190, 180),
            (5, bravo, zulu, 150, 0),
            (6, yankee, bravo, 40, 30),
            (7, alpha, zulu, 20, 10),
            (8, zulu, alpha, 15, 5),
        ]
        for week, a, b, sa, sb in games:
            _final(con, league_id, week, a, b, sa, sb)
        con.commit()

        detail = get_league_detail(league_id, con)
        got = [(s.team_name, s.wins, s.losses, s.ties, s.points_for)
               for s in detail.standings]

        # Hand-derived from the fabricated results above:
        #   Charlie 3-0-1 PF340 | Yankee 2-0-1 PF290 | Delta 2-1-0 PF580
        #   Bravo   1-2-0 PF250 | Alpha  1-2-0 PF30  | Zulu  1-5-0 PF65
        self.assertEqual(
            got,
            [
                ("Charlie", 3, 0, 1, 340.0),
                ("Yankee", 2, 0, 1, 290.0),
                ("Delta", 2, 1, 0, 580.0),
                ("Bravo", 1, 2, 0, 250.0),
                ("Alpha", 1, 2, 0, 30.0),
                ("Zulu", 1, 5, 0, 65.0),
            ],
        )
        names = [row[0] for row in got]
        self.assertNotEqual(names, sorted(names))  # not alphabetical
        # The my-matchup default (standings[0]) is the league leader.
        self.assertEqual(detail.standings[0].team_name, "Charlie")

    def test_full_tie_falls_back_to_name(self):
        con = _scratch_con()
        league_id = _league(con, "Tied League")
        foxtrot = _team(con, league_id, "Foxtrot")
        echo = _team(con, league_id, "Echo")
        # Identical records AND identical points-for: name decides.
        _final(con, league_id, 1, foxtrot, echo, 50, 50)
        con.commit()

        detail = get_league_detail(league_id, con)
        self.assertEqual(
            [(s.team_name, s.wins, s.losses, s.ties, s.points_for)
             for s in detail.standings],
            [("Echo", 0, 0, 1, 50.0), ("Foxtrot", 0, 0, 1, 50.0)],
        )


if __name__ == "__main__":
    unittest.main()
