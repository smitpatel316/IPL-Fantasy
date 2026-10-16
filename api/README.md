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
| `GET /api/leagues` | **live (P4-W7)** | league summaries (id, name, season, status, team_count) for the web league switcher |
| `GET /api/leagues/{id}` | live | league + settings + standings |
| `POST /api/leagues/{id}/join` | live | `{invite_code, team_name, owner_name}` — joining auto-claims the team (P4-W18): the response carries its one-time `claim_code` |
| `PATCH /api/leagues/{id}/settings` | **live (P4-W15)** | commissioner settings edit: `pick_clock_secs`, `trade_deadline_week`, `waiver_run_weekday` (validated, merged into the settings JSON) |
| `POST /api/leagues/{id}/adjustments` | **live (P4-W15)** | manual FAAB adjustment `{team_id, faab_delta, note}` — note mandatory, balance clamped at 0, written to `league_adjustments` |
| `GET /api/leagues/{id}/adjustments` | **live (P4-W15)** | commissioner audit log, newest first (limit 50) |
| `POST /api/teams/{id}/claim` · `POST /api/teams/{id}/reset-claim` | **live (P4-W18)** | claim an unclaimed team (returns its code once; 409 if already claimed) / commissioner reset (clears the code). Once claimed, team-scoped mutations (lineup PUT, waiver claim, trade propose/accept/reject/veto) require the `X-Team-Claim` header; unclaimed teams stay honor-system |
| `POST /api/leagues/{id}/roster-moves` · `GET /api/leagues/{id}/roster-moves` | **live (P4-W25)** | commissioner roster fiat: `{team_id, player_id, action: add\|drop, note}` — add enforces league-wide ownership + the 15-man cap; drop clears saved weekly lineups and refuses while the player is a pending claim's drop piece. Audited in `league_adjustments` (kind roster_add/roster_drop, sharing the P4-W15 table + player_id/player_name columns) |
| `GET /api/leagues/{id}/teams` | live | |
| `GET /api/leagues/{id}/playoffs` | **live (P4-W6)** | bracket projection of the P2-L6 engine: top-4 seeds from regular-season (weeks 1–6) standings, 1v4/2v3 semifinals, final + third-place game, champion; `seeds_final` false until every week-6 game is final; week-7/8 matchup rows are adopted (scores/status/winner, ties to the higher seed) as scoring lands them |
| `GET/POST /api/trade-block?league_id=` · `DELETE /api/trade-block?league_id=&team_id=&player_id=` | **live (P5-W7)** | league-wide "on the block" board: reads open (stale listings pruned on read — a listing lives only while the player is on the listing team's roster); POST is an upsert of `{league_id, team_id, player_id, seeking}` for a player the acting team owns (422 otherwise), claim-aware (P4-W18); DELETE idempotent 204 |
| `GET/POST /api/leagues/{id}/messages` · `DELETE /api/leagues/{id}/messages/{mid}?team_id=` | **live (P5-W5)** | persistent league message board: reads open + paginated (limit/offset, newest first, `total` + `commissioner_team_id` in the response); post is claim-aware (P4-W18); DELETE is commissioner-team-only soft-delete (deleted_at stamped, never hard-deleted) |
| `GET /api/leagues/{id}/schedule-nudges?week_no=` | **live (P3-A6)** | per-IPL-team game counts for a fantasy week; `weeks_available` + `week_start/end` + `source` provenance; powers the draft-room + waiver schedule badges (D10 option 4). Data: `api/schedule_games.py` importer (2026 Cricsheet fixture as dev stand-in; 2027 fixture swaps in ~Feb 2027, no re-architecture) |
| `POST /api/leagues/{id}/draft/start` | **live (P3-A2)** | snake order (seeded shuffle), league → drafting, engine in `engine_state` |
| `GET /api/drafts/{id}` | live | draft state (`on_clock_team_id` from the live engine; `current_pick_no` 1-indexed; `draft_order` is the round-1 team order — even rounds snake) |
| `GET /api/drafts/{id}/picks` | live | pick list |
| `POST /api/drafts/{id}/pick` | **live (P3-A2)** | `{team_id, player_id}`; clock expiry auto-fires on the next pick request; league → in_season when complete |
| `WS /api/drafts/{id}/ws?team_id=` | **live (P3-A3)** | draft room: full `state` snapshot on connect; client `pick`/`dnd_add`/`dnd_remove`/`ping`; server broadcasts `state` (event `pick`/`clock_expired`/`dnd_updated`), `error`, `pong`; 1s clock sweeper auto-picks on expiry; P4-W20 adds room chat: client `chat {text}`, server broadcasts `chat {message}`, history (last 100, in-memory) rides every `state` snapshot as `chat` |
| `POST /api/drafts/{id}/dnd` | **live (P3-A3)** | `{team_id, player_id}` — do-not-draft (live draft only); auto-pick skips, manual picks rejected |
| `DELETE /api/drafts/{id}/dnd` | **live (P3-A3)** | `{team_id, player_id}` — un-block |
| `GET /api/teams/{id}/ranks` · `PUT /api/teams/{id}/ranks` | **live (P4-W17)** | a team's custom pre-draft ranks (ordered player ids; PUT replaces, empty list clears). Read by the draft engine at build/revive; a PUT during a live draft refreshes the running draft's in-memory ranks so auto-pick follows immediately |
| `GET /api/leagues/{id}/draft` | **live (P3-A3)** | league's most recent draft (404 if none) |
| `GET /api/leagues/{id}/draft-recap` | **live (P5-W4)** | post-draft recap + grades: per-team A–F grade (drafted value vs pick-position-expected value, both from consensus pre_draft_ranks), biggest steal/reach per team, league headlines. Deterministic, read-only; until the draft completes returns its status with no teams (UI empty state) |
| `PUT /api/teams/{id}/lineup` | live | `{week_no, slots}` — validates D7 slots + D8 overseas cap + IL eligibility (422 on violation; IL only for players whose curated `player_roles.status` marks them out — retired/injured/out); **D5 lock enforced (P4-W8)**: 422 once the week's first ball is due — lock instant = the week's Monday 19:30 IST stand-in, date from `team_weekly_games` for the league's season else the engine `FANTASY_WEEKS` calendar; real fixture start times replace the stand-in when the 2027 fixture imports |
| `GET /api/teams/{id}/lineup?week_no=` | live | when no lineup is saved for the week, carries the most recent earlier saved lineup forward (response flags `carried_over_from_week`; players no longer rostered are dropped from the prefill; nothing persists until a PUT); response also carries the D5 lock state (`locked`, `lock_at`) and `player_availability` (P5-W6: player_id → active \| out \| retired for every slotted player) |
| `GET /api/players?league_id=&season=&role=&team=&q=` | live | universe + roles + preseason_rank + owned_by_team_id; P4-W19 adds `avg_points` (null until scoring lands) + `ownership_pct` (% of leagues rostered); P5-W6 adds `availability` (active \| out \| retired, derived from the curated `player_roles.status` until the live poller lands) |
| `GET /api/players/{id}?league_id=` | **live (P4-W19)** | player detail: profile + owners across all leagues + match-by-match log from `player_match_stats` (empty until scoring lands); carries `availability` like the list (P5-W6) |
| `POST /api/waivers/claim` | **live (P3-A2)** | `{league_id, team_id, add_player_id, drop_player_id?, bid}` — blind FAAB, budget enforced |
| `GET /api/waivers/pending?league_id=&week_no=&team_id=` | live | pending claims for the week; blind (D6): pass team_id for that team's own claims with amounts — without it, amounts are sealed (bid=null) |
| `GET /api/waivers/history?league_id=&week_no=` | **live (P4-W14)** | resolved claims (status != pending) for a league+week; bids are public record once the run resolves them |
| `POST /api/waivers/run?league_id=&week_no=` | **live (P3-A2)** | blind-bid run; winners swap into the drop's roster/week-1 slot; FAAB deducted. **Trigger (P4-W16)**: `api/waiver_scheduler.py` sweeps hourly and runs every in-season league-week whose configured run weekday (default Wed) 03:00 PT has passed and which still has pending claims; the waivers page also has a commissioner "Run waivers now" button. Ops alternative: cron this POST per league/week |
| `GET /api/leagues/{id}/cant-cut` · `PUT /api/leagues/{id}/cant-cut` | **live (P4-W22)** | the effective can't-cut list: commissioner `cant_cut_player_ids` when set ([] = off), else top-N preseason ranks (`cant_cut_top_n`, default 12). PUT writes either field; `player_ids: null` clears back to the default |
| `POST /api/trades` | **live (P3-A2)** | `{league_id, from_team_id, to_team_id, gives[], receives[]}` — balanced N-for-N enforced |
| `GET /api/trades?league_id=&status=` | live | filter by proposed/accepted/rejected/vetoed/expired; each trade carries `veto_count` + `proposed_at`/`accepted_at`/`vetoed_at`/`executed_at` (ISO UTC, null until the event happens) |
| `POST /api/trades/{id}/accept|reject|veto` | **live (P3-A2)** | accept → review window → auto-execute (paired week-1 slot swap); veto by other teams |
| `GET /api/trades/analyze?league_id=&from_team_id=&to_team_id=&gives=&receives=` | **live (P5-W1)** | read-only trade impact projection: per-side rank-implied delta (league pre_draft_ranks ADP proxy — NOT a points projection), net games each side's swapped players play over the next 3 fantasy weeks (P3-A6 game-count table), one-line "who wins" summary. Pure read — no engine, no writes |
| `GET /api/matchups?league_id=&week_no=` | **live (P3-A2)** | schedule generated at draft completion (weeks 1–6; byes for odd team counts) |
| `GET /api/matchups/scoreboard/{match_id}` | live | per-player points + breakdowns (empty until Phase 3 poller) |
| `POST /api/admin/score-match` | stub **P3-data** | `{match_id}` — idempotent trigger; scorer is `phase1/scorer.py` |
| `POST /api/mock-draft/{league_id}` | **live (P5-L1)** | ephemeral practice draft — `{"bots": [{"name, difficulty: casual\|sharp}], "seed"}` (both optional: defaults = 8 bots alternating sharp/casual, seed 42). Reads the league's players/roles/consensus ranks + weeks-1–3 schedule data, runs the draft in memory via `api/engine/mock_draft.py` (bots draft through `Draft.auto_pick`, so every pick is D8-guardrailed), and returns the full pick log + per-team rosters + avg consensus rank per bot. **Zero DB writes** — the live league is untouched. Bot ladder is locked at two levels (Atlas product call); `schedule_weighted` reports whether fixture data existed |

## Pure helpers (importable, no DB)
- `api/validation.py::validate_lineup(lineup, roles)` → raises `LineupError`; used by PUT lineup and P2-L2.
- `api/constants.py` — `ROSTER_SLOTS`, `SLOT_ELIGIBILITY`, `OVERSEAS_STARTER_CAP=4`, `FAAB_BUDGET=100`, `DRAFT_ROUNDS=14`, weeks, `SCORING_TABLE_VERSION`.

## Integrity rules (blueprint §5)
- One player → one team per league (exclusive ownership; `owned_map` in routers).
- Lineup: slot eligibility per `SLOT_ELIGIBILITY`; max 4 overseas starters (D8).
- **D7 resolved (chair ruling 2026-09-15)**: `ROSTER_SLOTS` = 11 starters (WK×1, BAT×3, AR×2, BOWL×3, UTIL×2), BN×3, IL×1 = 15 total. IL is not draft-filled (opens for injured players, Yahoo-style).

## Sandbox
`SANDBOX_MODE=true` (default) seeds one demo league (8 teams, 48 mock players across 4 mock franchises, week-1 matchups) on first boot. Deterministic. Real season data (Phase 3) replaces the seed; never mix.
