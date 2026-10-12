"""P4-D1 migration: correct role drift for three players in the demo league.

Verified 2026-10-12 against the IPL 2026 squad data (phase-1 role registry
sourced from the Wikipedia IPL personnel-change lists, IPLT20 official squad
pages, and Cricsheet ball-by-ball workloads in phase1/ipl.db):

  W Jacks  (MI)   canonical AR   — IPLT20 + Wikipedia list him as All-rounder;
                                  bowled in 5/8 (2024), 8/13 (2025), 6/7 (2026)
                                  matches. Demo DB already AR; the stale copy
                                  was the canonical universe JSON (fixed in
                                  seed_players_universe.json on this branch).
  P Arya   (PBKS) canonical BAT  — registry corrected AR->BAT for 2026; he has
                                  bowled 0 balls in IPL 2025+2026 across 31
                                  matches batted. Demo DB still carries the
                                  stale 2025 classification AR -> BAT.
  R Khan   (GT)   canonical BOWL — frontline leg-spinner (~4 overs/match every
                                  season 2017-2026); registry BOWL 2023-2026;
                                  squad listings group him with Bowlers.
                                  Demo DB already BOWL; the stale copy was the
                                  canonical universe JSON (fixed on this
                                  branch).

This script only ever updates `player_roles.role` for season-2027 rows of the
three named players, and only when the current value differs from the
canonical role above. It never touches names, team codes, drafts,
roster_slots, lineup data, or ranks.

Usage (run from the Pi checkout, reviewed first):
    python3 data/migrate_role_drift_p4d1.py --db ~/ipl-fantasy/data/ipl_fantasy.db   # dry run
    python3 data/migrate_role_drift_p4d1.py --db ~/ipl-fantasy/data/ipl_fantasy.db --apply

Back up the DB before --apply:
    cp ~/ipl-fantasy/data/ipl_fantasy.db ~/ipl-fantasy/data/ipl_fantasy.db.bak-p4d1

Idempotent: re-running after --apply reports zero changes.
"""

import argparse
import sqlite3
import sys
from pathlib import Path

SEASON = "2027"

# name -> (canonical role, expected ipl_team_code as a sanity guard)
CANONICAL = {
    "W Jacks": ("AR", "MI"),
    "P Arya": ("BAT", "PBKS"),
    "R Khan": ("BOWL", "GT"),
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/ipl_fantasy.db")
    ap.add_argument("--apply", action="store_true",
                    help="write changes (default is dry-run report)")
    args = ap.parse_args()

    db = Path(args.db)
    if not db.exists():
        print(f"DB not found: {db}", file=sys.stderr)
        return 2
    con = sqlite3.connect(str(db))
    con.row_factory = sqlite3.Row

    changes = []
    for name, (canon_role, canon_team) in CANONICAL.items():
        rows = con.execute(
            """SELECT p.id, pr.role, pr.ipl_team_code
               FROM players p JOIN player_roles pr ON pr.player_id = p.id
               WHERE p.name = ? AND pr.season = ?""",
            (name, SEASON),
        ).fetchall()
        if len(rows) != 1:
            print(f"ABORT: expected exactly 1 season-{SEASON} row for "
                  f"{name!r}, found {len(rows)}", file=sys.stderr)
            return 3
        r = rows[0]
        if r["ipl_team_code"] != canon_team:
            print(f"ABORT: {name} team guard failed: DB has "
                  f"{r['ipl_team_code']}, expected {canon_team}",
                  file=sys.stderr)
            return 3
        if r["role"] != canon_role:
            changes.append((r["id"], name, r["role"], canon_role))
        else:
            print(f"  ok (already canonical): {name} role={canon_role}")

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"[{mode}] role changes: {len(changes)}")
    for _pid, name, old, new in changes:
        print(f"    {name}: {old} -> {new}")

    if not args.apply:
        print("dry-run: no writes. Re-run with --apply to commit.")
        return 0

    with con:
        for pid, _name, _old, new in changes:
            con.execute(
                "UPDATE player_roles SET role = ? WHERE player_id = ? AND season = ?",
                (new, pid, SEASON))
    print(f"applied: {len(changes)} role change(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
