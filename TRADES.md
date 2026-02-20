# IPL Fantasy Pro - Trade System

## Trade Overview

### Why Trades Matter
- Keeps league active all season
- Allows teams to address weaknesses
- Creates league engagement
- No team is stuck with bad picks

---

## Trade Types

### 1. Player-for-Player Swap
Most common trade format:

```
Team A sends: Virat Kohli (₹15L)
Team B sends: KL Rahul (₹12L) + ₹3L cash

Result: Direct swap
```

### 2. Player + Cash Trade
When values don't match:

```
Team A sends: Mohammed Shami (₹8L)
Team B sends: Yuzvendra Chahal (₹6L) + ₹2L cash

Team A gets: Better spinner + cash
Team B gets: Better pacer
```

### 3. Multi-Player Trade
Bigger trades:

```
Team A sends: Rohit + Jadeja (₹26L combined)
Team B sends: Gill + Shami + Chakravarthy (₹22L combined) + ₹4L cash
```

---

## Trade Rules

### Commissioner's Settings

| Rule | Options | Default |
|------|---------|---------|
| Trade Window | Pre-season only / Mid-season only / Both | Both |
| Trade Deadline | Week 7-14 | Week 10 |
| Max Trades | 3-10 per team | 5 |
| Cash Allowed | Yes/No | Yes |
| Player-for-Player | Yes/No | Yes |
| Draft Picks | Yes/No | No |

### Trade Requirements
- Both teams must approve
- Commissioner can veto
- Minimum 2 players involved (no cash-only)
- Can't exceed roster limits
- Must follow overseas rules

---

## Trade Workflow

### Step 1: Propose Trade
```
Team A proposes:
- Send: Virat Kohli (₹15L)
- Receive: KL Rahul (₹12L) + ₹3L cash
- Reason: "Need WK, Rahul is in better form"
```

### Step 2: Review Period
- Other team gets notification
- Can accept, counter, or reject
- 24-48 hours to respond

### Step 3: Counter Offer
```
Team B counters:
- Send: KL Rahul + ₹3L
- Receive: Kohli + Ruturaj (₹8L)
- Reason: "Add young talent"
```

### Step 4: Accept/Reject
- Both teams must agree
- Commissioner notified
- Trade executes

### Step 5: Trade Executed
- Players swap teams
- Budgets updated
- League notified

---

## Trade Calculator

### Fair Trade Logic
```
Trade is "fair" if:
|Team A Give Value - Team B Give Value| < ₹2L

Otherwise: Add cash to balance
```

### Calculator UI
```
═══════════════════════════════════════════
  PROPOSE TRADE
═══════════════════════════════════════════

Team A Gives:
┌─────────────────────────────────────────┐
│ [x] Virat Kohli - ₹15L - 245 pts      │
│ [ ] Ruturaj Gaikwad - ₹8L - 156 pts   │
└─────────────────────────────────────────┘

Team B Gives:
┌─────────────────────────────────────────┐
│ [x] KL Rahul - ₹12L - 198 pts         │
│ [ ] cash: ₹3L                         │
└─────────────────────────────────────────┘

──────────────────────────────────────────
Analysis:
• Team A: -₹3L value disadvantage
• Team B: +₹3L value advantage
• Recommendation: Add ₹3L cash or different player
──────────────────────────────────────────

[COUNTER] [ACCEPT] [REJECT]
```

---

## Trade Market

### Public Trade Board (Optional Feature)
- See available players from other teams
- "Looking for" posts
- Open to offers

### Trade Offers
```
🔵 Team Fire is LOOKING FOR:
   • Quality WK
   • Budget bowler
   Offer: Virat Kohli + ₹5L

🟢 Team Bolt is LOOKING FOR:  
   • Exploding batsman
   Offer: Can match value
```

---

## Trade Analytics

### Trade History
```
═══════════════════════════════════════════
  TRADE HISTORY - Season 2026
═══════════════════════════════════════════

Week 8: Fire ↔ Bolt
  Fire gets: KL Rahul (₹12L) + ₹3L
  Bolt gets: Virat Kohli (₹15L)
  
  Winner: Fire (Kohli underperformed)

Week 11: Star ↔ Crown
  Star gets: Bumrah (₹12L)
  Crown gets: Shami + ₹3L
  
  Winner: Star (Bumrah was key)
```

### Trade Impact
- Track points before/after trade
- Did it improve the team?
- Net points gained/lost

---

## Trade Restrictions

### Blackout Periods
- No trades during active matchup week
- 48 hours before playoffs start
- Championship week

### Veto Power
- Commissioner can veto
- Requires 50%+ league vote
- Must document reason

### Emergency Trades
- Injury exceptions allowed
- Commissioner approval required
- May add salary relief

---

## Trade Notifications

### In-App
- "New trade offer from Team X"
- "Your trade was accepted!"
- "Team Y counter-offered"

### Email
- Trade proposal received
- Trade executed
- Weekly trade summary

---

## Trade UI Mockup

```
═══════════════════════════════════════════
  TRADES - Team Fire
═══════════════════════════════════════════

ACTIVE OFFERS
──────────────────────────────────────────
From Team Bolt:
  They give: KL Rahul (₹12L) + ₹3L
  You give: Virat Kohli (₹15L)
  
  [ACCEPT] [COUNTER] [REJECT]

──────────────────────────────────────────
YOUR TRADES
──────────────────────────────────────────
• Week 8: Acquired KL Rahul from Bolt
• Week 11: Sent Rohit to Crown for Shami

──────────────────────────────────────────
MAKE OFFER
──────────────────────────────────────────
Select player to offer: [Dropdown]
Select target team: [Dropdown]
Add cash: [₹___]
Message: [Optional]

[SUBMIT OFFER]
```

---

## Database Schema

```sql
CREATE TABLE trade_proposals (
  id UUID PRIMARY KEY,
  league_id UUID,
  proposing_team_id UUID,
  receiving_team_id UUID,
  players_giving JSONB, -- [{player_id, price}]
  players_receiving JSONB,
  cash_giving DECIMAL,
  cash_receiving DECIMAL,
  status VARCHAR(20), -- 'pending', 'accepted', 'rejected', 'countered'
  message TEXT,
  created_at TIMESTAMP,
  expires_at TIMESTAMP
);

CREATE TABLE trades (
  id UUID PRIMARY KEY,
  league_id UUID,
  team_a_id UUID,
  team_b_id UUID,
  players_a_to_b JSONB,
  players_b_to_a JSONB,
  cash_a_to_b DECIMAL,
  cash_b_to_a DECIMAL,
  executed_at TIMESTAMP,
  proposed_by UUID
);
```

---

*Trade System v1.0*
