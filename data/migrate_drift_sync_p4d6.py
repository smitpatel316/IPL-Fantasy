"""P4-D6 migration: drift fixes + demo-pool sync for the IPL demo league DB.

Implements Atlas's rulings (2026-10-12) on the P4-D4 three-way drift audit
(data/P4-D4-drift-report.md). ONE guarded, dry-run-default, idempotent
script. EVERY change is keyed by player id — name-keyed sync is unsafe
(the R Singh collision, audit section 2). Section-5b depth players (18)
stay untouched by design.

Scope:
  (1) DB role fixes:        S Iyer id45 AR->BAT, S Dube id15 BAT->AR.
  (2) BKG Mendis id97 -> name 'K Mendis', role AR, team SRH.
  (3) R Rinku id42 -> name 'R Singh' (Rinku Singh, KKR BAT). DEVIATION,
      forced by schema: players has UNIQUE(name, season), so id42 cannot
      take 'R Singh' while id35 holds it. The retired, unidentified
      R Singh id35 therefore gets a LABEL-ONLY rename to
      'R Singh (unidentified)' — role/team/status/source unchanged, still
      retired, never merged or deleted (the disambiguation the audit's
      decision #4 proposed). Every step here is id-keyed so the two rows
      can never be conflated either way.
  (4) Registry fixes:       A Rawat id118 BAT->WK; N Dhir id11 BAT->AR;
                            A Madhwal id12 team MI->CSK.
  (5) Pool sync: insert the universe players missing from the DB (52 by
      exact name; K Mendis is covered by step (2)'s rename, so 51 net new
      rows). Existing ids are never renumbered; AUTOINCREMENT assigns new
      ids. For the 4 registry-vs-universe role conflicts (T Stubbs,
      R Powell, H Patel, Ashutosh Sharma) the REGISTRY role wins and each
      is flagged in the report. New rows: players(season='2027') +
      player_roles(season='2027', status='active', source='universe-sync').
      No pre_draft_ranks rows are created — the demo draft is complete and
      ranks were per-team draft artifacts (Atlas: seed separately if a
      fresh draft is ever wanted).
  (6) Flag the 14 section-5d legacy actives status='retired' (flag, never
      delete — drafted rows reference them): ids 14, 17, 36, 58, 74, 83,
      84, 89, 93, 102, 107, 115, 117, 122.
  (7) Varun dedup, VOID variant (data/migrate_dedup_varun_p4d5.py as
      amended by P4-D6): team 2's duplicate pick 89 is void — the loser's
      draft_pick + roster_slots are deleted, its engine_state pick /
      roster entry / draft.pick event are removed; survivor id43 keeps
      team 6's legitimate pick 43 only.
  (8) Canonical universe fix lives in the repo, not the DB: P Cummins
      BOWL->AR in data/seed_players_universe.json (same branch as this
      script). The DB + registry already say AR, so no DB row changes.

Guards: every id-keyed step first asserts the row still matches the
audited name/role/team/status; any mismatch aborts the whole run before a
single write. Steps already applied are detected and skipped, so a
re-run after --apply is a clean no-op report.

WAL WARNING: the Pi DB lives in its WAL — back up with sqlite3 .backup /
the Python backup API (or checkpoint first), NEVER cp. --apply refuses
to run while a non-empty -wal file sits next to the DB unless that exact
path was just checkpointed by this run's own pre-apply backup step:
pass --backup-out <file> and the script takes a WAL-safe backup first
and verifies it before writing anything.

Usage (Atlas applies on the Pi after reviewing the dry-run):
    python3 data/migrate_drift_sync_p4d6.py --db ~/ipl-fantasy/data/ipl_fantasy.db
    python3 data/migrate_drift_sync_p4d6.py --db ~/ipl-fantasy/data/ipl_fantasy.db \
        --backup-out ~/ipl-fantasy/data/ipl_fantasy.db.bak-p4d6 --apply
"""

import argparse
import importlib.util
import json
import sqlite3
import sys
from pathlib import Path

SEASON = "2027"
HERE = Path(__file__).resolve().parent

# --- steps (1)-(4): (id, expected current name, field, expected, new) ---
ROLE_FIXES = [
    (45, "S Iyer", "AR", "BAT"),          # (1) audit section 1: DB wrong
    (15, "S Dube", "BAT", "AR"),          # (1) audit section 1: DB wrong
    (118, "A Rawat", "BAT", "WK"),        # (4) audit section 5c: registry WK
    (11, "N Dhir", "BAT", "AR"),          # (4) audit section 5c: registry AR
]
TEAM_FIXES = [
    (12, "A Madhwal", "MI", "CSK"),       # (4) audit section 5c: registry CSK
]
MENDIS_ID = 97                            # (2) BKG Mendis -> K Mendis/AR/SRH
MENDIS_EXPECT = ("BKG Mendis", "BAT", "GT")
MENDIS_NEW = ("K Mendis", "AR", "SRH")
RINKU_ID = 42                             # (3) R Rinku -> R Singh
RETIRED_R_SINGH_ID = 35                   # (3) label-only disambiguation
RETIRED_R_SINGH_LABEL = "R Singh (unidentified)"

# (6) audit section 5d: id -> name (guard)
LEGACY_RETIRE = {
    14: "D Conway", 17: "M Ali", 36: "M Bhandage", 58: "JM Bairstow",
    74: "RR Rossouw", 83: "R Gurbaz", 84: "J Little", 89: "W O'Rourke",
    93: "Naveen-ul-Haq", 102: "DJ Mitchell", 107: "S Atal",
    115: "V Kaverappa", 117: "R Salam", 122: "T Kotian",
}

# (5) registry role wins over the universe role for these four
# (phase1/player_roles.csv, season 2026; audit section 4):
#   T Stubbs (Tristan Stubbs) WK->BAT, R Powell (Rovman Powell) AR->BAT,
#   H Patel (Harshal Patel) BOWL->AR, Ashutosh Sharma AR->BAT
REGISTRY_ROLE_OVERRIDES = {
    "T Stubbs": "BAT",
    "R Powell": "BAT",
    "H Patel": "AR",
    "Ashutosh Sharma": "BAT",
}


def load_dedup_module():
    spec = importlib.util.spec_from_file_location(
        "dedup_p4d5", HERE / "migrate_dedup_varun_p4d5.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def fetch_role_row(con, pid):
    r = con.execute(
        """SELECT p.name, pr.role, pr.ipl_team_code, pr.is_overseas, pr.status
           FROM players p JOIN player_roles pr ON pr.player_id = p.id
           WHERE p.id = ? AND pr.season = ?""", (pid, SEASON)).fetchone()
    return tuple(r) if r else None


def plan(con, universe):
    """Compute the full change set (no writes). Raises SystemExit on any
    guard failure. Returns a dict consumed by report() and apply()."""
    p = {"role_fixes": [], "team_fixes": [], "renames": [],
         "retire": [], "inserts": [], "insert_flags": [],
         "disambiguate": None}

    for pid, name, old, new in ROLE_FIXES:
        row = fetch_role_row(con, pid)
        if row is None:
            raise SystemExit(f"ABORT: id {pid} ({name}) missing")
        if row[0] != name:
            raise SystemExit(f"ABORT: id {pid} name guard: DB has {row[0]!r}, "
                             f"expected {name!r}")
        if row[1] == new:
            continue  # already applied
        if row[1] != old:
            raise SystemExit(f"ABORT: id {pid} ({name}) role guard: DB has "
                             f"{row[1]}, expected {old} (or {new} if applied)")
        p["role_fixes"].append((pid, name, old, new))

    for pid, name, old, new in TEAM_FIXES:
        row = fetch_role_row(con, pid)
        if row is None or row[0] != name:
            raise SystemExit(f"ABORT: id {pid} ({name}) missing/renamed: {row}")
        if row[2] == new:
            continue
        if row[2] != old:
            raise SystemExit(f"ABORT: id {pid} ({name}) team guard: DB has "
                             f"{row[2]}, expected {old} (or {new} if applied)")
        p["team_fixes"].append((pid, name, old, new))

    # (2) Mendis rename + role/team
    row = fetch_role_row(con, MENDIS_ID)
    if row is None:
        raise SystemExit(f"ABORT: id {MENDIS_ID} missing")
    if row[0] == MENDIS_NEW[0]:
        if row[1] != MENDIS_NEW[1] or row[2] != MENDIS_NEW[2]:
            raise SystemExit(f"ABORT: id {MENDIS_ID} already renamed but "
                             f"role/team are {row[1]}/{row[2]}, expected "
                             f"{MENDIS_NEW[1]}/{MENDIS_NEW[2]}")
    elif (row[0], row[1], row[2]) == MENDIS_EXPECT:
        p["renames"].append((MENDIS_ID, row[0], MENDIS_NEW[0],
                             row[1], MENDIS_NEW[1], row[2], MENDIS_NEW[2]))
    else:
        raise SystemExit(f"ABORT: id {MENDIS_ID} guard: DB has "
                         f"{row[0]}/{row[1]}/{row[2]}, expected {MENDIS_EXPECT}")

    # (3) Rinku rename + id35 label disambiguation (paired: UNIQUE(name,
    # season) means id35's label must move before id42 can take the name;
    # apply() performs the id35 label first for the same reason).
    row35 = fetch_role_row(con, RETIRED_R_SINGH_ID)
    if row35 is None or row35[4] != "retired" or row35[2] != "RCB" \
            or row35[0] not in ("R Singh", RETIRED_R_SINGH_LABEL):
        raise SystemExit(f"ABORT: retired R Singh id {RETIRED_R_SINGH_ID} "
                         f"guard failed: {row35}")
    row = fetch_role_row(con, RINKU_ID)
    if row is None:
        raise SystemExit(f"ABORT: id {RINKU_ID} missing")
    rinku_done = (row[0] == "R Singh" and row[1] == "BAT" and row[2] == "KKR"
                  and row35[0] == RETIRED_R_SINGH_LABEL)
    if rinku_done:
        pass  # pair already applied
    elif row[0] == "R Rinku" and row[1] == "BAT" and row[2] == "KKR" \
            and row35[0] == "R Singh":
        p["disambiguate"] = (RETIRED_R_SINGH_ID, "R Singh",
                             RETIRED_R_SINGH_LABEL)
        p["renames"].append((RINKU_ID, "R Rinku", "R Singh",
                             None, None, None, None))
    else:
        raise SystemExit(f"ABORT: id {RINKU_ID}/id {RETIRED_R_SINGH_ID} "
                         f"pair guard: DB has id42={row}, id35={row35}")

    # (6) legacy retire flags
    for pid, name in sorted(LEGACY_RETIRE.items()):
        row = fetch_role_row(con, pid)
        if row is None or row[0] != name:
            raise SystemExit(f"ABORT: legacy id {pid} guard: expected {name!r}, "
                             f"DB has {row}")
        if row[4] == "retired":
            continue  # already flagged
        if row[4] != "active":
            raise SystemExit(f"ABORT: legacy id {pid} ({name}) status guard: "
                             f"DB has {row[4]!r}")
        p["retire"].append((pid, name))

    # (5) pool sync: universe names missing from the DB. After step (2)
    # 'K Mendis' will exist, so it is excluded from inserts whenever the
    # Mendis rename is pending or already applied.
    db_names = {r[0] for r in con.execute("SELECT name FROM players")}
    if any(r[0] == MENDIS_ID for r in p["renames"]):
        db_names.add(MENDIS_NEW[0])
    for entry in universe:
        if entry["name"] in db_names:
            continue
        role = entry["role"]
        if entry["name"] in REGISTRY_ROLE_OVERRIDES:
            role = REGISTRY_ROLE_OVERRIDES[entry["name"]]
            p["insert_flags"].append(
                (entry["name"], entry["role"], role,
                 "registry-vs-universe conflict, registry wins"))
        p["inserts"].append((entry["name"], role, entry["is_overseas"],
                             entry["team"]))
    return p


def report(p, dedup_plan, mode):
    print(f"[{mode}] P4-D6 drift-fix + pool-sync plan")
    print(f"  (1)+(4) role fixes: {len(p['role_fixes'])}")
    for pid, name, old, new in p["role_fixes"]:
        print(f"      id {pid} {name}: role {old} -> {new}")
    print(f"  (4) team fixes: {len(p['team_fixes'])}")
    for pid, name, old, new in p["team_fixes"]:
        print(f"      id {pid} {name}: team {old} -> {new}")
    print(f"  (2)+(3) renames/fixes: {len(p['renames'])}")
    for pid, old_name, new_name, old_role, new_role, old_team, new_team in p["renames"]:
        extra = ""
        if new_role:
            extra = f", role {old_role} -> {new_role}, team {old_team} -> {new_team}"
        print(f"      id {pid}: {old_name!r} -> {new_name!r}{extra}")
    if p.get("disambiguate"):
        pid, old_label, new_label = p["disambiguate"]
        print(f"      id {pid}: {old_label!r} -> {new_label!r} "
              f"(LABEL-ONLY disambiguation: still retired/RCB/BAT; required "
              f"by UNIQUE(name, season) so id {RINKU_ID} can take 'R Singh')")
    else:
        print(f"      (id {RETIRED_R_SINGH_ID} already labelled "
              f"{RETIRED_R_SINGH_LABEL!r}, still retired/RCB — untouched)")
    print(f"  (6) legacy actives to flag retired: {len(p['retire'])}")
    for pid, name in p["retire"]:
        print(f"      id {pid} {name}: active -> retired")
    print(f"  (5) universe players to insert: {len(p['inserts'])} "
          f"(new ids assigned by AUTOINCREMENT; existing ids preserved)")
    for name, role, os_, team in p["inserts"]:
        print(f"      + {name}: {role}/{team}/os={os_} (source=universe-sync)")
    for name, urole, rrole, why in p["insert_flags"]:
        print(f"      FLAG {name}: universe role {urole} overridden -> {rrole} ({why})")
    print("      note: no pre_draft_ranks rows for inserts (demo draft complete)")
    print("  (7) Varun dedup (VOID variant):")
    if dedup_plan.get("already_done"):
        print("      already deduplicated, nothing to do")
    else:
        print(f"      draft_picks DELETE (pick 89 void): {dedup_plan['draft_picks']}")
        print(f"      roster_slots DELETE:              {dedup_plan['roster_slots']}")
        print(f"      pre_draft_ranks DELETE (loser):   {dedup_plan['rank_rows_deleted']}")
        print(f"      player_match_stats repoint:       {dedup_plan['match_stats']}")
        print(f"      waiver_claims refs repoint:       {dedup_plan['waiver_refs']}")
        print(f"      trades JSON blobs repoint:        {dedup_plan['trades_touched']}")
        print(f"      engine_state void removals:       {dedup_plan['engine_void']}")
        print("      player_roles + players:           delete loser id 103 rows")
    total = (len(p["role_fixes"]) + len(p["team_fixes"]) + len(p["renames"])
             + len(p["retire"]) + len(p["inserts"]))
    print(f"  DB steps pending (excl. dedup): {total}; "
          f"(8) universe JSON Cummins fix is a repo change on this branch, "
          f"not a DB step.")


def apply(con, p, dedup):
    """All DB steps + the dedup, in ONE transaction."""
    with con:
        if p.get("disambiguate"):
            pid, _old_label, new_label = p["disambiguate"]
            con.execute("UPDATE players SET name = ? WHERE id = ?",
                        (new_label, pid))
        for pid, _name, _old, new in p["role_fixes"]:
            con.execute("UPDATE player_roles SET role = ? "
                        "WHERE player_id = ? AND season = ?",
                        (new, pid, SEASON))
        for pid, _name, _old, new in p["team_fixes"]:
            con.execute("UPDATE player_roles SET ipl_team_code = ? "
                        "WHERE player_id = ? AND season = ?",
                        (new, pid, SEASON))
        for pid, _on, new_name, _or, new_role, _ot, new_team in p["renames"]:
            con.execute("UPDATE players SET name = ? WHERE id = ?",
                        (new_name, pid))
            if new_role:
                con.execute("UPDATE player_roles SET role = ?, ipl_team_code = ? "
                            "WHERE player_id = ? AND season = ?",
                            (new_role, new_team, pid, SEASON))
        for pid, _name in p["retire"]:
            con.execute("UPDATE player_roles SET status = 'retired' "
                        "WHERE player_id = ? AND season = ?",
                        (pid, SEASON))
        for name, role, os_, team in p["inserts"]:
            cur = con.execute("INSERT INTO players (name, season) VALUES (?, ?)",
                              (name, SEASON))
            con.execute(
                """INSERT INTO player_roles
                       (player_id, season, role, is_overseas, ipl_team_code,
                        source, status)
                   VALUES (?, ?, ?, ?, ?, 'universe-sync', 'active')""",
                (cur.lastrowid, SEASON, role, os_, team))
        if not dedup["plan"].get("already_done"):
            dedup["apply"](con, dedup["plan"])


def verify(con, dedup):
    """Fail loudly unless the post-state matches every ruling."""
    problems = []
    expect_roles = {45: "BAT", 15: "AR", 118: "WK", 11: "AR", 97: "AR"}
    for pid, role in expect_roles.items():
        row = fetch_role_row(con, pid)
        if not row or row[1] != role:
            problems.append(f"id {pid} role is {row and row[1]}, expected {role}")
    row = fetch_role_row(con, 12)
    if not row or row[2] != "CSK":
        problems.append(f"id 12 team is {row and row[2]}, expected CSK")
    row = fetch_role_row(con, MENDIS_ID)
    if not row or row[0] != "K Mendis" or row[2] != "SRH":
        problems.append(f"id 97 is {row}, expected K Mendis/AR/SRH")
    row = fetch_role_row(con, RINKU_ID)
    if not row or row[0] != "R Singh" or row[2] != "KKR":
        problems.append(f"id 42 is {row}, expected R Singh (Rinku)/BAT/KKR")
    row = fetch_role_row(con, RETIRED_R_SINGH_ID)
    if not row or row[0] != RETIRED_R_SINGH_LABEL or row[4] != "retired" \
            or row[2] != "RCB" or row[1] != "BAT":
        problems.append(f"id 35 unexpected post-state: {row}")
    for pid, name in LEGACY_RETIRE.items():
        row = fetch_role_row(con, pid)
        if not row or row[4] != "retired":
            problems.append(f"legacy id {pid} ({name}) not retired: {row}")
    if problems:
        raise SystemExit(f"VERIFY FAILED: {problems}")
    n_players = con.execute("SELECT COUNT(*) FROM players").fetchone()[0]
    n_universe = con.execute(
        "SELECT COUNT(*) FROM player_roles WHERE source = 'universe-sync'"
    ).fetchone()[0]
    fk = con.execute("PRAGMA foreign_key_check").fetchall()
    if fk:
        raise SystemExit(f"VERIFY FAILED: foreign_key_check violations: {fk}")
    print(f"verify OK: role/team/rename/retire state matches rulings; "
          f"players total = {n_players}; universe-sync rows = {n_universe}; "
          f"FK check clean")
    if not dedup["plan"].get("already_done"):
        dedup["verify"](con)
    return n_players


def wal_safe_backup(db_path, out_path):
    """WAL-safe backup via the sqlite backup API + verification."""
    src = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    dst = sqlite3.connect(str(out_path))
    try:
        src.backup(dst)
        n = dst.execute("SELECT COUNT(*) FROM players").fetchone()[0]
        has_status = dst.execute(
            "SELECT COUNT(*) FROM pragma_table_info('player_roles') "
            "WHERE name = 'status'").fetchone()[0]
    finally:
        dst.close()
        src.close()
    if not has_status:
        raise SystemExit("ABORT: backup verification failed — player_roles "
                         "has no status column in the backup (stale snapshot?)")
    print(f"backup written + verified: {out_path} ({n} players, "
          f"status column present)")
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/ipl_fantasy.db")
    ap.add_argument("--universe", default=str(HERE / "seed_players_universe.json"),
                    help="canonical universe JSON (default: alongside this script)")
    ap.add_argument("--backup-out", default=None,
                    help="with --apply: take a verified WAL-safe backup here first")
    ap.add_argument("--apply", action="store_true",
                    help="write changes (default is dry-run report)")
    args = ap.parse_args()

    db = Path(args.db)
    if not db.exists():
        print(f"DB not found: {db}", file=sys.stderr)
        return 2
    universe = json.loads(Path(args.universe).read_text())
    if len(universe) != 129:
        print(f"ABORT: universe has {len(universe)} players, expected 129",
              file=sys.stderr)
        return 3

    dedup_mod = load_dedup_module()
    dedup = {"apply": dedup_mod.apply, "verify": dedup_mod.verify}

    if args.apply:
        wal = Path(str(db) + "-wal")
        if wal.exists() and wal.stat().st_size > 0 and not args.backup_out:
            print("ABORT: DB has a non-empty WAL and no --backup-out given. "
                  "Re-run with --backup-out <file> so a verified WAL-safe "
                  "backup is taken before any write.", file=sys.stderr)
            return 3
        if args.backup_out:
            wal_safe_backup(db, Path(args.backup_out))
        con = sqlite3.connect(str(db))
    else:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)

    p = plan(con, universe)
    dedup["plan"] = dedup_mod.plan(con)
    report(p, dedup["plan"], "APPLY" if args.apply else "DRY-RUN")

    pending = (len(p["role_fixes"]) + len(p["team_fixes"]) + len(p["renames"])
               + len(p["retire"]) + len(p["inserts"]))
    if pending == 0 and dedup["plan"].get("already_done"):
        verify(con, dedup)
        print("nothing to do: migration already fully applied (idempotent).")
        return 0
    if not args.apply:
        print("dry-run: no writes. Atlas: back up WAL-safely, then re-run "
              "with --backup-out <file> --apply.")
        return 0
    apply(con, p, dedup)
    verify(con, dedup)
    print("applied: P4-D6 drift-fix + pool-sync complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
