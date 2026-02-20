# Weekly Head-to-Head & League Formats

## NBA Fantasy Weekly H2H Format

### How It Works

Each week, you're matched against another team in your league:

```
Week 1: Team A vs Team B
Week 2: Team A vs Team C  
Week 3: Team A vs Team D
...and so on
```

**You earn a "win" by winning more categories than your opponent.**

---

### Categories (NBA Example)

| Category | Description |
|---------|-------------|
| Points | Total points scored |
| Rebounds | Total rebounds |
| Assists | Total assists |
| Steals | Total steals |
| Blocks | Total blocks |
| Three Pointers | Made 3-pointers |
| Field Goal % | FG% |
| Free Throw % | FT% |
| Turnovers | Fewer is better |
| Total 9CAT | Best of 9 categories |

**Most leagues use "9CAT" (9 categories) or "8CAT" (without Turnovers as it's negative).**

---

### Winning a Week

```
Team A vs Team B - Week 5

Category      Team A    Team B    Winner
─────────────────────────────────────────
Points       985       912       ✅ Team A
Rebounds     420        385       ✅ Team A
Assists      245        268       ✅ Team B
Steals        78         82        ✅ Team B
Blocks       45         38         ✅ Team A
3PM           85        92         ✅ Team B
FG%          .480       .465       ✅ Team A
FT%          .780       .795       ✅ Team B
Turnovers    125        118        ✅ Team B (fewer is better)

Result: Team A wins 5-4 ✅
```

**Tie-breaker:** Usually total points or category that counts for more.

---

### Playoff Format

```
Regular Season: 17-22 weeks (play every team once)

Top 4 teams: Get bye in first round
Top 8 teams: Make playoffs

Playoffs:
- Quarterfinals (Best of 3)
- Semifinals (Best of 3)  
- Finals (Best of 3)
- Champion!
```

---

## Applying to IPL Fantasy

### Weekly H2H for IPL

We can adapt this for cricket!

| Cricket Category | Points Equivalent |
|-----------------|------------------|
| Runs | Batting points |
| Wickets | Bowling points |
| catches | Fielding points |
| Strike Rate | Runs per balls faced |
| Economy | Runs conceded per over |
| 50s/100s | Milestone bonuses |
| 4s/6s | Boundary bonuses |

**Weekly Matchup Example:**
```
Matchup: Team Fire vs Team Bolt - Week 1

Category          Team Fire    Team Bolt    Winner
─────────────────────────────────────────────────
Total Points       1,245       1,198       ✅ Fire
Boundaries        45          38          ✅ Fire
Wickets           12          15          ✅ Bolt
Milestones        2           1           ✅ Fire
Strike Rate       142         138         ✅ Fire

Result: Team Fire wins 4-1 ✅
```

---

## Our League Formats

### 1. Auction Draft + Weekly H2H (Recommended)
- Build team via auction
- Weekly H2H matchups during season
- Head-to-head wins determine standings
- Playoffs for champion

### 2. Snake Draft + Weekly H2H
- Traditional snake draft
- Same weekly format

### 3. Salary Cap + H2H
- Pick players within budget
- Weekly matchups

### 4. Daily Fantasy (DFS)
- Pick new team each match day
- Compete in contests

---

## Standings Calculation

### Regular Season

| Result | Points |
|--------|--------|
| Win | 1 point |
| Loss | 0 points |
| Tie | 0.5 points |

**Standings Example:**
```
Team           W-L-T    Points
────────────────────────────────
1. Fire       15-2-0    15
2. Bolt       14-3-0    14
3. Star       12-5-0    12
4. Boom       11-6-0    11
5. Aim        9-8-0      9
```

---

## Playoff Seeding

### Seeding Logic
1. Overall winning percentage
2. Head-to-head record
3. Total points scored (tiebreaker)
4. Random coin flip (last resort)

### Playoff Bracket
```
Top 8 make playoffs:

Quarterfinals          Semifinals          Finals
─────────────────────────────────────────────────────
#1 Fire   vs  #8 Boom     │                 │
                         │                 ▼
#4 Star  vs  #5 Aim      │              Winner
                         │                 │
─────────────────────────────────────────────────────
                         ▼                 │
#3 Bolt  vs  #6 Crown    │                 │
                         │                 ▼
#2 Delta vs  #7 Echo     │              Runner-up
```

---

## Additional Features

### Trades
- Propose player swaps
- Both teams must approve
- Commissioner can veto
- Trade deadline (mid-season)

### Waiver Wire
- Claim unowned players
- Priority based on standings
- Weekly FAAB (Free Agent Acquisition Budget) bids

### Injured Players
- IR (Injured Reserve) slot
- Replace without using roster spot

---

## Matchup UI Design

```
═══════════════════════════════════════════
  WEEK 5: Fire vs Bolt
═══════════════════════════════════════════

┌─────────────────────────────────────────┐
│  MY TEAM (Fire)         vs  Bolt     │
│  1,245 pts ✓           1,198 pts    │
└─────────────────────────────────────────┘

CATEGORY BREAKDOWN:
──────────────────────────────────────────
Points         985    vs    912     ✅
Rebounds       420    vs    385     ✅
Assists       245    vs    268     ❌
Steals         78    vs    82      ❌
Blocks         45    vs    38      ✅
3PM            85    vs    92      ❌
FG%           .480   vs   .465     ✅
FT%           .780   vs   .795     ❌
Turnovers     125    vs    118     ❌

STATUS: LEADING 5-4

──────────────────────────────────────────
MY PLAYERS (Today):
• Rohit: 45 pts ✓
• Bumrah: 62 pts ✓
• Jadeja: 28 pts ✓
Remaining: 8 players → 145 pts potential
──────────────────────────────────────────
```

---

## Implementation Notes

### Scoring Pipeline
1. Match starts → Track player performances
2. Real-time point updates via WebSocket
3. Category totals calculated automatically
4. Winner determined at match end
5. Standings updated

### Key Tables Needed
```sql
-- Weekly matchups
CREATE TABLE weekly_matchups (
  id,
  league_id,
  week_number,
  home_team_id,
  away_team_id,
  home_score,
  away_score,
  home_wins,  -- categories won
  away_wins,
  status      -- 'pending', 'live', 'completed'
);

-- Season standings
CREATE TABLE standings (
  league_id,
  team_id,
  wins,
  losses,
  ties,
  total_points,
  rank
);
```

---

*Weekly H2H Format v1.0*
