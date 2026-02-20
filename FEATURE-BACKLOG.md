# IPL Fantasy Pro - Feature Backlog

## Priority Matrix

### P0 - Must Have (MVP)

| Feature | Description | Effort | Value |
|---------|-------------|--------|--------|
| User Auth | Register, login, JWT | L | H |
| League Creation | Create league, settings | M | H |
| Player Database | All players with stats | M | H |
| Auction Draft | Full auction flow | L | H |
| Team Management | Set lineup, captain | M | H |
| Basic Scoring | Calculate points | M | H |
| League Dashboard | View standings | S | M |

### P1 - Should Have

| Feature | Description | Effort | Value |
|---------|-------------|--------|--------|
| Snake Draft | Traditional draft mode | M | H |
| Live Match Center | Real-time scores | L | H |
| Invite System | Share league links | S | M |
| Auto-pick | Draft automation | S | M |
| Player Search | Find players | S | M |
| Draft Chat | League chat | M | M |

### P2 - Nice to Have

| Feature | Description | Effort | Value |
|---------|-------------|--------|--------|
| Salary Cap Mode | Budget-based picking | M | M |
| Trade System | Between teams | L | M |
| Keeper System | Carry players over | M | M |
| Analytics | Projections, value | L | M |
| Social Features | Friends, public leagues | M | L |
| Draft Templates | Pre-set strategies | S | L |

### P3 - Future

| Feature | Description | Effort | Value |
|---------|-------------|--------|--------|
| Daily Fantasy | DFS contests | L | H |
| Playoffs | Championship format | M | L |
| Mobile App | iOS/Android | XL | H |
| AI Assistant | Draft advice | M | M |
| Multiple Leagues | Join many | S | L |

---

## Sprint Planning

### Sprint 1: Foundation (Week 1-2)
- [ ] Project setup (React + Node)
- [ ] User authentication
- [ ] Database schema
- [ ] Basic routing

**Deliverable:** Running app with login

### Sprint 2: League & Players (Week 3-4)
- [ ] Create/join leagues
- [ ] Player database with search
- [ ] Player cards UI

**Deliverable:** Can browse players, create league

### Sprint 3: Auction Draft (Week 5-6)
- [ ] Draft room UI
- [ ] Bidding logic
- [ ] Timer system
- [ ] Auto-bid

**Deliverable:** Can run complete auction

### Sprint 4: Team Management (Week 7-8)
- [ ] Set lineup
- [ ] Captain/vice selection
- [ ] Points display

**Deliverable:** Can manage team after draft

### Sprint 5: Scoring & Match Center (Week 9-10)
- [ ] Scoring engine
- [ ] Match simulation
- [ ] Live leaderboard

**Deliverable:** Points calculate correctly

### Sprint 6: Polish (Week 11-12)
- [ ] Edge cases
- [ ] Error handling
- [ ] UX improvements
- [ ] Testing

**Deliverable:** Production-ready MVP

---

## Technical Debt

### Before Launch
- [ ] Add indexes for performance
- [ ] Set up caching layer
- [ ] Configure CDN
- [ ] Set up monitoring

### After MVP
- [ ] Refactor scoring engine
- [ ] Add WebSocket optimization
- [ ] Consider GraphQL for complex queries
- [ ] Add E2E tests

---

## Dependencies

### Frontend
```
react: ^18.2.0
react-router-dom: ^6.x
zustand: ^4.x
tailwindcss: ^3.x
socket.io-client: ^4.x
axios: ^1.x
date-fns: ^3.x
react-hook-form: ^7.x
zod: ^3.x
```

### Backend
```
express: ^4.x
socket.io: ^4.x
pg: ^8.x
redis: ^4.x
jsonwebtoken: ^9.x
bcrypt: ^5.x
zod: ^3.x
cors: ^2.x
helmet: ^7.x
```

---

## Milestones

| Milestone | Target | Features |
|-----------|--------|----------|
| M1: Auth | Week 1 | Login, register |
| M2: League | Week 2 | Create/join leagues |
| M3: Players | Week 3 | Browse players |
| M4: Draft | Week 5 | Run auction |
| M5: Team | Week 6 | Set lineup |
| M6: Scoring | Week 8 | Points work |
| M7: MVP | Week 10 | Ship! |

---

*Backlog Version: 1.0*
