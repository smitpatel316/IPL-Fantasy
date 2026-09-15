# IPL Fantasy — API contract (v1 scaffold, P2-W1)
Blueprint §7 surface. League-core builds the engines behind the 501 stubs;
**do not rename fields** — renames are breaking changes, discuss first.

Base URL: `{BACKEND}/api` · interactive docs: `{BACKEND}/api/docs`

## Status legend
- **live** — sqlite-backed, works now (sandbox seed on first boot)
- **stub/501** — contract final, engine owned by the tagged track; body is `{detail, track}`

## Endpoints
| Method & path | Status | Notes |
|---|---|---|
| `GET /api/health` | live | `{status, version, sandbox, scoring_table}` |
| `POST /api/leagues` | live | `{name, commissioner_name}` → league + invite_code |
| `GET /api/leagues/{id}` | live | league + settings + standings |
| `POST /api/leagues/{id}/join` | live | `{invite_code, team_name, owner_name}` |
| `GET /api/leagues/{id}/teams` | live | |
| `POST /api/leagues/{id}/draft/start` | stub **P2-L1** | creates draft (snake order), league → drafting |
| `GET /api/drafts/{id}` | live | draft state |
| `GET /api/drafts/{id}/picks` | live | pick list |
| `POST /api/drafts/{id}/pick` | stub **P2-L1** | `{team_id, player_id}`; auto-pick on clock expiry |
| `PUT /api/teams/{id}/lineup` | live | `{week_no, slots}` — validates D7 slots + D8 overseas cap (422 on violation); **P2-L2 seam**: weekly-lock deadline check goes here (marked in code) |
| `GET /api/teams/{id}/lineup?week_no=` | live | |
| `GET /api/players?league_id=&season=&role=&team=&q=` | live | universe + roles + preseason_rank + owned_by_team_id |
| `POST /api/waivers/claim` | stub **P2-L3** | `{league_id, team_id, add_player_id, drop_player_id?, bid}` |
| `GET /api/waivers/pending?league_id=&week_no=` | live | (empty until P2-L3) |
| `POST /api/waivers/run?league_id=&week_no=` | stub **P2-L3** | Wednesday blind-bid run |
| `POST /api/trades` | stub **P2-L4** | `{league_id, from_team_id, to_team_id, gives[], receives[]}` |
| `GET /api/trades?league_id=&status=` | live | (empty until P2-L4) |
| `POST /api/trades/{id}/accept|reject|veto` | stub **P2-L4** | |
| `GET /api/matchups?league_id=&week_no=` | live | |
| `GET /api/matchups/scoreboard/{match_id}` | live | per-player points + breakdowns (empty until Phase 3 poller) |
| `POST /api/admin/score-match` | stub **P3-data** | `{match_id}` — idempotent trigger; scorer is `phase1/scorer.py` |

## Pure helpers (importable, no DB)
- `api/validation.py::validate_lineup(lineup, roles)` → raises `LineupError`; used by PUT lineup and P2-L2.
- `api/constants.py` — `ROSTER_SLOTS`, `SLOT_ELIGIBILITY`, `OVERSEAS_STARTER_CAP=4`, `FAAB_BUDGET=100`, `DRAFT_ROUNDS=15`, weeks, `SCORING_TABLE_VERSION`.

## Integrity rules (blueprint §5)
- One player → one team per league (exclusive ownership; `owned_map` in routers).
- Lineup: slot eligibility per `SLOT_ELIGIBILITY`; max 4 overseas starters (D8).
- **D7 arithmetic open question**: `ROSTER_SLOTS` totals 10 starters; DECISIONS.md prose says 11. Do not invent the 11th — chair decision pending.

## Sandbox
`SANDBOX_MODE=true` (default) seeds one demo league (8 teams, 48 mock players across 4 mock franchises, week-1 matchups) on first boot. Deterministic. Real season data (Phase 3) replaces the seed; never mix.
