"""One-off migration: bring the demo league's player data in line with the
IPL 2026 season (post Dec-2025 mini-auction squads).

What it does (season 2027 player_roles rows):
  1. Renames players whose names were stored in the old multi-initial /
     typo'd format to the canonical `X Surname` universe names
     (e.g. "JC Buttler" -> "J Buttler", "D Santner" -> "M Santner").
  2. Updates `ipl_team_code` for players who changed franchises
     (e.g. Q de Kock KKR->MI, S Curran CSK->RR, R Jadeja CSK->RR).
  3. Flags retired players via `player_roles.status = 'retired'`
     (adds the column if missing). Retired: D Karthik, S Dhawan,
     P Chawla, R Ashwin, A Russell, K Pollard.

What it NEVER does: delete players, touch drafts / roster_slots /
lineup_slots / pre_draft_ranks. Drafted players keep their rows and picks;
only their team code / name / status is corrected.

Ambiguous old names ("R Singh" at RCB, "M Singh" at KKR, "S Sharma" at RCB)
cannot be tied to a real person with confidence -> reported, left unchanged.
Players not in the 2026 universe and not retired (e.g. D Conway, M Ali) are
reported and left unchanged. Role mismatches vs the universe are reported
but not changed (out of scope for this migration).

Usage (run from the Pi checkout, reviewed first):
    python3 data/migrate_demo_league_2026.py --db ~/ipl-fantasy/data/ipl_fantasy.db   # dry run
    python3 data/migrate_demo_league_2026.py --db ~/ipl-fantasy/data/ipl_fantasy.db --apply

Idempotent: re-running after --apply reports zero changes.
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

SEASON = "2027"

# Canonical IPL 2026 universe: name -> ipl_team_code.
# (Mirrors data/seed_players_universe.json on ipl/data/player-universe-2026;
# embedded here so this script is self-contained. --universe can override.)
TEAM_MAP = {
    "R Sharma": "MI", "S Yadav": "MI", "T Varma": "MI", "H Pandya": "MI",
    "J Bumrah": "MI", "T Boult": "MI", "D Chahar": "MI", "R Rickelton": "MI",
    "Q de Kock": "MI", "M Santner": "MI", "W Jacks": "MI", "S Thakur": "MI",
    "R Gaikwad": "CSK", "S Samson": "CSK", "MS Dhoni": "CSK", "S Dube": "CSK",
    "D Brevis": "CSK", "J Overton": "CSK", "N Ahmad": "CSK", "K Ahmed": "CSK",
    "M Henry": "CSK", "A Hosein": "CSK", "M Short": "CSK",
    "Sarfaraz Khan": "CSK", "R Chahar": "CSK",
    "V Kohli": "RCB", "R Patidar": "RCB", "D Padikkal": "RCB", "P Salt": "RCB",
    "J Sharma": "RCB", "K Pandya": "RCB", "T David": "RCB", "R Shepherd": "RCB",
    "J Hazlewood": "RCB", "B Kumar": "RCB", "Suyash Sharma": "RCB",
    "J Bethell": "RCB", "V Iyer": "RCB", "Y Dayal": "RCB",
    "A Rahane": "KKR", "A Raghuvanshi": "KKR", "R Singh": "KKR",
    "S Narine": "KKR", "V Chakravarthy": "KKR", "C Green": "KKR",
    "M Pathirana": "KKR", "M Rahman": "KKR", "R Ravindra": "KKR",
    "H Rana": "KKR", "R Powell": "KKR", "F Allen": "KKR",
    "K Rahul": "DC", "A Patel": "DC", "K Yadav": "DC", "M Starc": "DC",
    "T Natarajan": "DC", "T Stubbs": "DC", "N Rana": "DC", "P Nissanka": "DC",
    "D Miller": "DC", "A Porel": "DC", "Ashutosh Sharma": "DC",
    "L Ngidi": "DC", "K Jamieson": "DC", "P Shaw": "DC",
    "P Cummins": "SRH", "T Head": "SRH", "A Sharma": "SRH", "I Kishan": "SRH",
    "H Klaasen": "SRH", "N Reddy": "SRH", "H Patel": "SRH",
    "L Livingstone": "SRH", "B Carse": "SRH", "J Unadkat": "SRH",
    "E Malinga": "SRH", "K Mendis": "SRH", "A Verma": "SRH",
    "Y Jaiswal": "RR", "R Parag": "RR", "R Jadeja": "RR", "D Jurel": "RR",
    "S Hetmyer": "RR", "J Archer": "RR", "R Bishnoi": "RR", "S Curran": "RR",
    "T Deshpande": "RR", "S Sharma": "RR", "V Suryavanshi": "RR",
    "L Pretorius": "RR", "N Burger": "RR",
    "S Iyer": "PBKS", "A Singh": "PBKS", "Y Chahal": "PBKS",
    "M Stoinis": "PBKS", "S Singh": "PBKS", "N Wadhera": "PBKS",
    "P Singh": "PBKS", "P Arya": "PBKS", "A Omarzai": "PBKS",
    "L Ferguson": "PBKS", "M Jansen": "PBKS", "M Owen": "PBKS",
    "X Bartlett": "PBKS", "C Connolly": "PBKS",
    "S Gill": "GT", "B S Sudharsan": "GT", "J Buttler": "GT",
    "W Sundar": "GT", "R Khan": "GT", "K Rabada": "GT", "M Siraj": "GT",
    "P Krishna": "GT", "G Phillips": "GT", "R Tewatia": "GT",
    "J Holder": "GT", "I Sharma": "GT",
    "R Pant": "LSG", "N Pooran": "LSG", "M Yadav": "LSG", "M Shami": "LSG",
    "A Khan": "LSG", "M Marsh": "LSG", "A Markram": "LSG", "J Inglis": "LSG",
    "W Hasaranga": "LSG", "A Nortje": "LSG", "D Rathi": "LSG",
    "M Khan": "LSG",
}

# Old DB name -> canonical universe name (multi-initial format normalizations,
# plus two clear typo/shorthand fixes). A rename is SKIPPED with a warning if
# the target name already exists as another player row (e.g. "CV Varun" vs
# the sandbox's "V Chakravarthy" -- same person seeded twice).
NAME_ALIASES = {
    "JC Buttler": "J Buttler", "TM Head": "T Head", "PJ Cummins": "P Cummins",
    "RD Rickelton": "R Rickelton", "RR Pant": "R Pant",
    "SV Samson": "S Samson", "WG Jacks": "W Jacks", "MR Marsh": "M Marsh",
    "JO Holder": "J Holder", "AR Patel": "A Patel", "N K Reddy": "N Reddy",
    "M P Krishna": "P Krishna", "AK Markram": "A Markram",
    "JC Archer": "J Archer", "AJ Hosein": "A Hosein", "AM Rahane": "A Rahane",
    "KL Rahul": "K Rahul", "JP Inglis": "J Inglis", "FH Allen": "F Allen",
    "YBK Jaiswal": "Y Jaiswal", "CV Varun": "V Chakravarthy",
    "D Santner": "M Santner", "R Rinku": "R Singh", "PP Shaw": "P Shaw",
}

# Confirmed retired from IPL/all cricket (verified Sep 2026). DB-side names.
RETIRED = {
    "KD Karthik",      # all cricket, Jun 2024
    "S Dhawan",        # all cricket, Aug 2024
    "PP Chawla",       # all cricket, Jun 2025
    "R Ashwin",        # IPL, Aug 2025
    "A Russell",       # IPL, Nov 2025
    "K Pollard",       # IPL, Nov 2022
    "W Saha",          # all cricket, Feb 2025 (defensive; may not be in DB)
    "F du Plessis",    # IPL opt-out Nov 2025 (defensive; may not be in DB)
}

# Old names that cannot be tied to a real person with confidence -> report only.
AMBIGUOUS = {"R Singh", "M Singh", "S Sharma"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/ipl_fantasy.db")
    ap.add_argument("--apply", action="store_true",
                    help="write changes (default is dry-run report)")
    ap.add_argument("--universe", default=None,
                    help="optional path to seed_players_universe.json to "
                         "override the embedded TEAM_MAP")
    args = ap.parse_args()

    team_map = dict(TEAM_MAP)
    if args.universe:
        for p in json.loads(Path(args.universe).read_text()):
            team_map[p["name"]] = p["team"]

    db = Path(args.db)
    if not db.exists():
        print(f"DB not found: {db}", file=sys.stderr)
        return 2
    con = sqlite3.connect(str(db))
    con.row_factory = sqlite3.Row

    cols = [r[1] for r in con.execute("PRAGMA table_info(player_roles)")]
    has_status = "status" in cols

    rows = con.execute(
        """SELECT p.id, p.name, pr.role, pr.is_overseas, pr.ipl_team_code,
                  pr.source%s
           FROM players p JOIN player_roles pr ON pr.player_id = p.id
           WHERE pr.season = ?"""
        % (", pr.status" if has_status else ""),
        (SEASON,),
    ).fetchall()
    all_names = {r["name"] for r in rows}

    renames, team_changes, retire_flags = [], [], []
    skipped_rename, ambiguous, unknown, role_diffs = [], [], [], []

    for r in rows:
        pid, name = r["id"], r["name"]
        if name in AMBIGUOUS:
            ambiguous.append(name)
            continue
        new_name = NAME_ALIASES.get(name, name)
        if new_name != name:
            if new_name in all_names:
                skipped_rename.append((name, new_name))
                new_name = name  # keep original; team/retired logic on it
            else:
                renames.append((name, new_name))
        new_team = team_map.get(new_name)
        if new_team is None and new_name not in RETIRED:
            unknown.append(name)
        elif new_team and new_team != r["ipl_team_code"]:
            team_changes.append((new_name, r["ipl_team_code"], new_team))
        if name in RETIRED or new_name in RETIRED:
            if not has_status or r["status"] != "retired":
                retire_flags.append(new_name)

    # Role drift vs universe (reported only -- out of scope for this migration).
    uni_roles = {}
    if args.universe:
        for p in json.loads(Path(args.universe).read_text()):
            uni_roles[p["name"]] = p["role"]
    for r in rows:
        new_name = NAME_ALIASES.get(r["name"], r["name"])
        if new_name in uni_roles and uni_roles[new_name] != r["role"]:
            role_diffs.append((new_name, r["role"], uni_roles[new_name]))

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"[{mode}] players scanned: {len(rows)}")
    print(f"  renames: {len(renames)}")
    for old, new in renames:
        print(f"    {old} -> {new}")
    print(f"  team-code changes: {len(team_changes)}")
    for nm, old_t, new_t in team_changes:
        print(f"    {nm}: {old_t} -> {new_t}")
    print(f"  retired flags: {len(retire_flags)}")
    for nm in retire_flags:
        print(f"    {nm}")
    if skipped_rename:
        print(f"  renames SKIPPED (target name already exists): {len(skipped_rename)}")
        for old, new in skipped_rename:
            print(f"    {old} -/-> {new}")
    if ambiguous:
        print(f"  ambiguous (unchanged, needs human call): {sorted(set(ambiguous))}")
    if unknown:
        print(f"  not in 2026 universe, unchanged: {len(set(unknown))}")
    if role_diffs:
        print(f"  role drift vs universe (reported only): {len(role_diffs)}")
        for nm, old_r, new_r in role_diffs:
            print(f"    {nm}: {old_r} -> {new_r}")

    if not args.apply:
        print("dry-run: no writes. Re-run with --apply to commit.")
        return 0

    with con:
        if not has_status:
            con.execute("ALTER TABLE player_roles ADD COLUMN status TEXT DEFAULT 'active'")
        for old, new in renames:
            con.execute("UPDATE players SET name = ? WHERE id = ?",
                        (new, next(r["id"] for r in rows if r["name"] == old)))
        for nm, _old_t, new_t in team_changes:
            con.execute(
                "UPDATE player_roles SET ipl_team_code = ? WHERE season = ? AND player_id = "
                "(SELECT id FROM players WHERE name = ?)",
                (new_t, SEASON, nm))
        for nm in retire_flags:
            con.execute(
                "UPDATE player_roles SET status = 'retired' WHERE season = ? AND player_id = "
                "(SELECT id FROM players WHERE name = ?)",
                (SEASON, nm))
    print(f"applied: {len(renames)} renames, {len(team_changes)} team changes, "
          f"{len(retire_flags)} retired flags.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
