# IPL Fantasy Pro - Auction Draft Logic

## Detailed Auction Mechanics

### 1. Pre-Draft Setup

#### League Commissioner Sets:
- **Purse Amount**: ₹50-100 lakhs (default: ₹50L)
- **Squad Size**: 7-25 players (default: 15)
- **Overseas Limit**: 4-8 players (default: 4)
- **Minimum Indian Players**: 5-7 (default: 7)
- **Draft Timer**: 30-120 seconds (default: 60s)
- **Minimum Bid Increment**: ₹1-5 lakhs (default: ₹1L)

#### Teams Prepare:
- **Reserve List**: Players they want but won't actively bid on
- **Max Bid Limits**: Cap on how high they'll go per player
- **Auto-Bid Settings**: How to handle when not present

---

### 2. Player Queue

#### Sorting (Commissioner can choose):
1. **By Price** - Highest base price first (most popular)
2. **By Role** - Bowlers → Batsmen → All-rounders → WK
3. **By Team** - MI → CSK → RCB → etc.
4. **Shuffle** - Random order

#### Player Presentation:
- Show current player prominently
- Display: Name, Team, Role, Base Price, Stats
- Show "Recent Form" indicator
- Show "Player Card" with key stats

---

### 3. Bidding Process

```
Auction Flow:
1. Announce Player
2. Opening Bid (can be base price or lower)
3. Teams Bid (raise hand / click bid)
4. Timer Counts Down
5. Last Bid Wins OR Timer Expires
6. Player Sold OR Unsold
7. Move to Next Player
```

#### Bid Rules:
- Minimum increment: ₹1 lakh
- New bid must exceed current high
- Team can bid on own players? No
- Can exceed max bid limit? No (auto-pass)
- All teams pass = Player unsold

---

### 4. Team Budget Tracking

#### Budget Display:
```
Team Name: 🔥 Fire
Budget: ₹42.5L / ₹50L (85%)
Spent: ₹7.5L
Players: 7/15
Overseas: 2/4
```

#### Auto-Pass Conditions:
- Budget below player's base price
- Would exceed squad limit
- Would exceed overseas limit
- Exceeds user's max bid setting
- Player is on blocked list

---

### 5. Special Scenarios

#### Player Goes Unsold:
- Move to "Unsold Pool"
- Can be picked after all players done
- Base price reduces by 50%

#### Short-handed Teams:
- If team has < minimum players at end
- Can pick from unsold at base/50% price

#### Bidding War:
- If two teams really want player
- No limit on back-and-forth
- Timer resets on each new bid
- "Going, Going, SOLD!"

#### Pause/Delay:
- Commissioner can pause
- Individual timers paused for absent teams
- Resume when ready

---

### 6. Auto-Bid System

#### User Sets:
```javascript
{
  // Always bid on these players
  "mustHave": ["Virat Kohli", "Jasprit Bumrah"],
  
  // Bid up to this price
  "maxBid": {
    "Virat Kohli": 18,
    "Jasprit Bumrah": 15
  },
  
  // Skip entirely
  "neverBid": ["Ashwin"], // Already have him
  
  // Bid strategy
  "strategy": "aggressive" // or "conservative"
}
```

#### Auto-Bid Logic:
```
For each player:
  IF player in mustHave AND bid < maxBid[player]:
    Auto-bid
  
  IF bid reaches maxBid[player]:
    Auto-pass
  
  IF strategy = aggressive AND bid < basePrice * 1.3:
    Continue bidding
  
  ELSE:
    Pass
```

---

### 7. Draft Completion

#### Final Checks:
- All teams have minimum players?
- Budget accounting correct?
- Overseas limits respected?
- Role requirements met?

#### Post-Draft:
- Lock all teams
- Calculate initial rankings
- Send notifications
- Set first match lineup deadline

---

### 8. In-Season Management

#### Mid-Season Trades:
- Propose trade (player swap + cash)
- Both teams must accept
- Commissioner approves
- Salary remains same

#### Player Injuries:
- Can replace injured player
- From unsold pool OR release (lose investment)
- Commissioner discretion

#### Substitution:
- Set playing XI before each match
- Captain/Vice must play
- Bench doesn't earn points

---

## Sample Auction Flow

```
Commissioner: "Next player - Jasprit Bumrah, Mumbai Indians, Bowler, Base Price ₹12 lakhs"

Team A: "₹12 lakhs"
Team C: "₹13 lakhs"
Team B: "₹14 lakhs"
Team A: "₹15 lakhs"
[Timer at 45 seconds...]

Team C: "₹16 lakhs"
Team A: [Thinking...]
[Timer at 15 seconds...]

Team A: "₹17 lakhs"
Team C: Pass
[Timer at 3 seconds...]

Commissioner: "Going once... Going twice... SOLD to Team A for ₹17 lakhs!"

System: "Team A spends ₹17L on Jasprit Bumrah. Remaining: ₹33L"
```

---

## UI Requirements

### Draft Room Must-Haves:
- [ ] Player being auctioned (large, prominent)
- [ ] Current high bid (big numbers)
- [ ] Timer (countdown, urgency colors)
- [ ] All team budgets (sidebar)
- [ ] Bid button (for active teams)
- [ ] Pass button
- [ ] Player stats card
- [ ] Draft queue (next 5 players)
- [ ] Completed picks list
- [ ] Chat panel (optional)
- [ ] Auto-bid toggle
- [ ] Commissioner controls

### Timer Colors:
- 60-30s: Green
- 30-15s: Yellow
- 15-0s: Red (pulsing)

---

## API Events (WebSocket)

```javascript
// Client joins draft room
socket.emit('draft:join', { leagueId, teamId });

// Server sends state
socket.on('draft:state', { 
  currentPlayer,
  currentBid,
  highBidder,
  timer,
  teamBudgets,
  pickQueue
});

// Client places bid
socket.emit('draft:bid', { amount });

// Server confirms
socket.on('draft:bid_confirmed', { bidAmount, teamId });
socket.on('draft:outbid', { newHighBid, teamId });

// Timer
socket.on('draft:timer', { remaining });
socket.on('draft:timer_warning', { at: 15 }); // 15 seconds

// Player sold
socket.on('draft:player_sold', { 
  player, 
  team, 
  finalBid 
});

// Player unsold
socket.on('draft:player_unsold', { player });

// Draft complete
socket.on('draft:complete', { finalTeams });
```

---

*Auction Logic v1.0*
