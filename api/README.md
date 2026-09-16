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
| `POST /api/leagues/{id}/draft/start` | **live (P3-A2)** | snake order (seeded shuffle), league → drafting, engine in `engine_state` |
| `GET /api/drafts/{id}` | live | draft state (`on_clock_team_id` from the live engine; `current_pick_no` 1-indexed; `draft_order` is the round-1 team order — even rounds snake) |
| `GET /api/drafts/{id}/picks` | live | pick list |
| `POST /api/drafts/{id}/pick` | **live (P3-A2)** | `{team_id, player_id}`; clock expiry auto-fires on the next pick request; league → in_season when complete |
| `PUT /api/teams/{id}/lineup` | live | `{week_no, slots}` — validates D7 slots + D8 overseas cap (422 on violation); **P2-L2 seam**: weekly-lock deadline check goes here (marked in code) |
| `GET /api/teams/{id}/lineup?week_no=` | live | |
| `GET /api/players?league_id=&season=&role=&team=&q=` | live | universe + roles + preseason_rank + owned_by_team_id |
| `POST /api/waivers/claim` | **live (P3-A2)** | `{league_id, team_id, add_player_id, drop_player_id?, bid}` — blind FAAB, budget enforced |
| `GET /api/waivers/pending?league_id=&week_no=` | live | pending claims for the week |
| `POST /api/waivers/run?league_id=&week_no=` | **live (P3-A2)** | blind-bid run; winners swap into the drop's roster/week-1 slot; FAAB deducted |
| `POST /api/trades` | **live (P3-A2)** | `{league_id, from_team_id, to_team_id, gives[], receives[]}` — balanced N-for-N enforced |
| `GET /api/trades?league_id=&status=` | live | filter by proposed/accepted/rejected/vetoed/expired |
| `POST /api/trades/{id}/accept|reject|veto` | **live (P3-A2)** | accept → review window → auto-execute (paired week-1 slot swap); veto by other teams |
| `GET /api/matchups?league_id=&week_no=` | **live (P3-A2)** | schedule generated at draft completion (weeks 1–6; byes for odd team counts) |
| `GET /api/matchups/scoreboard/{match_id}` | live | per-player points + breakdowns (empty until Phase 3 poller) |
| `POST /api/admin/score-match` | stub **P3-data** | `{match_id}` — idempotent trigger; scorer is `phase1/scorer.py` |

## Pure helpers (importable, no DB)
- `api/validation.py::validate_lineup(lineup, roles)` → raises `LineupError`; used by PUT lineup and P2-L2.
- `api/constants.py` — `ROSTER_SLOTS`, `SLOT_ELIGIBILITY`, `OVERSEAS_STARTER_CAP=4`, `FAAB_BUDGET=100`, `DRAFT_ROUNDS=14`, weeks, `SCORING_TABLE_VERSION`.

## Integrity rules (blueprint §5)
- One player → one team per league (exclusive ownership; `owned_map` in routers).
- Lineup: slot eligibility per `SLOT_ELIGIBILITY`; max 4 overseas starters (D8).
- **D7 resolved (chair ruling 2026-09-15)**: `ROSTER_SLOTS` = 11 starters (WK×1, BAT×3, AR×2, BOWL×3, UTIL×2), BN×3, IL×1 = 15 total. IL is not draft-filled (opens for injured players, Yahoo-style).

## Sandbox
`SANDBOX_MODE=true` (default) seeds one demo league (8 teams, 48 mock players across 4 mock franchises, week-1 matchups) on first boot. Deterministic. Real season data (Phase 3) replaces the seed; never mix.
