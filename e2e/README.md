# IPL Fantasy Pro - E2E Tests

## Setup

```bash
cd e2e
npm install @playwright/test
npx playwright install chromium
```

## Running Tests

```bash
# Run all tests
npx playwright test

# Run with UI
npx playwright test --ui

# Run specific test
npx playwright test login.spec.ts
```

## Test Suites

### Auth Tests (auth.spec.ts)
- User can register with valid email
- User can login with correct credentials
- Invalid credentials are rejected
- Token is stored securely

### League Tests (league.spec.ts)
- User can create a league
- User can join a league with code
- League shows correct member count
- Commissioner can manage league

### Draft Tests (draft.spec.ts)
- Draft room displays available players
- User can place bids
- Timer counts down correctly
- Player is sold to highest bidder

### Team Tests (team.spec.ts)
- User can view their team
- User can set captain
- User can set vice-captain
- Points calculate correctly

### Match Tests (match.spec.ts)
- Live match displays scores
- Category breakdown is accurate
- Standings update correctly
