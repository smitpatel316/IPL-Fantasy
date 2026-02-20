# IPL Fantasy Pro - Backend API

## Prerequisites
- Node.js 18+
- PostgreSQL 14+
- npm or yarn

## Setup

1. Install dependencies:
```bash
cd backend
npm install
```

2. Configure database:
```bash
cp .env.example .env
# Edit .env with your database credentials
```

3. Initialize database:
```bash
npm run db:init
```

4. Start server:
```bash
npm run dev  # Development
npm start    # Production
```

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login
- `GET /api/auth/me` - Get current user
- `PUT /api/auth/profile` - Update profile

### Leagues
- `GET /api/leagues` - Get user's leagues
- `POST /api/leagues` - Create league
- `POST /api/leagues/join` - Join league with code
- `GET /api/leagues/:id` - Get league details
- `PUT /api/leagues/:id/status` - Update league status

### Players
- `GET /api/players` - Get all players (with filters)
- `GET /api/players/:id` - Get player details
- `GET /api/players/:id/stats` - Get player stats
- `GET /api/players/meta/teams` - Get all teams
- `GET /api/players/meta/roles` - Get all roles

### Drafts (Auction)
- `GET /api/drafts/league/:leagueId` - Get draft for league
- `POST /api/drafts/league/:leagueId/start` - Start auction
- `POST /api/drafts/:draftId/bid` - Place bid
- `POST /api/drafts/:draftId/sell` - Mark player sold
- `POST /api/drafts/:draftId/unsold` - Mark player unsold

### Teams
- `GET /api/teams/league/:leagueId` - Get user's team
- `PUT /api/teams/:teamId/captain` - Set captain/vice
- `PUT /api/teams/:teamId/lineup` - Set playing XI
- `GET /api/teams/league/:leagueId/all` - Get all teams

### Matches
- `GET /api/matches/league/:leagueId/standings` - Get standings
- `GET /api/matches/league/:leagueId/current` - Get current matchup
- `GET /api/matches/league/:leagueId/points` - Get team points

## WebSocket Events

Connect to `/` namespace with JWT token.

### Draft Events
- `draft:started` - Draft has started
- `draft:bid` - New bid placed
- `draft:sold` - Player sold
- `draft:unsold` - Player marked unsold
- `draft:timer` - Timer countdown

### Join League Room
```javascript
socket.emit('join:league', { leagueId: 'uuid' });
```

## Database Schema

- `users` - User accounts
- `leagues` - League definitions
- `league_members` - League participants
- `players` - IPL player database
- `teams` - User's fantasy teams
- `team_players` - Players in each team
- `auction_drafts` - Draft state
- `auction_bids` - Bid history
- `matchups` - Weekly matchups
- `weekly_scores` - Weekly scores
- `player_points` - Real-time scoring
