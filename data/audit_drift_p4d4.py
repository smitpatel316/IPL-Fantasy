"""P4-D4: three-way role/team drift audit (READ-ONLY, produces a report).

Compares the three player-universe sources that must agree but historically
haven't:

  A. canonical universe  data/seed_players_universe.json  (129 players)
  B. Pi demo-league DB   players + player_roles (season 2027) — pass either a
                         live sqlite path (--db, WAL alongside) or a JSON dump
                         produced read-only from the Pi (--db-json) of the form
                         {"players": [{id,name,role,is_overseas,
                         ipl_team_code,source,status}], "refs": {...}}
  C. sandbox seed        api/sandbox.py MOCK_SQUADS (48 players, 4 franchises)

No writes to any source. Output is a Markdown report on stdout (or --out).

Usage:
    python3 data/audit_drift_p4d4.py --db-json pi_live.json > report.md
    python3 data/audit_drift_p4d4.py --db data/ipl_fantasy.db > report.md
"""

import argparse
import ast
import json
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_universe(path):
    rows = json.loads(Path(path).read_text())
    return {r["name"]: {"role": r["role"], "os": int(r["is_overseas"]),
                         "team": r["team"], "pred": r.get("pred")} for r in rows}


def load_sandbox(path):
    tree = ast.parse(Path(path).read_text())
    squads = None
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) \
                and node.target.id == "MOCK_SQUADS":
            squads = ast.literal_eval(node.value)
        elif isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "MOCK_SQUADS" for t in node.targets):
            squads = ast.literal_eval(node.value)
    if squads is None:
        raise SystemExit("MOCK_SQUADS not found in sandbox.py")
    out = {}
    for team, players in squads.items():
        for name, role, overseas in players:
            out[name] = {"role": role, "os": 1 if overseas else 0, "team": team}
    return out


def load_db_json(path):
    d = json.loads(Path(path).read_text())
    out = {}
    for r in d["players"]:
        out[r["name"]] = {"role": r["role"], "os": int(r["is_overseas"] or 0),
                          "team": r["ipl_team_code"], "id": r["id"],
                          "source": r["source"], "status": r["status"]}
    return out, d.get("refs", {})


def load_db_sqlite(path):
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    has_status = "status" in [r[1] for r in con.execute("PRAGMA table_info(player_roles)")]
    status_expr = "pr.status" if has_status else "'<no status col>'"
    out = {}
    for r in con.execute(
            f"""SELECT p.id, p.name, pr.role, pr.is_overseas, pr.ipl_team_code,
                pr.source, {status_expr} AS status
                FROM players p LEFT JOIN player_roles pr ON pr.player_id = p.id
                ORDER BY p.id"""):
        out[r["name"]] = {"role": r["role"], "os": int(r["is_overseas"] or 0),
                          "team": r["ipl_team_code"], "id": r["id"],
                          "source": r["source"], "status": r["status"]}
    return out, {}


def surname(name):
    return name.split()[-1].lower()


def fmt(v):
    return f"{v['role']}/{v['team']}/os={v['os']}"


def compare(label, a, b, a_name, b_name, lines):
    """Exact-name matches in both: field mismatches. Returns mismatch rows."""
    rows = []
    for name in sorted(set(a) & set(b)):
        diffs = []
        if a[name]["role"] != b[name]["role"]:
            diffs.append(f"role {a_name}={a[name]['role']} vs {b_name}={b[name]['role']}")
        if a[name]["team"] != b[name]["team"]:
            diffs.append(f"team {a_name}={a[name]['team']} vs {b_name}={b[name]['team']}")
        if a[name]["os"] != b[name]["os"]:
            diffs.append(f"overseas {a_name}={a[name]['os']} vs {b_name}={b[name]['os']}")
        if diffs:
            rows.append((name, "; ".join(diffs)))
    lines.append(f"### {label}: {len(rows)} exact-name field mismatch(es)")
    for name, d in rows:
        lines.append(f"- `{name}`: {d}")
    if not rows:
        lines.append("- none")
    lines.append("")
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--universe", default=str(ROOT / "data/seed_players_universe.json"))
    ap.add_argument("--sandbox", default=str(ROOT / "api/sandbox.py"))
    ap.add_argument("--db-json")
    ap.add_argument("--db")
    ap.add_argument("--out")
    args = ap.parse_args()
    if not (args.db_json or args.db):
        print("one of --db-json / --db is required", file=sys.stderr)
        return 2

    uni = load_universe(args.universe)
    sbx = load_sandbox(args.sandbox)
    if args.db_json:
        db, refs = load_db_json(args.db_json)
    else:
        db, refs = load_db_sqlite(args.db)

    L = []
    L.append("# P4-D4 three-way drift audit — raw machine output")
    L.append("")
    L.append(f"- universe (A): {len(uni)} players")
    L.append(f"- demo DB (B): {len(db)} players "
             f"({sum(1 for v in db.values() if v.get('status') == 'retired')} status=retired, "
             f"{sum(1 for v in db.values() if v.get('status') != 'retired')} other/active)")
    L.append(f"- sandbox (C): {len(sbx)} players")
    L.append("")
    for label, src in (("A universe", uni), ("B demo DB", db), ("C sandbox", sbx)):
        L.append(f"{label} by team: {dict(sorted(Counter(v['team'] for v in src.values()).items()))}")
        L.append(f"{label} by role: {dict(sorted(Counter(v['role'] for v in src.values()).items()))}")
    L.append("")

    L.append("## Set overlaps (exact name)")
    L.append(f"- A∩B: {len(set(uni) & set(db))} | A∩C: {len(set(uni) & set(sbx))} | "
             f"B∩C: {len(set(db) & set(sbx))} | A∩B∩C: {len(set(uni) & set(db) & set(sbx))}")
    L.append("")

    compare("B demo DB vs A universe", db, uni, "DB", "UNI", L)
    compare("C sandbox vs A universe", sbx, uni, "SBX", "UNI", L)
    compare("B demo DB vs C sandbox", db, sbx, "DB", "SBX", L)

    def only(label, src, others):
        names = sorted(set(src) - set().union(*[set(o) for o in others]))
        L.append(f"### Only in {label}: {len(names)}")
        for n in names:
            v = src[n]
            extra = f" id={v['id']} source={v['source']} status={v['status']}" if "id" in v else ""
            L.append(f"- `{n}` ({fmt(v)}){extra}")
        L.append("")
        return names

    only("A universe (not in DB or sandbox)", uni, [db, sbx])
    only("B demo DB (not in universe or sandbox)", db, [uni, sbx])
    only("C sandbox (not in universe or DB)", sbx, [uni, db])
    L.append("### In universe but missing from demo DB (regardless of sandbox)")
    for n in sorted(set(uni) - set(db)):
        L.append(f"- `{n}` ({fmt(uni[n])})")
    L.append("")
    L.append("### In demo DB but absent from universe (regardless of sandbox)")
    for n in sorted(set(db) - set(uni)):
        v = db[n]
        L.append(f"- `{n}` ({fmt(v)}) id={v['id']} source={v['source']} status={v['status']}")
    L.append("")

    # Probable same-person variants: same surname, different exact name,
    # appearing in different sources (or twice inside the DB).
    L.append("## Probable name variants (same surname, different exact name)")
    by_surname = defaultdict(list)
    for label, src in (("A", uni), ("B", db), ("C", sbx)):
        for n, v in src.items():
            by_surname[surname(n)].append((label, n, fmt(v)))
    seen = set()
    for sn, entries in sorted(by_surname.items()):
        names = {(lab, n) for lab, n, _ in entries}
        exacts = {n for _, n, _ in entries}
        if len(exacts) > 1:
            key = tuple(sorted(exacts))
            if key in seen:
                continue
            seen.add(key)
            rendered = "; ".join(f"{lab}:`{n}` ({f})" for lab, n, f in sorted(entries))
            L.append(f"- surname `{sn}`: {rendered}")
    L.append("")

    # DB-internal suspected duplicates: same surname + same team inside DB.
    L.append("## DB-internal same-surname+team groups (duplicate suspects)")
    groups = defaultdict(list)
    for n, v in db.items():
        groups[(surname(n), v["team"])].append((n, v))
    for (sn, team), entries in sorted(groups.items()):
        if len(entries) > 1:
            rendered = "; ".join(f"`{n}` id={v['id']} {fmt(v)} status={v['status']}"
                                 for n, v in sorted(entries, key=lambda e: e[1]['id']))
            L.append(f"- {sn}/{team}: {rendered}")
    L.append("")
    if refs:
        L.append("## DB reference counts (draft_picks/roster_slots/pre_draft_ranks rows per player id)")
        ref_by_id = defaultdict(dict)
        for table, mapping in refs.items():
            for pid, cnt in mapping.items():
                ref_by_id[int(pid)][table] = cnt
        id2name = {v["id"]: n for n, v in db.items() if "id" in v}
        for pid in sorted(ref_by_id):
            L.append(f"- id={pid} `{id2name.get(pid)}`: {ref_by_id[pid]}")
        L.append("")

    text = "\n".join(L) + "\n"
    if args.out:
        Path(args.out).write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
