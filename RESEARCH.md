# Research: Fantasy Cricket Apps

## Executive Summary
This research covers the fantasy sports landscape, IPL ecosystem, and user needs to build a competitive fantasy cricket platform.

---

## 1. Market Research

### Fantasy Sports Growth
- 150M+ fantasy sports users in India alone
- Cricket accounts for 90%+ of Indian fantasy market
- IPL drives 3x traffic during season
- Average user spends 45 mins/day during IPL

### Competitor Analysis

| App | Strengths | Weaknesses |
|-----|-----------|------------|
| Dream11 | Large user base, good UX | Expensive, limited customization |
| MPL | Games variety, wallet | Complex, too many ads |
| ESPN | Brand trust, stats | No auction mode |
| Yahoo | Snake drafts | Limited cricket support |
| Our App | Auction drafts, custom leagues | New entrant |

---

## 2. User Research

### Target Personas

#### 1. The Fantasy Veteran (Age 25-40)
- Has played Dream11/ESPN for years
- Wants better customization
- Frustrated with one-size-fits-all
- **Needs:** Flexible scoring, custom leagues, better analytics

#### 2. The IPL Fan (Age 18-35)
- Watches every match
- Wants to feel more invested
- Casual player, not expert
- **Needs:** Easy onboarding, fun features, social

#### 3. The Commissioner (Age 30-45)
- Organizes work/friend leagues
- Manages draft day
- **Needs:** Reliable tools, automation, good draft UX

#### 4. The Data Nerd (Age 22-35)
- Loves stats and analysis
- Trades players based on projections
- **Needs:** Deep stats, projections, value analysis

---

## 3. Feature Research

### Auction Draft Mode
- Most popular in IPL-style fantasy
- Mimics real team building
- Higher engagement than salary cap
- **Key Features:**
  - Reserve list
  - Max bid limits
  - Auto-bid
  - Un-sold pile

### Snake Draft
- Traditional fantasy format
- Faster than auction
- **Key Features:**
  - Auto-pick
  - Draft timer
  - Keeper support

### Live Scoring
- Real-time point updates
- Match simulation
- **Key Features:**
  - Push notifications
  - Score widgets
  - Leaderboard updates

---

## 4. Technical Research

### Scoring System Analysis
Best practices from existing apps:

1. **Points should reward activity**
   - Not just wickets/runs
   - Bonus for boundaries, dot balls
   - Fielding points important

2. **Multipliers create strategy**
   - Captain 2x is standard
   - Some apps add "impact player"

3. **Negative points prevent spamming**
   - Ducks penalized
   - Wides/no-balls cost points

### Real-time Architecture

```
Cricket API → Webhook → Queue → Worker → Cache → WebSocket → Client
```

Providers:
- CricAPI (₹5k/month)
- SportMonks (~$200/month)
- API Cricket (~$100/month)

---

## 5. IPL Ecosystem

### Season Structure
- March-May (2 months)
- 14 teams → 10 teams (2022+)
- ~74 matches per season
- Double headers common

### Key Events
1. **Auction** (pre-season) - Biggest engagement
2. **First match** - Peak interest
3. **Playoffs** - High engagement
4. **Final** - Maximum users

### Content Needs
- Match schedules
- Team announcements
- Injury updates
- Pitch reports
- Weather

---

## 6. Competitive Analysis

### What Works
1. **Simple onboarding** - Dream11 does this well
2. **Quick drafts** - No one wants 4 hour auctions
3. **Social proof** - League friends feature
4. **Instant feedback** - Points update quickly

### What Doesn't Work
1. **Complex scoring** - Confuses casual users
2. **Slow load times** - Users abandon
3. **Poor draft UX** - Biggest complaint
4. **Limited support** - No help when issues

---

## 7. Differentiation Strategy

### Our Unique Value

1. **True Auction Mode**
   - Not just "bid to select"
   - Full auction mechanics
   - Reserve lists
   - Auto-bid

2. **Custom Leagues**
   - Complete control
   - Private with friends
   - Custom scoring

3. **Better Draft Experience**
   - Real-time sync
   - Chat during draft
   - Player analytics
   - Clean UI

4. **Data Transparency**
   - All stats visible
   - No hidden algorithms
   - Fair play

---

## 8. Risk Analysis

### Risks
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| API costs high | Medium | High | Start with free tier, scale |
| User acquisition | High | High | SEO, referrals |
| Legal uncertainty | Low | High | Consult legal |
| Technical scale | Medium | Medium | Cloud-native |

### Mitigations
- Start with MVP only
- Focus on retention > acquisition
- Free tier with limits
- Partner with influencers

---

## 9. Conclusion

The market is ready for a modern, auction-focused fantasy cricket app. Key success factors:

1. **Auction first** - Our differentiator
2. **League with friends** - Network effect
3. **Great draft UX** - Reduce friction
4. **Live scores** - Keep engaged
5. **Fair & transparent** - Build trust

**Recommendation:** Proceed with development focusing on auction draft mode as primary differentiator.

---

*Research completed: February 20, 2026*
