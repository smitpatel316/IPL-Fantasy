"""P4-D5 migration: deduplicate Varun Chakravarthy in the demo league DB.

Evidence (verified read-only against the Pi demo DB, 2026-10-12):
  id 43  "V Chakravarthy"  BOWL/KKR/os=0/active, source=sandbox
  id 103 "CV Varun"        BOWL/KKR/os=0/active, source=preseason-csv
Same person: registry (phase1/player_roles.csv) has Varun Chakravarthy as
KKR's BOWL in every season 2023-2026; the canonical universe and sandbox both
use "V Chakravarthy". "CV Varun" is the preseason-rank CSV's name form.
migrate_demo_league_2026.py already knew: its rename CV Varun -> V
Chakravarthy was SKIPPED because the target row existed (its lines 86-88,
97). Both rows were then auto-drafted in the demo draft (draft 1):
  id 43  -> pick 43, round 6,  team 6 (Anaya's Avengers), roster BOWL + wk1 BOWL
  id 103 -> pick 89, round 12, team 2 (Mansi's Marvels),  roster BN + wk1 UTIL

Consolidation (survivor = id 43, the canonical-name, earlier-picked row):
  draft_picks.player_id        103 -> 43   (1 row)
  roster_slots.player_id       103 -> 43   (2 rows)
  pre_draft_ranks              loser's 8 rows DELETED (survivor already holds
                               a rank row for every team; PK (team,player)
                               forbids repointing) after verifying coverage
  waiver_claims add/drop ids   103 -> 43   (0 rows today; handled generically)
  player_match_stats.player_id 103 -> 43   (0 rows today; handled generically)
  trades gives/receives JSON   int rewrite (0 trades today; handled)
  engine_state (scope=draft)   key-aware JSON rewrite: values under a
                               "player_id" key and bare ints inside
                               rosters.<team>.<SLOT> lists only. Expected
                               exactly 3 replacements (picks[88].player_id,
                               rosters.2.BN[0], event_log payload). NEVER a
                               blanket int replace: pick_no 103, seq 103 and
                               payload.pick_no 103 are NOT player ids.
  player_roles + players       loser rows deleted last.

CONSEQUENCE (deliberate, flagged for Atlas): after consolidation, player 43
is rostered by TWO demo teams (team 6 via pick 43, team 2 via pick 89) —
the double-draft already happened; this migration makes it one person
owned twice instead of two ghost rows. Voiding team 2's pick / awarding a
replacement is a league decision for Atlas, NOT done here.

Guards: aborts unless both rows exist with exactly the expected
name/role/team/status/source, and survivor rank coverage >= loser's.
Idempotent: a re-run after --apply reports "already deduplicated".

WAL WARNING: the Pi DB is WAL-mode with an uncheckpointed 4 MB WAL — back
up with `sqlite3 <db> .backup <file>` (or checkpoint first), never `cp`.

Usage (Atlas applies on the Pi, after a WAL-safe backup):
    python3 data/migrate_dedup_varun_p4d5.py --db ~/ipl-fantasy/data/ipl_fantasy.db          # dry run
    python3 data/migrate_dedup_varun_p4d5.py --db ~/ipl-fantasy/data/ipl_fantasy.db --apply
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

SURVIVOR = 43
LOSER = 103
EXPECT = {
    SURVIVOR: ("V Chakravarthy", "BOWL", "KKR", 0, "active", "sandbox"),
    LOSER: ("CV Varun", "BOWL", "KKR", 0, "active", "preseason-csv"),
}
SLOT_KEYS = {"WK", "BAT", "AR", "BOWL", "UTIL", "BN", "IL"}


def rewrite_engine_state(state, loser, survivor):
    """Key-aware player-id rewrite. Returns (new_state, replacement_count).

    Replaces the loser id only where the value is unambiguously a player id:
    a dict value under key "player_id", or a bare int inside a roster slot
    list (any list reached via a slot-named key under a "rosters" dict).
    """
    count = 0

    def walk(node, in_rosters=False, key=None):
        nonlocal count
        if isinstance(node, dict):
            out = {}
            for k, v in node.items():
                if k == "player_id" and v == loser:
                    out[k] = survivor
                    count += 1
                else:
                    out[k] = walk(v, in_rosters or k == "rosters", k)
            return out
        if isinstance(node, list):
            return [walk(v, in_rosters, key) for v in node]
        if in_rosters and key in SLOT_KEYS and isinstance(node, int) and node == loser:
            count += 1
            return survivor
        return node

    return walk(state), count


def plan(con):
    """Compute the full change set without writing. Returns dict or None."""
    rows = {}
    for pid in (SURVIVOR, LOSER):
        r = con.execute(
            """SELECT p.name, pr.role, pr.ipl_team_code, pr.is_overseas,
                      pr.status, pr.source
               FROM players p JOIN player_roles pr ON pr.player_id = p.id
               WHERE p.id = ?""", (pid,)).fetchone()
        rows[pid] = tuple(r) if r else None
    if rows[LOSER] is None:
        return {"already_done": True}
    if rows[SURVIVOR] is None:
        raise SystemExit(f"ABORT: survivor id {SURVIVOR} missing")
    for pid, exp in EXPECT.items():
        if rows[pid] != exp:
            raise SystemExit(f"ABORT: id {pid} guard failed: DB has {rows[pid]}, "
                             f"expected {exp}")
    p = {"already_done": False}
    p["draft_picks"] = con.execute(
        "SELECT COUNT(*) FROM draft_picks WHERE player_id = ?", (LOSER,)).fetchone()[0]
    p["roster_slots"] = con.execute(
        "SELECT COUNT(*) FROM roster_slots WHERE player_id = ?", (LOSER,)).fetchone()[0]
    p["match_stats"] = con.execute(
        "SELECT COUNT(*) FROM player_match_stats WHERE player_id = ?", (LOSER,)).fetchone()[0]
    p["waiver_refs"] = con.execute(
        "SELECT COUNT(*) FROM waiver_claims WHERE add_player_id = ? OR drop_player_id = ?",
        (LOSER, LOSER)).fetchone()[0]
    loser_teams = {r[0] for r in con.execute(
        "SELECT team_id FROM pre_draft_ranks WHERE player_id = ?", (LOSER,))}
    surv_teams = {r[0] for r in con.execute(
        "SELECT team_id FROM pre_draft_ranks WHERE player_id = ?", (SURVIVOR,))}
    if not loser_teams <= surv_teams:
        raise SystemExit(f"ABORT: survivor lacks rank rows for teams "
                         f"{sorted(loser_teams - surv_teams)}; cannot drop loser's ranks")
    p["rank_rows_deleted"] = len(loser_teams)
    p["trades_touched"] = 0
    for gives, receives in con.execute("SELECT gives, receives FROM trades"):
        for blob in (gives, receives):
            if LOSER in json.loads(blob or "[]"):
                p["trades_touched"] += 1
    p["engine_replacements"] = 0
    p["engine_states"] = []
    for scope, scope_id, state in con.execute(
            "SELECT scope, scope_id, state FROM engine_state"):
        _, n = rewrite_engine_state(json.loads(state), LOSER, SURVIVOR)
        if n:
            p["engine_replacements"] += n
            p["engine_states"].append((scope, scope_id, n))
    return p


def report(p, mode):
    if p.get("already_done"):
        print(f"[{mode}] already deduplicated: no loser row id {LOSER}, nothing to do.")
        return
    print(f"[{mode}] dedup plan: loser id {LOSER} ('CV Varun') -> survivor id {SURVIVOR} ('V Chakravarthy')")
    print(f"    draft_picks repoint:      {p['draft_picks']}")
    print(f"    roster_slots repoint:     {p['roster_slots']}")
    print(f"    pre_draft_ranks delete:   {p['rank_rows_deleted']} (survivor covers all teams)")
    print(f"    player_match_stats:       {p['match_stats']}")
    print(f"    waiver_claims refs:       {p['waiver_refs']}")
    print(f"    trades JSON blobs:        {p['trades_touched']}")
    print(f"    engine_state rewrites:    {p['engine_replacements']} in {p['engine_states']}")
    print(f"    player_roles + players:   delete loser rows (1 + 1)")
    print("    WARNING: survivor ends up rostered by team 6 (pick 43) AND team 2 "
          "(pick 89) — pre-existing double-draft; roster remedy is Atlas's call.")


def apply(con, p):
    with con:
        con.execute("UPDATE draft_picks SET player_id = ? WHERE player_id = ?",
                    (SURVIVOR, LOSER))
        con.execute("UPDATE roster_slots SET player_id = ? WHERE player_id = ?",
                    (SURVIVOR, LOSER))
        con.execute("UPDATE player_match_stats SET player_id = ? WHERE player_id = ?",
                    (SURVIVOR, LOSER))
        con.execute("UPDATE waiver_claims SET add_player_id = ? WHERE add_player_id = ?",
                    (SURVIVOR, LOSER))
        con.execute("UPDATE waiver_claims SET drop_player_id = ? WHERE drop_player_id = ?",
                    (SURVIVOR, LOSER))
        con.execute("DELETE FROM pre_draft_ranks WHERE player_id = ?", (LOSER,))
        for tid, gives, receives in con.execute(
                "SELECT id, gives, receives FROM trades").fetchall():
            ng = [SURVIVOR if x == LOSER else x for x in json.loads(gives or "[]")]
            nr = [SURVIVOR if x == LOSER else x for x in json.loads(receives or "[]")]
            if ng != json.loads(gives or "[]") or nr != json.loads(receives or "[]"):
                con.execute("UPDATE trades SET gives = ?, receives = ? WHERE id = ?",
                            (json.dumps(ng), json.dumps(nr), tid))
        for scope, scope_id, state in con.execute(
                "SELECT scope, scope_id, state FROM engine_state").fetchall():
            new_state, n = rewrite_engine_state(json.loads(state), LOSER, SURVIVOR)
            if n:
                con.execute("UPDATE engine_state SET state = ? WHERE scope = ? AND scope_id = ?",
                            (json.dumps(new_state), scope, scope_id))
        con.execute("DELETE FROM player_roles WHERE player_id = ?", (LOSER,))
        con.execute("DELETE FROM players WHERE id = ?", (LOSER,))


def verify(con):
    """Fail loudly if any reference to the loser survives."""
    left = []
    for table, col in (("draft_picks", "player_id"), ("roster_slots", "player_id"),
                       ("pre_draft_ranks", "player_id"),
                       ("player_match_stats", "player_id")):
        n = con.execute(f"SELECT COUNT(*) FROM {table} WHERE {col} = ?",
                        (LOSER,)).fetchone()[0]
        if n:
            left.append(f"{table}.{col}: {n}")
    n = con.execute("SELECT COUNT(*) FROM waiver_claims WHERE add_player_id = ? "
                    "OR drop_player_id = ?", (LOSER, LOSER)).fetchone()[0]
    if n:
        left.append(f"waiver_claims: {n}")
    if con.execute("SELECT COUNT(*) FROM players WHERE id = ?", (LOSER,)).fetchone()[0]:
        left.append("players row still present")
    for _scope, _sid, state in con.execute("SELECT scope, scope_id, state FROM engine_state"):
        _, n = rewrite_engine_state(json.loads(state), LOSER, SURVIVOR)
        if n:
            left.append(f"engine_state still has {n} loser refs")
    if left:
        raise SystemExit(f"VERIFY FAILED, loser refs remain: {left}")
    surv = {t: con.execute(f"SELECT COUNT(*) FROM {t} WHERE player_id = ?",
                           (SURVIVOR,)).fetchone()[0]
            for t in ("draft_picks", "roster_slots", "pre_draft_ranks")}
    print(f"verify OK: no refs to id {LOSER}; survivor id {SURVIVOR} refs: {surv}")
    return surv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/ipl_fantasy.db")
    ap.add_argument("--apply", action="store_true",
                    help="write changes (default is dry-run report)")
    args = ap.parse_args()
    db = Path(args.db)
    if not db.exists():
        print(f"DB not found: {db}", file=sys.stderr)
        return 2
    if args.apply:
        con = sqlite3.connect(str(db))
    else:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    p = plan(con)
    report(p, "APPLY" if args.apply else "DRY-RUN")
    if p.get("already_done"):
        verify(con)
        return 0
    if not args.apply:
        print("dry-run: no writes. Back up WAL-safely (sqlite3 .backup), "
              "then re-run with --apply.")
        return 0
    apply(con, p)
    verify(con)
    print("applied: deduplication complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
