# IPL Fantasy Pro - Product Specification

## Project Overview

**Project Name:** IPL Fantasy Pro  
**Type:** Fantasy Sports Web Application (T20 Cricket)  
**Core Functionality:** A comprehensive IPL fantasy cricket platform with multiple game modes including auction drafts (like real IPL teams), snake drafts, and salary cap leagues.  
**Target Users:** IPL fans, cricket enthusiasts, fantasy sports players, friends/colleagues wanting to compete in private leagues

---

## 1. IPL 2026 Context

### Teams (10 Franchises)
1. Mumbai Indians (MI)
2. Chennai Super Kings (CSK)
3. Royal Challengers Bangalore (RCB)
4. Kolkata Knight Riders (KKR)
5. Sunrisers Hyderabad (SRH)
6. Rajasthan Royals (RR)
7. Delhi Capitals (DC)
8. Punjab Kings (PBSK)
9. Lucknow Super Giants (LSG)
10. Gujarat Titans (GT)

### Budget
- Each franchise: ₹125 crore (₹12.5 billion)
- Squad size: 18-25 players
- Overseas limit: 8 players

### Key Players (Sample)
- Jasprit Bumrah, Rohit Sharma, Hardik Pandya (MI)
- MS Dhoni, Ravindra Jadeja, Ruturaj Gaikwad (CSK)
- Virat Kohli, R Ashwin, Rajat Patidar (RCB)
- Shubman Gill, Mohammed Shami (KKR)
- And 500+ more players across all teams

---

## 2. Game Modes

### 2.1 Auction Draft (Primary - IPL Style)
**Description:** Like real IPL auctions, each player is bid on. Teams have a fixed purse and compete to build their squad.

**Mechanics:**
- Each team starts with equal budget (configurable: default ₹50 lakhs per team)
- Players go up for auction one by one
- Teams bid against each other
- Winning bid is deducted from team budget
- Minimum squad: 7 players, Maximum: 25 players
- Must fill roles: Captain, Vice-Captain + 5+ core players
- Can have up to 4 overseas players

**Features:**
- Set player reserves (players you want but won't bid on)
- Set max bid limits per player
- Auto-bid assistant for busy users
- Pause/resume draft
- Trade deadline (mid-season trades)

### 2.2 Snake Draft
**Description:** Traditional fantasy draft where order reverses each round.

**Mechanics:**
- Configurable: 5-15 rounds
- Draft order: 1→2→3→...→N→N→...→3→2→1→1→2...
- No budget - each pick is free
- Auto-pick for absent users
- Draft room with chat
- Keeper options (carry over players from previous season)

### 2.3 Salary Cap / Draft
**Description:** Each player has a price, fixed budget, pick any players within budget.

**Mechanics:**
- Player prices based on real IPL auction values
- Standard budget: ₹50-100 lakhs
- No repeat picks
- Squad size: 11-15 players
- Point cap system (star players limited)

### 2.4 Daily Fantasy (DFS)
**Description:** Pick a new lineup for each match day.

**Mechanics:**
- Smaller squads (3-7 players per match)
- Contest entry fees
- Prize pools
- Multiple contest types (H2H, GPP, 50/50)

---

## 3. Scoring System

### 3.1 Batting Points
| Action | Points |
|--------|--------|
| Every run scored | +1 |
| Boundary (4) bonus | +2 |
| Six bonus | +4 |
| Half-century (50s) | +20 |
| Century (100s) | +40 |
| Duck (0) | -5 |

### 3.2 Bowling Points
| Action | Points |
|--------|--------|
| Wicket | +30 |
| Maiden over | +10 |
| Dot ball bonus | +1 |
| 4+ wickets | +20 bonus |

### 3.3 Fielding Points
| Action | Points |
|--------|--------|
| Catch | +10 |
| Stumping | +15 |
| Run out | +10 |

### 3.4 Multiplier
| Role | Points Multiplier |
|------|------------------|
| Captain | 2x |
| Vice-Captain | 1.5x |
| Impact Player | 1.5x |

### 3.5 Bonus Points
| Action | Points |
|--------|--------|
| Player of the Match | +50 |
| Team Win | +20 |
| 30+ runs | +10 |
| 3+ wickets | +10 |

---

## 4. User Roles & Permissions

### 4.1 League Commissioner
- Create/edit league settings
- Start/kick draft
- Manage league rules
- Resolve disputes
- Invite users

### 4.2 Team Manager
- Manage team roster
- Set lineup for matches
- Participate in draft
- Make trades (if allowed)
- View league stats

### 4.3 Viewer (Optional)
- View-only access to public leagues
- No team management

---

## 5. Core Features

### 5.1 League Management
- Create public/private leagues
- Invite via link/code
- League settings:
  - Game mode (auction/snake/salary cap)
  - Budget amount
  - Squad size
  - Draft date/time
  - Scoring format
  - Trade rules

### 5.2 Player Database
- All IPL 2026 players
- Player stats:
  - Role (Batsman, Bowler, All-rounder, WK)
  - Team
  - Base price
  - Performance history (last 3 seasons)
  - Form guide (recent matches)
  - Injury status
- Player projections/analysis

### 5.3 Draft Room
- Real-time draft board
- Live bidding interface
- Draft timer (30-120 seconds per pick)
- Auto-pick options
- Draft chat
- Player search/filter
- Draft history

### 5.4 Team Management
- Set playing XI
- Assign captain/vice-captain
- Impact player selection
- Substitution management
- Player stats dashboard

### 5.5 Match Center
- Live score updates
- Player performance tracking
- Point accumulation in real-time
- Leaderboard
- Matchups

### 5.6 League Standings
- Points table
- Head-to-head records
- Statistics dashboard
- Award winners (best manager, etc.)

---

## 6. Technical Requirements

### 6.1 Tech Stack
- **Frontend:** React + TypeScript
- **Backend:** Node.js + Express
- **Database:** PostgreSQL (user data, leagues) + Redis (live scores cache)
- **Real-time:** WebSocket for live updates
- **Styling:** Tailwind CSS
- **State:** Zustand/Redux

### 6.2 Data Sources
- CricAPI or similar for live scores
- Player data from official IPL stats
- Historical performance data

### 6.3 Key Entities

```
User {
  id, email, name, avatar
  teams: Team[]
  leagues: League[]
  draftRooms: DraftRoom[]
}

League {
  id, name, commissionerId
  type: 'auction' | 'snake' | 'salary_cap' | 'dfs'
  settings: LeagueSettings
  teams: Team[]
  draft: Draft
  matches: Match[]
  status: 'drafting' | 'active' | 'completed'
}

Team {
  id, leagueId, ownerId
  name, players: Player[]
  captainId, viceCaptainId
  budget, remaining
  totalPoints
}

Player {
  id, name, team, role
  basePrice, currentPrice
  stats: PlayerStats
  availability: 'available' | 'sold' | 'injured'
}

Draft {
  id, leagueId, type
  status: 'pending' | 'active' | 'completed'
  currentPick, pickOrder
  picks: DraftPick[]
  timer
}

DraftPick {
  pickNumber, teamId, playerId
  bidAmount (for auction)
  timestamp
}

Match {
  id, leagueId, date
  teamAId, teamBId
  playerPerformances: Performance[]
}

Performance {
  playerId, matchId
  points, runs, wickets, etc.
}
```

---

## 7. UI/UX Design

### 7.1 Color Palette
- Primary: #1E3A8A (Deep Blue - IPL feel)
- Secondary: #F59E0B (Amber/Gold - Trophy color)
- Accent: #10B981 (Emerald - Success)
- Background: #0F172A (Dark theme)
- Surface: #1E293B
- Text: #F8FAFC

### 7.2 Layout

#### Landing Page
- Hero with IPL fantasy showcase
- Feature highlights
- Create/join league CTAs
- Recent public leagues

#### League Dashboard
- League standings
- Match schedule
- Team rosters
- Draft status

#### Draft Room
- Full-screen draft board
- Player cards with prices
- Team budgets (sidebar)
- Draft timer (prominent)
- Chat panel
- Player search/filter

#### Team Management
- Roster view
- Points breakdown
- Player stats
- Set captain/lineup

#### Match Center
- Live scores
- Point accumulation
- Player cards updating
- Leaderboard

### 7.3 Key Screens
1. Landing/Home
2. Create League
3. League Dashboard
4. Draft Room
5. Team Management
6. Player Database/Search
7. Match Center
8. Standings/Leaderboard
9. User Profile

---

## 8. Advanced Features (V2+)

### 8.1 Social Features
- League chat
- Friend leaderboards
- Trade proposals
- Mock drafts
- Public leagues

### 8.2 Analytics
- Player projections
- Value analysis (points per crore)
- Matchup analysis
- Optimal lineup suggestions

### 8.3 Seasonal Features
- Keeper system
- Mid-season draft
- Trade deadline
- Playoffs/Championship

### 8.4 Fantasy DFS
- Daily contests
- Multiple contest types
- Prize payouts
- Bankroll management

---

## 9. Success Metrics

- **User Acquisition:** 10,000+ users by IPL 2026
- **League Creation:** 1,000+ private leagues
- **Retention:** 60% return users
- **Draft Completion:** 95% of started drafts complete
- **Live Engagement:** 80% users check during matches

---

## 10. Differentiation from Existing Apps

| Feature | Our App | ESPN/Yahoo | Dream11 |
|---------|---------|-------------|---------|
| Auction Draft | ✅ Full | ❌ | Limited |
| Snake Draft | ✅ | ✅ | ❌ |
| Salary Cap | ✅ | ✅ | ✅ |
| Custom Scoring | ✅ | Partial | Limited |
| Private Leagues | ✅ | ✅ | ✅ |
| Real-time Points | ✅ | ✅ | ✅ |
| Player Analysis | ✅ | ✅ | Partial |
| Trade System | ✅ | ✅ | ❌ |
| Social Features | ✅ | ✅ | Partial |

---

## 11. Development Phases

### Phase 1 (MVP)
- League creation
- Player database
- Auction draft
- Basic scoring
- Team management

### Phase 2
- Snake draft mode
- Match center with live scores
- League standings

### Phase 3
- Social features
- Analytics dashboard
- Trade system

### Phase 4 (DFS)
- Daily fantasy contests
- Prize payouts
- Bankroll management

---

## 12. Budget & Resources

### Estimated Development
- **Frontend Dev:** 3-4 weeks
- **Backend Dev:** 4-5 weeks
- **Design/UX:** 2 weeks
- **Testing:** 2 weeks

### Infrastructure
- **Server:** AWS/Vercel
- **Database:** PostgreSQL (Neon/Supabase)
- **Real-time:** Socket.io on Redis
- **CDN:** Cloudflare

---

*Document Version: 1.0*  
*Created: February 20, 2026*  
*Status: Planning Complete*
