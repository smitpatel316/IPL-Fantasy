# IPL Fantasy Pro - Scoring System

## Complete Points Breakdown

### Batting Points

| Action | Points | Description |
|--------|--------|-------------|
| Every Run | +1 | Base points per run scored |
| Boundary Bonus | +2 | Extra for hitting 4s |
| Six Bonus | +4 | Extra for hitting 6s |
| 30+ Runs | +10 | Milestone bonus |
| Half-Century (50s) | +20 | 50 runs milestone |
| Century (100s) | +40 | 100 runs milestone |
| 150+ Runs | +60 | Big milestone |
| Double Century | +100 | Massive score |
| Duck (0) | -5 | Getting out for zero |
| Golden Duck | -10 | Out on first ball faced |
| Hit Wicket | -5 | Hit wicket dismissal |
| Obstructing Field | -5 | Obstructing field dismissal |
| Run Out (Batting) | -5 | Run out as batter |

---

### Bowling Points

| Action | Points | Description |
|--------|--------|-------------|
| Per Wicket | +30 | Base points per wicket |
| Maiden Over | +10 | Complete over with 0 runs |
| 4 Wickets | +20 | Bonus for 4+ |
| 5 Wickets | +40 | Bonus for 5+ |
| Hat-trick | +50 | 3 wickets in 3 balls |
|Dot Ball Bonus | +1 | Every dot ball |
| Wicket Ball | +5 | Ball that took wicket |
| No-ball (by bowler) | -2 | Extra runs conceded |
| Wide (by bowler) | -2 | Extra runs conceded |

---

### Fielding Points

| Action | Points | Description |
|--------|--------|-------------|
| Catch | +10 | Taking a catch |
| Catch (3+) | +20 | 3 catches in match |
| Stumping | +15 | Wicket-keeper stumping |
| Run Out (Direct) | +10 | Direct hit run out |
| Run Out (Assisted) | +5 | Assisted run out |
| Missed Catch | -5 | Dropped catch |

---

### Captain & Vice-Captain Multipliers

| Role | Multiplier | Notes |
|------|------------|-------|
| Captain | 2x | All points doubled |
| Vice-Captain | 1.5x | Points multiplied by 1.5 |
| Impact Player | 1.5x | Special player bonus |

**Note:** Captain choice must be made before match starts. If captain doesn't play, no multiplier applies.

---

### Team Performance Bonuses

| Action | Points | Description |
|--------|--------|-------------|
| Team Win | +20 | Your team wins match |
| Team Loss | +0 | No penalty for loss |
| Team Tie | +10 | Match tied |
| 10+ Runs Win | +10 | Bonus for big win |
| Wicket Win | +10 | Bonus for win by wickets |

---

### Player of the Match

| Action | Points | Description |
|--------|--------|-------------|
| Player of Match | +50 | Awarded by match officials |

---

## Example Point Calculation

### Jasprit Bumrah Performance

```
Bowling:
- 4 wickets: 4 × 30 = +120
- Maiden over: +10
- 2 boundaries saved (dot balls): 2 × 1 = +2
- 4 wicket bonus: +20

Total Bowling: +152

Fielding:
- 1 catch: +10

Total Fielding: +10

Captain (2x multiplier if captain):
- (152 + 10) × 2 = +324 points

NOT captain:
- 152 + 10 = 162 points
```

---

### Rohit Sharma Performance

```
Batting:
- 65 runs: 65 × 1 = +65
- 5 fours: 5 × 2 = +10
- 3 sixes: 3 × 4 = +12
- Half-century bonus: +20
- 30+ runs bonus: +10

Total Batting: +117

Fielding:
- 1 catch: +10

Total Fielding: +10

Vice-Captain (1.5x):
- (117 + 10) × 1.5 = +190.5 points
```

---

## Points Table Reference

### Batting Milestones

| Milestone | Points | Cumulative for 65 runs |
|-----------|--------|----------------------|
| 0 runs | 0 | -5 (duck) |
| 10 runs | 10 | +5 |
| 25 runs | 25 | +15 |
| 30 runs | 30+10 | +40 (milestone) |
| 50 runs | 50+20+10 | +80 (half-century) |
| 65 runs | 65+10+4+12+20 | +111 (with milestones) |

### Bowling Milestones

| Wickets | Base | Milestone | Total |
|---------|------|-----------|-------|
| 1 wkt | 30 | - | 30 |
| 2 wkts | 60 | - | 60 |
| 3 wkts | 90 | - | 90 |
| 4 wkts | 120 | +20 | 140 |
| 5 wkts | 150 | +40 | 190 |

---

## Tie-Breaking Rules

If teams have equal points:

1. **Total Points** - Higher total wins
2. **Most Runs Scored** - Team with more runs
3. **Most Wickets Taken** - Team with more wickets
4. **Head-to-Head** - Winner in direct matchup
5. **Coin Toss** - Random (rarely needed)

---

## Match Types

### League Matches
- Standard scoring as above
- Points from all 11 playing members

### Knockout/Playoffs
- Same scoring
- Bonus: Winner gets +50 points

### Super Over
- No fantasy points for Super Over
- Only main innings count

---

## Scoring Engine Implementation

```javascript
function calculatePlayerPoints(player, match) {
  let points = 0;
  const breakdown = {};
  
  // Batting
  if (player.batting) {
    points += player.runs * 1;
    breakdown.runs = player.runs;
    
    if (player.runs >= 4) points += (player.runs - 3) * 2; // boundaries
    if (player.runs >= 6) points += (player.runs - 3) * 4; // sixes
    
    if (player.runs >= 100) points += 40;
    else if (player.runs >= 50) points += 20;
    else if (player.runs >= 30) points += 10;
    
    if (player.runs === 0) points -= 5;
  }
  
  // Bowling
  if (player.bowling) {
    points += player.wickets * 30;
    points += player.maidens * 10;
    if (player.wickets >= 5) points += 40;
    else if (player.wickets >= 4) points += 20;
  }
  
  // Fielding
  points += player.catches * 10;
  points += player.stumpings * 15;
  points += player.runouts * 10;
  
  // Multiplier
  const multiplier = player.isCaptain ? 2 : player.isViceCaptain ? 1.5 : 1;
  points *= multiplier;
  
  return { total: Math.round(points), breakdown };
}
```

---

## Displaying Points

### Player Card
```
Jasprit Bumrah
MI | Bowler
---
Today's Points: 162
🏏 4/28 (4.2 ov)
✋ 1 Catch
⭐ Captain: 2x → 324 pts
```

### Leaderboard
```
🏆 LEAGUE STANDINGS
─────────────────────
1. 🔥 Team Fire      1,845 pts
2. ⚡ Team Bolt      1,792 pts
3. 🌟 Team Star     1,756 pts
4. 💥 Team Boom     1,698 pts
5. 🎯 Team Aim     1,645 pts
```

---

*Scoring System v1.0*
