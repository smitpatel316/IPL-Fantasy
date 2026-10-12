"""P4-D2 migration: resolve the three ambiguous legacy player names left
unchanged by migrate_demo_league_2026.py. Researched 2026-10-12 against the
phase-1 role registry (Wikipedia IPL personnel-change lists), IPL 2023-2026
squad lists, and actual scorecards:

  "S Sharma" (RCB, BOWL) -> rename to "Suyash Sharma"
      The only Sharma bowling for RCB in 2025/2026 is Suyash Sharma
      (registry: BOWL, KKR 2023-24 -> RCB 2025-26). Sandeep Sharma — the
      universe's "S Sharma" — has been RR in every season 2023-2026 and has
      never played for RCB. The canonical universe already disambiguates
      exactly this pair by giving Suyash his full name (data/README.md).
      No separate "Suyash Sharma" row exists in the DB, so no collision.

  "M Singh" (KKR, BAT) -> rename to "Mandeep Singh" + status 'retired'
      The only Singh batsman in KKR squads of the seed era is Mandeep Singh
      (registry: BAT, KKR 2023 only; 2023 KKR squad lists show him as a
      batsman bought for Rs 50L; a 2023 KKR scorecard shows "M Singh"
      batting for KKR). He appears in no IPL squad 2024-2026 and is not in
      the canonical 2026 universe, so he is flagged retired (IPL-inactive
      since 2023) with the rename so the row names a real person. Manish
      Pandey is a separate DB row ("M Pandey"), so this is not him.

  "R Singh" (RCB, BAT) -> status 'retired', name left unchanged
      No batsman named R Singh appears in any RCB squad 2023-2026. The
      era's real R Singhs are Rinku Singh (KKR — already a separate row in
      this DB as "R Rinku") and Ramandeep Singh (MI/KKR all-rounder).
      RCB's only 2026 Singh is Abhinandan Singh, a bowler. No verified
      identity exists, so the row is NOT renamed; it is flagged retired to
      take the phantom out of the active pool. The row itself is kept —
      it was drafted (draft_picks/roster_slots reference it) and this
      migration never deletes players or touches draft/roster data.

Guards: each change applies only if the row still matches the expected
(name, team, role) triple; a rename aborts if the target name already
exists. All writes happen in one transaction.

Usage (run from the Pi checkout, reviewed first):
    python3 data/migrate_ambiguous_names_p4d2.py --db ~/ipl-fantasy/data/ipl_fantasy.db   # dry run
    python3 data/migrate_ambiguous_names_p4d2.py --db ~/ipl-fantasy/data/ipl_fantasy.db --apply

Back up the DB before --apply:
    cp ~/ipl-fantasy/data/ipl_fantasy.db ~/ipl-fantasy/data/ipl_fantasy.db.bak-p4d2

Idempotent: re-running after --apply reports zero changes.
"""

import argparse
import sqlite3
import sys
from pathlib import Path

SEASON = "2027"

# (current name, expected team, expected role, new name or None, retire?)
RESOLUTIONS = [
    ("S Sharma", "RCB", "BOWL", "Suyash Sharma", False),
    ("M Singh", "KKR", "BAT", "Mandeep Singh", True),
    ("R Singh", "RCB", "BAT", None, True),
]


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

    cols = [r[1] for r in con.execute("PRAGMA table_info(player_roles)")]
    if "status" not in cols:
        print("ABORT: player_roles.status column missing "
              "(run migrate_demo_league_2026.py --apply first)",
              file=sys.stderr)
        return 3

    renames, retire_flags = [], []
    for cur_name, exp_team, exp_role, new_name, retire in RESOLUTIONS:
        rows = con.execute(
            """SELECT p.id, p.name, pr.role, pr.ipl_team_code, pr.status
               FROM players p JOIN player_roles pr ON pr.player_id = p.id
               WHERE p.name = ? AND pr.season = ?""",
            (cur_name, SEASON),
        ).fetchall()
        if not rows:
            # Already resolved (renamed rows no longer match cur_name).
            if new_name and con.execute(
                    "SELECT 1 FROM players WHERE name = ?",
                    (new_name,)).fetchone():
                print(f"  ok (already resolved): {cur_name} -> {new_name}")
                continue
            if not new_name:
                print(f"  ok (already checked): {cur_name} not present")
                continue
            print(f"ABORT: {cur_name!r} not found and target {new_name!r} "
                  "absent too", file=sys.stderr)
            return 3
        if len(rows) != 1:
            print(f"ABORT: expected 1 row for {cur_name!r}, found "
                  f"{len(rows)}", file=sys.stderr)
            return 3
        r = rows[0]
        if r["ipl_team_code"] != exp_team or r["role"] != exp_role:
            print(f"ABORT: {cur_name} guard failed: DB has "
                  f"{r['ipl_team_code']}/{r['role']}, expected "
                  f"{exp_team}/{exp_role}", file=sys.stderr)
            return 3
        if new_name:
            if con.execute("SELECT 1 FROM players WHERE name = ?",
                           (new_name,)).fetchone():
                print(f"ABORT: rename target {new_name!r} already exists",
                      file=sys.stderr)
                return 3
            renames.append((r["id"], cur_name, new_name))
        if retire and r["status"] != "retired":
            retire_flags.append((r["id"], new_name or cur_name))

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"[{mode}] renames: {len(renames)}")
    for _pid, old, new in renames:
        print(f"    {old} -> {new}")
    print(f"[{mode}] retired flags: {len(retire_flags)}")
    for _pid, nm in retire_flags:
        print(f"    {nm}")

    if not args.apply:
        print("dry-run: no writes. Re-run with --apply to commit.")
        return 0

    with con:
        for pid, _old, new in renames:
            con.execute("UPDATE players SET name = ? WHERE id = ?",
                        (new, pid))
        for pid, _nm in retire_flags:
            con.execute(
                "UPDATE player_roles SET status = 'retired' "
                "WHERE player_id = ? AND season = ?",
                (pid, SEASON))
    print(f"applied: {len(renames)} rename(s), "
          f"{len(retire_flags)} retired flag(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
