-- IPL Fantasy core schema (blueprint §5, sqlite dialect).
-- Dev database; Postgres migration is a later decision (Phase 4 / Pi deploy).
-- Season-scoped: players and roles are per-season (role registry is owned/curated).

PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    email       TEXT UNIQUE,
    avatar_url  TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS leagues (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    invite_code     TEXT NOT NULL UNIQUE,
    commissioner_id INTEGER REFERENCES users(id),
    season          TEXT NOT NULL DEFAULT '2027',
    settings        TEXT NOT NULL DEFAULT '{}',   -- JSON: draft_type, rounds, roster_slots, faab_budget, scoring_table_version, overseas_cap, playoff_teams, trade_deadline_week
    status          TEXT NOT NULL DEFAULT 'setup', -- setup | drafting | in_season | playoffs | complete
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS teams (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    league_id       INTEGER NOT NULL REFERENCES leagues(id) ON DELETE CASCADE,
    owner_id        INTEGER REFERENCES users(id),
    name            TEXT NOT NULL,
    faab_remaining  INTEGER NOT NULL DEFAULT 100,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (league_id, name)
);

-- Draft universe, season-scoped.
CREATE TABLE IF NOT EXISTS players (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT NOT NULL,
    season  TEXT NOT NULL DEFAULT '2027',
    UNIQUE (name, season)
);

-- Owned/curated role registry (data team curates; web reads).
-- role ∈ {WK,BAT,AR,BOWL}
CREATE TABLE IF NOT EXISTS player_roles (
    player_id    INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    season       TEXT NOT NULL,
    role         TEXT NOT NULL CHECK (role IN ('WK','BAT','AR','BOWL')),
    is_overseas  INTEGER NOT NULL DEFAULT 0,
    ipl_team_code TEXT,
    source       TEXT,
    PRIMARY KEY (player_id, season)
);

CREATE TABLE IF NOT EXISTS drafts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    league_id       INTEGER NOT NULL REFERENCES leagues(id) ON DELETE CASCADE,
    draft_order     TEXT NOT NULL DEFAULT '[]',  -- JSON: [team_id...] snake base order
    rounds          INTEGER NOT NULL DEFAULT 15,
    status          TEXT NOT NULL DEFAULT 'scheduled', -- scheduled | live | complete
    current_pick_no INTEGER NOT NULL DEFAULT 0,
    pick_deadline   TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS draft_picks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    draft_id    INTEGER NOT NULL REFERENCES drafts(id) ON DELETE CASCADE,
    pick_no     INTEGER NOT NULL,
    round_no    INTEGER NOT NULL,
    team_id     INTEGER NOT NULL REFERENCES teams(id),
    player_id   INTEGER REFERENCES players(id),
    is_auto     INTEGER NOT NULL DEFAULT 0,
    picked_at   TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (draft_id, pick_no)
);

-- Per-team custom ranks; fallback = league preseason rank ("ADP" proxy, R1).
CREATE TABLE IF NOT EXISTS pre_draft_ranks (
    team_id     INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    player_id   INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    rank        INTEGER NOT NULL,
    PRIMARY KEY (team_id, player_id)
);

-- slot ∈ {WK,BAT,AR,BOWL,UTIL,BN,IL}; one row per rostered player.
-- Weekly lineups are snapshots: week_no NULL = current roster construction.
CREATE TABLE IF NOT EXISTS roster_slots (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id     INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    player_id   INTEGER NOT NULL REFERENCES players(id),
    slot        TEXT NOT NULL CHECK (slot IN ('WK','BAT','AR','BOWL','UTIL','BN','IL')),
    week_no     INTEGER,  -- NULL = draft/construction state; else the fantasy week this lineup is locked for
    UNIQUE (team_id, player_id, week_no)
);
CREATE INDEX IF NOT EXISTS idx_roster_team_week ON roster_slots(team_id, week_no);

-- Real IPL fixtures mapped onto fantasy weeks (data team / Phase 3 poller writes).
-- status ∈ {scheduled,live,completed,abandoned}
CREATE TABLE IF NOT EXISTS matches (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id     TEXT UNIQUE,
    season          TEXT NOT NULL,
    week_no         INTEGER,
    match_date_ist  TEXT,
    venue           TEXT,
    home_code       TEXT,
    away_code       TEXT,
    status          TEXT NOT NULL DEFAULT 'scheduled'
);

CREATE TABLE IF NOT EXISTS player_match_stats (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id        INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    player_id       INTEGER REFERENCES players(id),
    player_name     TEXT NOT NULL,          -- denormalized: scorecards arrive by name
    fantasy_points  INTEGER NOT NULL DEFAULT 0,
    breakdown       TEXT NOT NULL DEFAULT '{}',  -- JSON per-component points
    scored_at       TEXT,
    UNIQUE (match_id, player_name)
);

-- status ∈ {pending,won,lost}
CREATE TABLE IF NOT EXISTS waiver_claims (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    league_id       INTEGER NOT NULL REFERENCES leagues(id) ON DELETE CASCADE,
    week_no         INTEGER NOT NULL,
    team_id         INTEGER NOT NULL REFERENCES teams(id),
    add_player_id   INTEGER NOT NULL REFERENCES players(id),
    drop_player_id  INTEGER REFERENCES players(id),
    bid             INTEGER NOT NULL DEFAULT 0,
    status          TEXT NOT NULL DEFAULT 'pending',
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- status ∈ {proposed,accepted,rejected,vetoed,expired}
CREATE TABLE IF NOT EXISTS trades (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    league_id       INTEGER NOT NULL REFERENCES leagues(id) ON DELETE CASCADE,
    from_team_id    INTEGER NOT NULL REFERENCES teams(id),
    to_team_id      INTEGER NOT NULL REFERENCES teams(id),
    gives           TEXT NOT NULL DEFAULT '[]',   -- JSON [player_id...]
    receives        TEXT NOT NULL DEFAULT '[]',  -- JSON [player_id...]
    status          TEXT NOT NULL DEFAULT 'proposed',
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    review_deadline TEXT,
    engine_id       INTEGER  -- api.engine.trade_engine trade id (Phase 3)
);

-- Phase 3: persisted engine snapshots (api/services.py).
-- scope ∈ {draft, waiver, trade}; scope_id = drafts.id / leagues.id.
CREATE TABLE IF NOT EXISTS engine_state (
    scope      TEXT NOT NULL,
    scope_id   INTEGER NOT NULL,
    state      TEXT NOT NULL,   -- engine to_dict() JSON
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (scope, scope_id)
);

-- status ∈ {scheduled,live,final}
CREATE TABLE IF NOT EXISTS matchups (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    league_id   INTEGER NOT NULL REFERENCES leagues(id) ON DELETE CASCADE,
    week_no     INTEGER NOT NULL,
    team_a_id   INTEGER NOT NULL REFERENCES teams(id),
    team_b_id   INTEGER NOT NULL REFERENCES teams(id),
    score_a     REAL NOT NULL DEFAULT 0,
    score_b     REAL NOT NULL DEFAULT 0,
    status      TEXT NOT NULL DEFAULT 'scheduled',
    UNIQUE (league_id, week_no, team_a_id, team_b_id)
);

-- P3-A6 (D10 option 4): per-fantasy-week IPL team game counts for the
-- schedule-aware UI nudges (draft-room + waiver badges). Keyed by league
-- season; written idempotently by api/schedule_games.py. week_start/week_end
-- record the exact calendar the counts were built against (fixed 2027 league
-- calendar or Mon–Sun weeks derived from the fixture), so badge counts always
-- equal the fixture math. source = fixture provenance for the 2027 swap audit.
CREATE TABLE IF NOT EXISTS team_weekly_games (
    season        TEXT NOT NULL,   -- league season, e.g. '2027'
    week_no       INTEGER NOT NULL,
    week_start    TEXT NOT NULL,   -- ISO date, Monday
    week_end      TEXT NOT NULL,   -- ISO date, Sunday
    ipl_team_code TEXT NOT NULL,   -- e.g. 'MI'
    games         INTEGER NOT NULL CHECK (games >= 0),
    source        TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (season, week_no, ipl_team_code)
);
