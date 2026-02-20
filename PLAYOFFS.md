# IPL Fantasy Pro - Playoffs & Championships

## Season Structure

### Regular Season
- **Duration:** 14 match weeks (parallel to IPL season)
- **Format:** Weekly Head-to-Head
- **Matchups:** Each team plays every other team once
- **Standings:** Win = 1 point, Loss = 0, Tie = 0.5

### Example Schedule (10 Teams)
```
Week 1: 1v10, 2v9, 3v8, 4v7, 5v6
Week 2: 1v9, 10v8, 2v7, 3v6, 4v5
...
Week 9: Bye weeks / Makeup games
```

---

## Playoff Format

### Seeding
- Top 8 teams make playoffs
- Seeded by:
  1. Winning percentage
  2. Head-to-head record
  3. Total points scored
  4. Coin flip

### Bracket Structure
```
Quarterfinals (Best of 3)     Semifinals (Best of 3)     Finals (Best of 3)
─────────────────────────────────────────────────────────────────────────────────────
#1 Seed    vs   #8 Seed           │                        │
                                  │                        ▼
#4 Seed    vs   #5 Seed           │                   CHAMPION
                                  │                        │
──────────────────────────────────┤                        ▼
                                  │                   Runner-up
#3 Seed    vs   #6 Seed           │                        │
                                  │                        ▼
#2 Seed    vs   #7 Seed           │                        │
```

---

## Playoff Rules

### Roster Rules
- Set lineup before each playoff match
- Can't add new players (trade deadline passed)
- IR (Injury Reserve) slots available
- Captain/Vice must play to get multiplier

### Match Scoring
- Same as regular season
- Category wins determine winner
- Tie = split point

### Tiebreakers
1. Total points scored in series
2. Head-to-head from season
3. Higher seed advances

---

## Championship Week

### Third Place Match
- Losers of semifinals play
- Single match

### Grand Finals
- Best of 3 like other rounds
- Championship trophy awarded
- Prize distribution:

```
🏆 CHAMPION
- Trophy + Badge
- League Winner title
- Featured on leaderboard

🥈 RUNNER-UP  
- Finalist badge
- Featured on leaderboard

🥉 THIRD PLACE
- Bronze medal
- Consolation prize
```

---

## Awards Ceremony

### End of Season Awards

| Award | Criteria | Winner |
|-------|-----------|--------|
| 🏆 League Champion | Best playoff record | Team |
| 🌟 Regular Season Winner | Best regular season record | Team |
| 📈 Best Manager | Most wins (H2H) | Manager |
| 💎 Best Value Player | Highest points per cost | Player |
| 🔥 Hot Hand | Best recent form (last 5 matches) | Player |
| ❄️ Cold Hand | Worst recent form | Player |
| 📊 Mr. Consistent | Lowest variance in points | Player |
| 🚀 Breakout Star | Biggest point increase | Player |

---

## UI Screens

### Standings Page
```
═══════════════════════════════════════
  STANDINGS - Week 12
═══════════════════════════════════════

 Pos | Team       | W-L   | Pts  | Streak
────────────────────────────────────────────
  1  | 🔥 Fire    | 15-2  | 15   | W5
  2  | ⚡ Bolt     | 14-3  | 14   | W3
  3  | 🌟 Star    | 12-5  | 12   | W2
  4  | 💥 Boom    | 11-6  | 11   | L1
  5  | 🎯 Aim     | 9-8   | 9    | W1
  6  | 👑 Crown   | 8-9   | 8    | L2
  7  | 🔮 Magic   | 6-11  | 6    | L3
  8  | ⚔️ Knight | 5-12  | 5    | L5
────────────────────────────────────────────
 9  | 🚀 Rocket  | 3-14  | 3    | L7
 10 | 🐢 Turtle  | 2-15  | 2    | L10

────────────────────────────────────────────
🏆 CLINCHED: Fire, Bolt (Playoffs)
🔒 ELIMINATED: Rocket, Turtle
```

### Playoffs Bracket
```
═══════════════════════════════════════
  PLAYOFFS - Semifinals
═══════════════════════════════════════

Quarterfinals          Semifinals          Finals
────────────────────────────────────────────────
🔥 Fire   2-0       │
                      │
🌟 Star   0-1       │ Fire vs Star
                      │ Game 1: Fire 5-4
💥 Boom   2-1       │
                      │ 
⚡ Bolt   2-0       │
                      │ Bolt vs Crown
👑 Crown  2-1       │ Game 1: Crown 5-4
                      │
🎯 Aim   0-2       │
```

### Matchup Detail
```
═══════════════════════════════════════
  WEEK 15: Fire vs Star - Game 1
═══════════════════════════════════════

Categories: Fire leads 5-4

Category          Fire     Star     Lead
───────────────────────────────────────────
Total Points     1,245   1,198    🔥 +47
Boundaries         45       38     🔥 +7
Wickets            12       15     ⭐ +3
Milestones          2        1      🔥 +1
Strike Rate      142      138      🔥 +4
Economy          7.2      7.8      ⭐ +0.6
Catches            8       10      ⭐ +2
Run Rate         8.9      9.1      🔥 +0.2
Duck Outs          2        1      ⭐ +1

───────────────────────────────────────────
GAME 1: 🔥 Fire wins 5-4
Need 2 more wins to advance!
```

---

## Database Schema

```sql
-- Playoff bracket
CREATE TABLE playoffs (
  id UUID PRIMARY KEY,
  league_id UUID,
  year INTEGER,
  format VARCHAR(20), -- 'bracket', 'round_robin'
  status VARCHAR(20)   -- 'pending', 'active', 'completed'
);

-- Bracket rounds
CREATE TABLE playoff_rounds (
  id UUID,
  playoff_id UUID,
  round_number INTEGER, -- 1= quarters, 2= semis, 3= finals
  best_of INTEGER,      -- 1, 3, 5, 7
  status VARCHAR(20)
);

-- Matchups in each round
CREATE TABLE playoff_matchups (
  id UUID,
  round_id UUID,
  home_team_id UUID,
  away_team_id UUID,
  home_wins INTEGER DEFAULT 0,
  away_wins INTEGER DEFAULT 0,
  games_played INTEGER DEFAULT 0,
  winner_id UUID
);

-- Awards
CREATE TABLE season_awards (
  id UUID,
  league_id UUID,
  year INTEGER,
  award_type VARCHAR(50),
  winner_team_id UUID,
  winner_player_id UUID,
  criteria JSONB
);
```

---

*Playoffs & Championships v1.0*
