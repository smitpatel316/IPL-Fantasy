# IPL Fantasy Pro - Technical Architecture

## Overview
A real-time fantasy cricket platform supporting multiple draft modes (auction, snake, salary cap) with live match scoring.

---

## 1. System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                             │
│    React + TypeScript + Tailwind + Zustand                │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ HTTPS/WSS
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                      API Gateway                             │
│                 (Express + Socket.io)                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
         ┌─────────────┼─────────────┐
         │             │             │
         ▼             ▼             ▼
┌───────────┐  ┌───────────┐  ┌───────────┐
│  Auth     │  │ League    │  │  Draft    │
│  Service   │  │  Service   │  │  Service  │
└───────────┘  └───────────┘  └───────────┘
         │             │             │
         └─────────────┼─────────────┘
                       │
         ┌─────────────┴─────────────┐
         ▼                           ▼
┌──────────────────┐     ┌──────────────────┐
│   PostgreSQL     │     │      Redis       │
│   (Primary DB)   │     │  (Cache/Queue)  │
└──────────────────┘     └──────────────────┘
```

---

## 2. Tech Stack

| Layer | Technology |
|--------|------------|
| Frontend | React 18, TypeScript, TailwindCSS, Zustand |
| Backend | Node.js, Express, Socket.io |
| Database | PostgreSQL (Neon/Supabase) |
| Cache | Redis (Upstash) |
| Real-time | WebSocket (Socket.io) |
| Auth | JWT + Refresh Tokens |
| File Storage | S3/Cloudflare R2 |
| Hosting | Vercel + Railway |

---

## 3. Database Schema

### Users
```sql
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255),
  name VARCHAR(100),
  avatar_url TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

### Leagues
```sql
CREATE TABLE leagues (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(100) NOT NULL,
  commissioner_id UUID REFERENCES users(id),
  type VARCHAR(20) NOT NULL, -- 'auction', 'snake', 'salary_cap', 'dfs'
  status VARCHAR(20) DEFAULT 'drafting', -- 'drafting', 'active', 'completed'
  settings JSONB, -- { budget, squad_size, draft_timer, etc. }
  invite_code VARCHAR(10) UNIQUE,
  is_public BOOLEAN DEFAULT false,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### Teams
```sql
CREATE TABLE teams (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  league_id UUID REFERENCES leagues(id),
  owner_id UUID REFERENCES users(id),
  name VARCHAR(100),
  budget DECIMAL(12,2), -- remaining budget
  total_points DECIMAL(10,2) DEFAULT 0,
  rank INTEGER,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### Players
```sql
CREATE TABLE players (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(100) NOT NULL,
  team_code VARCHAR(10), -- MI, CSK, RCB, etc.
  role VARCHAR(20), -- 'batsman', 'bowler', 'allrounder', 'wicketkeeper'
  base_price DECIMAL(10,2),
  current_price DECIMAL(10,2),
  stats JSONB, -- { avg_points, strike_rate, economy, etc. }
  status VARCHAR(20) DEFAULT 'available' -- 'available', 'sold', 'injured'
);
```

### Draft Picks
```sql
CREATE TABLE draft_picks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  draft_id UUID REFERENCES drafts(id),
  team_id UUID REFERENCES teams(id),
  player_id UUID REFERENCES players(id),
  pick_number INTEGER NOT NULL,
  bid_amount DECIMAL(10,2), -- for auction
  created_at TIMESTAMP DEFAULT NOW()
);
```

### Matches & Points
```sql
CREATE TABLE matches (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  league_id UUID REFERENCES leagues(id),
  team_a_id UUID,
  team_b_id UUID,
  match_date TIMESTAMP NOT NULL,
  status VARCHAR(20) DEFAULT 'scheduled' -- 'scheduled', 'live', 'completed'
);

CREATE TABLE player_points (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  match_id UUID REFERENCES matches(id),
  player_id UUID REFERENCES players(id),
  points DECIMAL(8,2) DEFAULT 0,
  breakdown JSONB -- { runs: 45, wickets: 2, catch: 1, etc. }
);
```

---

## 4. API Endpoints

### Auth
- `POST /api/auth/register` - Create account
- `POST /api/auth/login` - Login
- `POST /api/auth/refresh` - Refresh token
- `GET /api/auth/me` - Current user

### Leagues
- `POST /api/leagues` - Create league
- `GET /api/leagues` - List user's leagues
- `GET /api/leagues/:id` - League details
- `POST /api/leagues/:id/join` - Join league
- `PUT /api/leagues/:id/settings` - Update settings

### Draft
- `POST /api/drafts/:leagueId/start` - Start draft
- `GET /api/drafts/:id` - Draft status
- `POST /api/drafts/:id/bid` - Place bid (auction)
- `POST /api/drafts/:id/pick` - Make pick (snake)
- `PUT /api/drafts/:id/autopick` - Set autopick

### Teams
- `GET /api/teams/:id` - Team details
- `PUT /api/teams/:id/lineup` - Set playing XI
- `PUT /api/teams/:id/captain` - Set captain/vice

### Players
- `GET /api/players` - List players (with filters)
- `GET /api/players/:id` - Player details
- `GET /api/players/:id/stats` - Historical stats

### Matches
- `GET /api/matches` - Upcoming matches
- `GET /api/matches/:id/points` - Live points

---

## 5. WebSocket Events

### Draft Room
```javascript
// Client → Server
'draft:join' - Join draft room
'draft:bid' - Place bid (auction)
'draft:pick' - Make pick (snake)
'draft:pass' - Pass on pick

// Server → Client
'draft:state' - Full draft state
'draft:pick_made' - New pick made
'draft:turn' - Your turn to pick
'draft:timer' - Timer updates
'draft:complete' - Draft finished
```

### Match Center
```javascript
// Server → Client
'match:score_update' - Score changed
'match:wicket' - Wicket fell
'match:over_end' - Over completed
'match:points_update' - Points updated
```

---

## 6. Scoring Engine

### Point Calculation (Live)
```javascript
function calculatePoints(performance) {
  let points = 0;
  
  // Batting
  points += performance.runs * 1;
  points += performance.fours * 2;
  points += performance.sixes * 4;
  if (performance.runs >= 50) points += 20;
  if (performance.runs >= 100) points += 40;
  if (performance.runs === 0) points -= 5;
  
  // Bowling
  points += performance.wickets * 30;
  points += performance.maidens * 10;
  if (performance.wickets >= 4) points += 20;
  
  // Fielding
  points += performance.catches * 10;
  points += performance.stumpings * 15;
  points += performance.runouts * 10;
  
  // Multipliers
  if (performance.isCaptain) points *= 2;
  if (performance.isViceCaptain) points *= 1.5;
  if (performance.isImpactPlayer) points *= 1.5;
  
  return points;
}
```

---

## 7. Draft Logic

### Auction Draft Flow
```javascript
// Server handles
1. Sort players by popularity/price
2. Present player to all teams
3. Accept bids (min increment ₹1 lakh)
4. Timer counts down (60 seconds default)
5. Highest bid wins OR unsold
6. Deduct from team budget
7. Mark player as 'sold'
8. Next player...

// Auto-bid system
if (user.hasAutopick) {
  if (player.isInReservedList) {
    bidUpTo(maxBid);
  } else {
    skip();
  }
}
```

### Snake Draft Flow
```javascript
// Pick order: 1,2,3,4,5,5,4,3,2,1,1,2...
const pickOrder = [];
for (round = 1; round <= totalRounds; round++) {
  if (round % 2 === 1) {
    // Forward
    for (i = 1; i <= teamCount; i++) pickOrder.push(i);
  } else {
    // Reverse
    for (i = teamCount; i >= 1; i--) pickOrder.push(i);
  }
}
```

---

## 8. Frontend State Management

### Stores (Zustand)

```javascript
// User Store
userStore = {
  user: null,
  isAuthenticated: false,
  login: async () => {...},
  logout: () => {...}
}

// League Store
leagueStore = {
  leagues: [],
  currentLeague: null,
  fetchLeagues: async () => {...},
  createLeague: async () => {...}
}

// Draft Store
draftStore = {
  draft: null,
  currentPick: null,
  myTurn: false,
  timeRemaining: 0,
  joinDraft: async () => {...},
  placeBid: async () => {...},
  makePick: async () => {...}
}

// Team Store
teamStore = {
  myTeam: null,
  players: [],
  fetchTeam: async () => {...},
  setCaptain: async () => {...}
}
```

---

## 9. Key Components

### Draft Room Components
```
DraftRoom/
├── DraftBoard.jsx        # Main draft visualization
├── PlayerCard.jsx       # Player being bid/picked
├── TeamBudget.jsx       # Team's remaining budget
├── DraftTimer.jsx       # Countdown timer
├── BidPanel.jsx         # Bid controls
├── DraftChat.jsx        # League chat
├── PlayerQueue.jsx      # Upcoming players
└── DraftHistory.jsx    # Completed picks
```

### Team Components
```
TeamManagement/
├── RosterView.jsx       # Team lineup
├── PlayerCard.jsx       # Player stats
├── CaptainSelector.jsx  # Assign roles
├── PointsBreakdown.jsx  # Points analysis
└── TradePanel.jsx       # Propose trades
```

---

## 10. Security

- JWT access tokens (15 min expiry)
- Refresh tokens (7 days, httpOnly cookie)
- Rate limiting (100 req/min)
- Input validation (Zod)
- SQL injection prevention (parameterized queries)
- XSS prevention (react sanitize)
- CORS configured

---

## 11. Performance

- Database indexes on frequently queried columns
- Redis caching for player data (TTL: 1 hour)
- Pagination on list endpoints (20 items default)
- WebSocket for real-time (not polling)
- Image optimization (Cloudflare Images)
- CDN for static assets (Vercel)

---

## 12. Deployment

```yaml
# docker-compose.yml
services:
  api:
    build: ./backend
    ports:
      - "4000:4000"
    environment:
      - DATABASE_URL=...
      - REDIS_URL=...
    depends_on:
      - postgres
      - redis

  web:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - api

  postgres:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
```

---

*Architecture Version: 1.0*
