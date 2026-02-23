# League Invite System - IPL Fantasy Pro

## Overview
This document describes the League Invite System implementation for IPL Fantasy Pro, enabling users to share league invites and join leagues via unique invite codes.

## Features Implemented

### Backend API Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/leagues/invite/:code` | GET | No | Validate invite code (public) |
| `/api/leagues/:id/invite` | GET | Yes | Get league invite details |
| `/api/leagues/:id/invite/regenerate` | POST | Yes | Generate new invite code (commissioner only) |
| `/api/leagues/join` | POST | Yes | Join league with code |
| `/api/leagues` | GET | Yes | Get user's leagues |
| `/api/leagues` | POST | Yes | Create new league (auto-generates code) |

### Frontend Components

1. **LeagueInvite.js** - Component for commissioners to share invites
   - Display invite code
   - Copy to clipboard functionality
   - Share via Web Share API (mobile)
   - Regenerate invite code
   - Shows league info (name, code, max teams)

2. **JoinLeague.js** - Page for players to join via invite
   - Enter invite code
   - Validate code and show league details
   - Enter team name
   - Confirm and join
   - Deep link support (`/join/:code`)

3. **leagueApi.js** - API service for league operations
   - All API calls to league endpoints
   - Token-based authentication
   - Error handling

## Usage

### For Commissioners (Inviting Players)

```jsx
import LeagueInvite from './components/LeagueInvite';

function LeaguePage() {
  return (
    <LeagueInvite 
      leagueId="league-123"
      leagueName="IPL Champions 2026"
      onClose={() => console.log('Closed')}
    />
  );
}
```

### For Players (Joining a League)

```jsx
import JoinLeague from './pages/JoinLeague';

function App() {
  const handleJoinComplete = (leagueId) => {
    console.log('Joined league:', leagueId);
    // Navigate to league page
  };

  return (
    <JoinLeague 
      onJoinComplete={handleJoinComplete}
    />
  );
}
```

### Deep Linking

Users can share links like `https://app.example.com/join/ABC123`. The JoinLeague component automatically detects this pattern and pre-fills the invite code.

## Invite Code Format

- 6-character alphanumeric code
- Uppercase letters and numbers only
- Example: `ABC123`, `XYZ789`, `TEAM01`

## Security Considerations

1. Invite codes are unique and cannot be easily guessed
2. League capacity is enforced (can't join if full)
3. Users cannot join the same league twice
4. Only commissioners can regenerate invite codes
5. All join operations require authentication
