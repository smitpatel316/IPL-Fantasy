# IPL Fantasy Pro - MVP Specification

## Phase 1: MVP (Minimum Viable Product)

**Goal:** League creation + Auction Draft + Basic match scoring

---

## Core Features (MVP)

### 1. User Authentication
- Email/password sign up & login
- Profile management
- Session handling

### 2
- Create league. League Management (name, settings)
- Invite friends (share code)
- Join league with code
- League dashboard (view all teams)
- Commissioner controls

### 3. Auction Draft Room
- Player list with prices (200+ players)
- Real-time bidding UI
- Budget tracking per team
- Auto-bid option
- Draft timer
- Player card display

### 4. Team Management
- View squad (15 players)
- Set playing XI
- Select Captain (2x points)
- Select Vice-Captain (1.5x points)
- Substitute players

### 5. Match Scoring
- Live match center
- Real-time point updates
- Category breakdown (runs, wickets, catches, etc.)
- Matchup view (you vs opponent)

### 6. Standings
- Weekly W-L-T record
- Total points
- Category wins/losses

---

## Technical Stack

- **Frontend:** SwiftUI (iOS)
- **Backend:** Node.js + PostgreSQL
- **Real-time:** WebSocket
- **Auth:** JWT

---

## UI Screens MVP

1. **Login/Register** - Simple form
2. **Dashboard** - Your leagues, active matches
3. **League List** - All leagues, create new
4. **League Detail** - Teams, standings, settings
5. **Draft Room** - Auction interface
6. **My Team** - Squad management
7. **Set Lineup** - Select XI, captain, vice
8. **Match Center** - Live scoring
9. **Standings** - Weekly rankings

---

## Database Schema (Core Tables)

```sql
users
leagues
league_members
teams
players
auction_drafts
auction_bids
matchups
weekly_scores
player_points
```

---

## Acceptance Criteria

- [ ] User can sign up/login
- [ ] User can create league and invite friends
- [ ] User can join league with code
- [ ] Auction draft works (bid, win, budget updates)
- [ ] User can set captain/vice-captain
- [ ] Scores update in real-time
- [ ] Standings calculate correctly

---

*MVP v1.0 - Start Development*
