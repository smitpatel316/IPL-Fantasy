"""P3-A6 (D10 option 4, chair-confirmed 2026-09-16): schedule-aware UI nudges.

Fixture -> fantasy-week (Mon-Sun) per-IPL-team game counts.

The game-count table is the raw material for the draft-room and waiver-wire
schedule badges ("MI 3 games this week") that turn schedule luck into a
draftable/waivable skill instead of hidden noise.

Dev stand-in: the importer runs today against the 2026 fixture derived from
the phase-1 Cricsheet backtest data (``ipl.db`` matches table). When the real
2027 fixture is released (~Feb 2027), re-run with the live fixture — the
stored ``season`` label stays '2027' and ``source`` records provenance, so the
endpoint and UI need no re-architecture; only the data changes.

Week math: fantasy weeks are Mon-Sun covering the fixture span. week_no is
1-based from the Monday of the first fixture's calendar week; week_start /
week_end are stored per week so badge counts always equal the fixture math.
This mirrors research/schedule_luck.py::fantasy_weeks (kept self-contained so
the api package does not depend on the research tree).

Mid-season recompute: ``recompute_from_fixture`` reloads live 2027 data,
upserts fresh counts idempotently, and reports which (week, team) counts
changed vs the previous snapshot — that diff is the re-armed 15% tripwire
input; the full luck_share re-measurement runs via
research/schedule_luck.py once 2027 backtest data exists.

Usage:
    python3 -m api.schedule_games --standin           # 2026 fixture -> api db
    python3 -m api.schedule_games --fixture-csv f.csv --season 2027 --source "ipl-2027-official"
    python3 -m api.schedule_games --recompute --fixture-csv live.csv
Fixture CSV columns: match_date (ISO), team1, team2 (full names or codes).
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import logging
import os
import sqlite3
import sys

log = logging.getLogger("api.schedule_games")

# Full Cricsheet names -> franchise codes (2026 season; update on expansion).
FULL_NAME_TO_CODE = {
    "Mumbai Indians": "MI",
    "Chennai Super Kings": "CSK",
    "Royal Challengers Bengaluru": "RCB",
    "Royal Challengers Bangalore": "RCB",
    "Kolkata Knight Riders": "KKR",
    "Sunrisers Hyderabad": "SRH",
    "Delhi Capitals": "DC",
    "Gujarat Titans": "GT",
    "Punjab Kings": "PBKS",
    "Rajasthan Royals": "RR",
    "Lucknow Super Giants": "LSG",
}


def to_code(name: str) -> str:
    """Map a fixture team name to its franchise code; codes pass through."""
    name = (name or "").strip()
    if name in FULL_NAME_TO_CODE:
        return FULL_NAME_TO_CODE[name]
    upper = name.upper()
    if upper in set(FULL_NAME_TO_CODE.values()):
        return upper
    raise ValueError(f"unknown IPL team name: {name!r}")


def fantasy_weeks(dates: list[dt.date]) -> list[tuple[dt.date, dt.date]]:
    """Mon-Sun weeks (1-based) covering the fixture span, no edge dropping.

    Badge counts must equal the fixture math, so every fixture date belongs
    to exactly one week — no trimming like the R2 measurement variant.
    """
    first, last = min(dates), max(dates)
    mon = first - dt.timedelta(days=first.weekday())
    weeks: list[tuple[dt.date, dt.date]] = []
    while mon <= last:
        weeks.append((mon, mon + dt.timedelta(days=6)))
        mon += dt.timedelta(days=7)
    return weeks


def load_fixture_standin(phase1_db: str, season: str = "2026") -> list[tuple[dt.date, str, str]]:
    """Dev stand-in: fixture from the phase-1 Cricsheet matches table."""
    con = sqlite3.connect(phase1_db)
    try:
        rows = con.execute(
            "SELECT match_date, team1, team2 FROM matches WHERE season = ? AND status = 'completed'",
            (season,),
        ).fetchall()
    finally:
        con.close()
    fixture = [(dt.date.fromisoformat(d), to_code(t1), to_code(t2)) for d, t1, t2 in rows]
    log.info(f"stand-in fixture {season}: {len(fixture)} matches")
    return fixture


def load_fixture_csv(path: str) -> list[tuple[dt.date, str, str]]:
    """Live/official fixture CSV: match_date (ISO), team1, team2."""
    fixture = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            fixture.append(
                (dt.date.fromisoformat(row["match_date"].strip()),
                 to_code(row["team1"]), to_code(row["team2"]))
            )
    log.info(f"fixture {path}: {len(fixture)} matches")
    return fixture


def build_rows(fixture: list[tuple[dt.date, str, str]],
               season_label: str, source: str) -> list[dict]:
    """Every (week, IPL team) -> game count, including 0-game bye weeks."""
    weeks = fantasy_weeks([d for d, _, _ in fixture])
    teams = sorted({c for _, c1, c2 in fixture for c in (c1, c2)})
    counts: dict[tuple[int, str], int] = {}
    for wi, (mon, sun) in enumerate(weeks):
        for code in teams:
            counts[(wi + 1, code)] = 0
    for d, c1, c2 in fixture:
        for wi, (mon, sun) in enumerate(weeks):
            if mon <= d <= sun:
                counts[(wi + 1, c1)] += 1
                counts[(wi + 1, c2)] += 1
                break
    rows = []
    for wi, (mon, sun) in enumerate(weeks):
        for code in teams:
            rows.append({
                "season": season_label,
                "week_no": wi + 1,
                "week_start": mon.isoformat(),
                "week_end": sun.isoformat(),
                "ipl_team_code": code,
                "games": counts[(wi + 1, code)],
                "source": source,
            })
    return rows


def upsert_rows(con: sqlite3.Connection, rows: list[dict]) -> int:
    """Idempotent upsert (PK = season, week_no, ipl_team_code)."""
    n = 0
    for r in rows:
        con.execute(
            """INSERT INTO team_weekly_games
                   (season, week_no, week_start, week_end, ipl_team_code, games, source)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(season, week_no, ipl_team_code) DO UPDATE SET
                   week_start = excluded.week_start,
                   week_end = excluded.week_end,
                   games = excluded.games,
                   source = excluded.source""",
            (r["season"], r["week_no"], r["week_start"], r["week_end"],
             r["ipl_team_code"], r["games"], r["source"]),
        )
        n += 1
    con.commit()
    return n


def fetch_week(con: sqlite3.Connection, season: str, week_no: int) -> dict:
    """GET seam for the schedule-nudges endpoint."""
    rows = con.execute(
        """SELECT week_start, week_end, ipl_team_code, games, source
           FROM team_weekly_games WHERE season = ? AND week_no = ?
           ORDER BY ipl_team_code""",
        (season, week_no),
    ).fetchall()
    weeks = [w for (w,) in con.execute(
        "SELECT DISTINCT week_no FROM team_weekly_games WHERE season = ? ORDER BY week_no",
        (season,))]
    if not rows:
        return {"season": season, "week_no": week_no, "weeks_available": weeks,
                "games": [], "source": ""}
    return {
        "season": season,
        "week_no": week_no,
        "week_start": rows[0][0],
        "week_end": rows[0][1],
        "source": rows[0][4],
        "weeks_available": weeks,
        "games": [{"ipl_team_code": r[2], "games": r[3]} for r in rows],
    }


def recompute_from_fixture(con: sqlite3.Connection, fixture: list[tuple[dt.date, str, str]],
                           season_label: str, source: str) -> dict:
    """Mid-season recompute: upsert live counts, report deltas vs snapshot.

    Returns a tripwire report: changed (week, team) counts and the max
    absolute game-count differential swing — the re-armed 15% tripwire input.
    The full luck_share re-measurement runs via research/schedule_luck.py once
    2027 backtest data exists; this job keeps the input fixture fresh.
    """
    before = {(r[0], r[1]): r[2] for r in con.execute(
        "SELECT week_no, ipl_team_code, games FROM team_weekly_games WHERE season = ?",
        (season_label,))}
    rows = build_rows(fixture, season_label, source)
    upsert_rows(con, rows)
    deltas = []
    for r in rows:
        key = (r["week_no"], r["ipl_team_code"])
        old = before.get(key)
        if old is not None and old != r["games"]:
            deltas.append({"week_no": r["week_no"], "ipl_team_code": r["ipl_team_code"],
                           "was": old, "now": r["games"]})
    report = {
        "season": season_label, "source": source,
        "weeks": len({r["week_no"] for r in rows}),
        "changed_counts": deltas,
        "n_changed": len(deltas),
        "tripwire_rearmed": True,
        "note": ("fixture refreshed on live 2027 data; re-run research/schedule_luck.py "
                 "for luck_share when 2027 backtest data exists (15% D10 tripwire)"),
    }
    log.info(f"recompute: {len(rows)} rows upserted, {len(deltas)} changed")
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="P3-A6 fixture->weekly game counts")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--standin", action="store_true",
                     help="2026 Cricsheet fixture as dev stand-in (phase-1 ipl.db)")
    src.add_argument("--fixture-csv", help="official/live fixture CSV")
    ap.add_argument("--recompute", action="store_true",
                    help="mid-season recompute from --fixture-csv, report deltas (not the 15% measurement)")
    ap.add_argument("--phase1-db", default=os.path.expanduser(
        "~/workspace/ipl-fantasy/phase1/ipl.db"))
    ap.add_argument("--api-db", default=os.path.expanduser(
        "~/workspace/ipl-fantasy/repo/data/ipl_fantasy.db"))
    ap.add_argument("--season", default="2027",
                    help="league season label stored in team_weekly_games")
    ap.add_argument("--fixture-season", default="2026",
                    help="Cricsheet season to read for the stand-in")
    ap.add_argument("--source", default="",
                    help="fixture provenance label (default: auto from mode)")
    args = ap.parse_args(argv)

    if args.recompute:
        if not args.fixture_csv:
            ap.error("--recompute needs --fixture-csv")
        fixture = load_fixture_csv(args.fixture_csv)
        source = args.source or f"live-2027-{dt.date.today().isoformat()}"
        con = sqlite3.connect(args.api_db)
        try:
            report = recompute_from_fixture(con, fixture, args.season, source)
        finally:
            con.close()
        print(report)
        return 0
    if args.standin:
        fixture = load_fixture_standin(args.phase1_db, args.fixture_season)
        source = args.source or f"cricsheet-{args.fixture_season}-standin"
    else:
        fixture = load_fixture_csv(args.fixture_csv)
        source = args.source or "official-fixture"

    rows = build_rows(fixture, args.season, source)
    con = sqlite3.connect(args.api_db)
    try:
        n = upsert_rows(con, rows)
    finally:
        con.close()
    print(f"upserted {n} team_weekly_games rows for season={args.season} source={source}")
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sys.exit(main())
