# IPL Fantasy Pro 🏏

A full-stack fantasy cricket application with league management, auction drafting, and real-time scoring.

## Features

### Core Features
- **User Authentication** - Register, login, JWT-based auth
- **League Management** - Create, join, invite friends
- **Auction Draft** - Real-time bidding with timer
- **Team Management** - Set captain, vice-captain, lineup
- **Live Scoring** - Real-time match updates
- **Standings** - Weekly head-to-head rankings

### Additional Features
- **Player Search** - Filter by team, role, price
- **League Chat** - Real-time messaging
- **Notifications** - Match updates, trade offers
- **Compare Teams** - Side-by-side analysis
- **Profile & Stats** - Lifetime achievements
- **Settings** - Notifications, preferences

## Tech Stack

### iOS App
- **SwiftUI** - Native iOS UI
- **MVVM** - Architecture
- **Combine** - Reactive programming
- **WebSocket** - Real-time updates

### Backend
- **Node.js** - Runtime
- **Express** - Web framework
- **PostgreSQL** - Database
- **Socket.io** - Real-time communication
- **JWT** - Authentication

## Project Structure

```
IPL-Fantasy/
├── iOS/                    # SwiftUI app
│   └── Sources/
│       ├── App/           # App entry, ContentView
│       ├── Components/    # Reusable UI components
│       ├── Models/        # Data models
│       ├── Screens/       # All app screens
│       ├── Services/      # API services
│       ├── Theme/         # Colors, fonts, spacing
│       └── ViewModels/    # MVVM view models
│
├── backend/               # Node.js API
│   └── src/
│       ├── db/           # Database config & init
│       └── routes/       # API routes
│
└── docs/                 # Planning documents
```

## Getting Started

### Prerequisites
- Node.js 18+
- PostgreSQL 14+
- Xcode 15+ (for iOS)

### Backend Setup

```bash
cd backend
npm install
cp .env.example .env
# Edit .env with your database credentials
npm run db:init
npm run dev
```

### iOS Setup

```bash
cd iOS
xcodegen generate
open IPLFantasyPro.xcodeproj
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `/api/auth` | Authentication |
| `/api/leagues` | League CRUD |
| `/api/players` | Player database |
| `/api/drafts` | Auction draft |
| `/api/teams` | Team management |
| `/api/matches` | Scores & standings |
| `/api/chat` | League chat |
| `/api/trades` | Player trades |

## WebSocket Events

- `draft:started` - Auction started
- `draft:bid` - New bid placed
- `draft:sold` - Player sold
- `chat:message` - New chat message
- `trade:proposed` - Trade offer

## Database Schema

- `users` - User accounts
- `leagues` - League definitions
- `league_members` - League participants
- `players` - IPL player database
- `teams` - Fantasy teams
- `team_players` - Players in teams
- `auction_drafts` - Draft state
- `matchups` - Weekly matchups

## Planning Documents

- SPEC.md - Product specification
- ARCHITECTURE.md - Technical architecture
- UI-DESIGN.md - Wireframes
- PLAYER-DATABASE.md - Player data
- SCORING-SYSTEM.md - Points calculation
- WEEKLY-H2H.md - Match format
- PLAYOFFS.md - Championship structure

## License

MIT

## Author

Smit Patel
