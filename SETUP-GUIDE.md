# IPL Fantasy Pro - Setup Guide

This guide will help you set up and run the complete IPL Fantasy Pro application.

---

## Prerequisites

### Required Software
| Software | Version | Install |
|----------|---------|---------|
| Node.js | 18+ | [nodejs.org](https://nodejs.org) |
| PostgreSQL | 14+ | [postgresql.org](https://www.postgresql.org/download/) |
| Xcode | 15+ | Mac App Store |
| XcodeGen | Latest | `brew install xcodegen` |
| CocoaPods | Latest | `sudo gem install cocoapods` |

### Optional (for development)
| Software | Purpose | Install |
|----------|---------|---------|
| Docker | Run PostgreSQL locally | `brew install docker` |
| TablePlus | Database GUI | [tableplus.com](https://tableplus.com) |

---

## Part 1: Backend Setup

### Step 1.1: Install Node Dependencies
```bash
cd backend
npm install
```

### Step 1.2: Configure Environment
```bash
cp .env.example .env
```

Edit `.env` file:
```env
# Server
NODE_ENV=development
PORT=3001

# Database (update with your credentials)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ipl_fantasy
DB_USER=postgres
DB_PASSWORD=your_password_here

# JWT (change this to something random)
JWT_SECRET=your-super-secret-key-change-this

# Allowed origins (comma-separated)
ALLOWED_ORIGINS=http://localhost:3000
```

### Step 1.3: Create Database
```bash
# Option A: If you have PostgreSQL installed
createdb ipl_fantasy

# Option B: Using Docker
docker run -d \
  --name ipl-fantasy-db \
  -e POSTGRES_DB=ipl_fantasy \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  postgres:15-alpine
```

### Step 1.4: Initialize Database
```bash
npm run db:init
```

Expected output:
```
Database tables created successfully!
Player database seeded!
```

### Step 1.5: Start Backend Server
```bash
npm run dev
```

You should see:
```
╔═══════════════════════════════════════════════════════════╗
║   IPL Fantasy Pro API Server                             ║
║   Version: 1.0.0                                         ║
║   Environment: development                               ║
║   Port: 3001                                             ║
╚═══════════════════════════════════════════════════════════╝
```

### Step 1.6: Test Backend
```bash
# Health check
curl http://localhost:3001/api/health

# Expected response:
{"status":"ok","timestamp":"2026-02-20T12:00:00.000Z","version":"1.0.0"}
```

---

## Part 2: iOS Setup

### Step 2.1: Install XcodeGen
```bash
# If not installed
brew install xcodegen
```

### Step 2.2: Install CocoaPods Dependencies
```bash
cd iOS
pod install
```

### Step 2.3: Generate Xcode Project
```bash
xcodegen generate
```

### Step 2.4: Open in Xcode
```bash
open IPLFantasyPro.xcodeproj
```

### Step 2.5: Configure App (Optional)

#### Google Sign In
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project
3. Enable "Sign in with Google" API
4. Create OAuth credentials (iOS)
5. Copy Client ID to `LoginView.swift`

#### Apple Sign In
1. In Xcode, select your project
2. Go to Signing & Capabilities
3. Add "Sign in with Apple" capability

### Step 2.6: Run the App
1. Select a simulator (e.g., iPhone 15)
2. Press ⌘+R to run

---

## Part 3: Docker Setup (Optional)

### Using Docker Compose
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

Services:
- API: http://localhost:3001
- PostgreSQL: localhost:5432
- Redis: localhost:6379

---

## Part 4: Project Structure

```
IPL-Fantasy/
├── backend/              # Node.js API server
│   ├── src/
│   │   ├── routes/     # API endpoints
│   │   ├── middleware/ # Auth, validation, logging
│   │   └── db/        # Database config
│   └── tests/         # Unit tests
│
├── iOS/                 # SwiftUI app
│   ├── Sources/
│   │   ├── App/        # App entry point
│   │   ├── Screens/    # All views
│   │   ├── ViewModels/ # MVVM view models
│   │   ├── Services/   # API, WebSocket
│   │   ├── Models/     # Data models
│   │   ├── Theme/     # Colors, fonts
│   │   └── Utils/     # Helpers
│   └── Tests/         # Unit tests
│
└── docs/               # Planning docs
```

---

## Part 5: API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/auth/register | Create account |
| POST | /api/auth/login | Login |
| GET | /api/auth/me | Get current user |

### Leagues
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/leagues | Get user's leagues |
| POST | /api/leagues | Create league |
| POST | /api/leagues/join | Join league |

### Players
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/players | Get all players |
| GET | /api/players/:id | Get player |

### Drafts
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/drafts/:id/bid | Place bid |
| POST | /api/drafts/:id/sell | Mark sold |

### Teams
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/teams/league/:id | Get team |
| PUT | /api/teams/:id/captain | Set captain |

### Matches
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/matches/league/:id/standings | Get standings |

### Scores
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/scores/live | Get live matches |

---

## Part 6: Testing

### Backend Tests
```bash
cd backend
node tests/unit.test.js
```

### iOS Tests
Open Xcode → Product → Test (⌘U)

---

## Part 7: Common Issues

### "Database connection refused"
- Make sure PostgreSQL is running
- Check DB credentials in `.env`

### "Port already in use"
- Change PORT in `.env`
- Or kill process using port: `lsof -ti:3001 | xargs kill`

### "Module not found"
- Run `npm install` again
- Delete `node_modules` and reinstall

### iOS Build Failed
- Open Xcode → Preferences → Components → Install simulators
- Run `pod install` again

---

## Part 8: Next Steps

After setup, you can:

1. **Test the app** - Use the testing guide
2. **Add real cricket data** - Integrate CricAPI
3. **Deploy to production** - Use the provided Docker/PM2 config
4. **Submit to App Store** - Create App Store Connect app

---

## Need Help?

- Check GitHub issues
- Review TESTING-GUIDE.md
- Check backend logs in terminal

**Happy Testing! 🎉**
