# IPL Fantasy Pro - E2E Tests

## Setup

```bash
cd e2e
npm install
npx playwright install chromium
```

## Running Tests

```bash
# Run all tests
npm test

# Run with UI mode
npm run test:ui

# Run with headed browser
npm run test:headed

# Run specific spec file
npx playwright test auth.spec.js

# Generate HTML report
npm run test:report
```

## Test Structure

```
e2e/
├── app.spec.js          # Main UI tests (home, auth, leagues, draft, team, match pages)
├── auth.spec.js         # Authentication API tests
├── league.spec.js       # League management API tests
├── draft.spec.js        # Auction draft API tests
├── team.spec.js         # Team management API tests
├── match.spec.js        # Match and scores API tests
├── player.spec.js       # Players API and health check tests
├── playwright.config.js # Playwright configuration
└── package.json
```

## Test Suites

### app.spec.js - UI Tests
- Home page rendering
- Authentication UI flows
- League management UI
- Draft room UI
- Team management UI
- Match center UI
- Responsive design (mobile, tablet, desktop)
- Accessibility checks

### auth.spec.js - Authentication API
- User registration with validation
- Login with valid/invalid credentials
- Token-based authentication
- Protected route access

### league.spec.js - League Management API
- Create/view/update leagues
- Join league with code
- League members management
- Draft status for leagues

### draft.spec.js - Auction Draft API
- View available players
- Place bids with validation
- View draft teams and sold players
- Draft clock management

### team.spec.js - Team Management API
- View team details and players
- Set captain and vice-captain
- Points calculation
- Points breakdown by match

### match.spec.js - Match & Scores API
- List live/upcoming/completed matches
- Match scores and details
- Player points for matches
- Analytics endpoints

### player.spec.js - Players API
- List/search players
- Filter by team or role
- Player statistics
- Health check endpoint

## Configuration

Set environment variables:
- `BASE_URL` - Frontend URL (default: http://localhost:3000)
- `API_URL` - Backend API URL (default: http://localhost:3001)

## Running Tests with Environment

```bash
# With custom URLs
BASE_URL=http://localhost:3000 API_URL=http://localhost:3001 npm test

# Run specific browser
npx playwright test --project=chromium

# Run only API tests
npx playwright test auth.spec.js league.spec.js draft.spec.js team.spec.js match.spec.js player.spec.js

# Run only UI tests
npx playwright test app.spec.js
```
