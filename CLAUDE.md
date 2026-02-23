# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a full-stack IPL Fantasy Cricket application with:
- **Backend**: Node.js/Express API server (port 3001)
- **iOS**: SwiftUI native app (MVVM architecture)
- **Database**: PostgreSQL + Redis (via Docker)
- **Real-time**: Socket.io for live drafts and chat

## Common Commands

### Development
```bash
# Start all services (backend + Docker)
make dev

# Start Docker services only
make docker-up

# Initialize database
make db-init

# Run backend with hot reload
cd backend && npm run dev
```

### Testing
```bash
# Backend unit tests
cd backend && npm test

# Backend tests with coverage
cd backend && npm run test:coverage

# E2E tests (requires backend running)
cd e2e && npx playwright test
```

### Linting
```bash
# Backend linting
cd backend && npm run lint
cd backend && npm run lint:fix
```

### iOS
```bash
cd iOS
xcodegen generate    # Regenerate project after project.yml changes
pod install         # Install dependencies
# Open IPLFantasyPro.xcodeproj in Xcode
```

## Architecture

### Backend Structure
- `backend/src/index.js` - Express server entry point
- `backend/src/routes/` - API route handlers (auth, leagues, players, drafts, teams, matches, chat, trades, scores, analytics)
- `backend/src/middleware/` - Authentication (JWT), validation, logging
- `backend/src/db/` - Database pool, initialization, migrations

### iOS Structure (MVVM)
- `Sources/Screens/` - SwiftUI views (Auth, Draft, League, Team, Match, Chat, etc.)
- `Sources/ViewModels/` - ViewModels (AuthViewModel, DraftViewModel, LeagueViewModel, TeamViewModel)
- `Sources/Services/` - APIService, AuthService, DraftService, WebSocketService
- `Sources/Models/` - Data models (Player, Match, UserLeague, etc.)
- `Sources/Components/` - Reusable UI components
- `Sources/Theme/` - Colors, fonts, spacing constants

### Authentication
- Backend uses JWT tokens with Bearer auth header
- Middleware: `authenticate` (required), `optionalAuth` (optional)
- iOS uses Firebase Auth (Google + Apple Sign In)

### Real-time (Socket.io)
- Events: `draft:started`, `draft:bid`, `draft:sold`, `chat:message`, `trade:proposed`
- Users join league-specific rooms (`league-{leagueId}`)

### Database
- PostgreSQL: Users, leagues, players, teams, drafts, matches, scores
- Redis: Session/caching layer
