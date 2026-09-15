# IPL Fantasy 🏏

Season-long IPL fantasy for friends — Yahoo-style: **snake draft, weekly head-to-head,
FAAB waivers, trades, playoffs**. We are the league server; there is no Yahoo for IPL.

> **Stack (D1, locked 2026-09-15):** Next.js + FastAPI, Pi-hosted.
> The February 2026 Express/React scaffold was replaced in P2-W1; its docs are kept
> under the repo root as design input (see "Feb docs" below).

## Product (D1–D11, locked)
- Snake draft, 15 rounds · Dream11-official T20 scoring, no C/VC multipliers
- Weekly H2H, Mon–Sun · weekly lineup lock (no 7am alarms)
- Weekly blind FAAB ($100/season) · 15-man rosters (WK×1/BAT×3/AR×2/BOWL×3/UTIL×1/BN×4/IL×1)
- Max 4 overseas starters · top-4 playoffs, fantasy weeks 7–8
- End-of-match batch scoring (live scoring later)

## Project structure
```
api/                 FastAPI backend (blueprint §7 surface; see api/README.md)
  routers/           leagues, drafts, players, lineups, waivers, trades, matchups, admin
  validation.py      pure D7/D8 lineup validation (no DB)
  sandbox.py         deterministic mock league for dev (SANDBOX_MODE)
web/                 Next.js 15 frontend (blueprint §8 pages)
  app/               /, league/[id], draft-room/[id], lineup, players,
                     waivers, trades, matchup, playoffs
  lib/api.ts         typed API client (mirrors api/schemas.py)
*.md                 Feb 2026 design docs — kept as input, not spec
```

## Dev quickstart
```bash
cp .env.example .env
./start-dev.sh --install   # api :8014, web :3014
./start-dev.sh             # afterwards
```
- API docs: http://127.0.0.1:8014/api/docs
- Web: http://127.0.0.1:3014
- Sandbox mode seeds a demo league (ID 1) on first boot — explore freely.
- **Ports 8000/3000 are never used here** (NBA production). Dev = 8014/3014.

## API contract
Full endpoint table: [api/README.md](api/README.md). Engine endpoints
(draft pick, waiver run, trades, scoring) return `501 {detail, track}` until the
league-core track wires them — the contract is final, the track tag says who owns it.

## Feb docs (design input, not spec)
Per the blueprint's reconciliation (§11): `AUCTION-DRAFT-LOGIC.md` /
`AUCTION-STRATEGY.md` (auction = second draft mode, deferred), `UI-DESIGN.md`
(dark theme + palette — applied to `web/`), `WEEKLY-H2H.md`, `TRADES.md`,
`PLAYOFFS.md` (validate against the Yahoo mechanics reference).
Superseded: `ARCHITECTURE.md` (Express/Postgres/Redis), `SCORING-SYSTEM.md`
(custom table → Dream11-official), `FEATURE-BACKLOG.md` (→ phased plan).

## Constitution
`~/workspace/ipl-fantasy/DECISIONS.md` (D1–D11) · `~/workspace/ipl-fantasy/IMPLEMENTATION-BLUEPRINT.md` (build spec).
No PR, merge, or deploy without Smit's explicit word.

## Author
Smit Patel · MIT
