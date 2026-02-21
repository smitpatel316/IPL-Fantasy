# IPL Fantasy Pro - Manual Testing Guide

**App Version:** 1.0.0  
**Test Date:** _____________  
**Tester:** _____________

---

## Pre-Test Setup

### Backend
```bash
cd backend
npm install
# Configure .env with your database
cp .env.example .env
npm run db:init
npm run dev
```
Server runs at: http://localhost:3001

### iOS
```bash
cd iOS
xcodegen generate
open IPLFantasyPro.xcodeproj
```
Run on simulator or device

---

## Test 1: Authentication

### 1.1 Email Registration
- [ ] Open app
- [ ] Tap "Create Account"
- [ ] Enter email: _____________@test.com
- [ ] Enter password: test123456
- [ ] Enter display name: Test User
- [ ] Tap "Create Account"
- [ ] **Expected:** Navigate to dashboard
- [ ] **Actual:** 
- [ ] **Comments:**

### 1.2 Email Login
- [ ] Logout (if logged in)
- [ ] Enter email: _____________@test.com
- [ ] Enter password: test123456
- [ ] Tap "Login"
- [ ] **Expected:** Navigate to dashboard
- [ ] **Actual:**
- [ ] **Comments:**

### 1.3 Google Sign In
- [ ] Tap "Continue with Google"
- [ ] **Expected:** Google Sign In sheet appears
- [ ] **Actual:**
- [ ] **Comments:**

### 1.4 Apple Sign In
- [ ] Tap "Sign in with Apple"
- [ ] **Expected:** Apple Sign In sheet appears
- [ ] **Actual:**
- [ ] **Comments:**

### 1.5 Invalid Login
- [ ] Enter wrong password
- [ ] Tap "Login"
- [ ] **Expected:** Error message "Invalid credentials"
- [ ] **Actual:**
- [ ] **Comments:**

### 1.6 Logout
- [ ] Go to Profile
- [ ] Tap "Log Out"
- [ ] **Expected:** Return to login screen
- [ ] **Actual:**
- [ ] **Comments:**

---

## Test 2: League Management

### 2.1 Create League
- [ ] Go to Leagues tab
- [ ] Tap "+" or "Create League"
- [ ] Enter league name: Test League
- [ ] Set max teams: 8
- [ ] Set budget: 50Cr
- [ ] Tap "Create"
- [ ] **Expected:** League created, see code
- [ ] **Actual:**
- [ ] **League Code:** _____________

### 2.2 Join League
- [ ] Logout and create another account
- [ ] Tap "Join League"
- [ ] Enter code from 2.1: _____________
- [ ] Enter team name: Test Team 2
- [ ] Tap "Join"
- [ ] **Expected:** Added to league
- [ ] **Actual:**
- [ ] **Comments:**

### 2.3 View League Details
- [ ] Tap on league
- [ ] **Expected:** See members, settings
- [ ] **Actual:**
- [ ] **Comments:**

---

## Test 3: Auction Draft

### 3.1 Start Draft (Commissioner)
- [ ] As commissioner, open league
- [ ] Tap "Start Draft"
- [ ] **Expected:** Draft room opens, first player shown
- [ ] **Actual:**
- [ ] **Comments:**

### 3.2 Place Bid
- [ ] Tap "+1Cr" or enter custom bid
- [ ] Tap "Place Bid"
- [ ] **Expected:** Bid updates, timer resets
- [ ] **Actual:**
- [ ] **Comments:**

### 3.3 Player Sold
- [ ] As commissioner, tap "Sold"
- [ ] **Expected:** Player moves to team, next player appears
- [ ] **Actual:**
- [ ] **Comments:**

### 3.4 Player Unsold
- [ ] Tap "Unsold"
- [ ] **Expected:** Player removed, next appears
- [ ] **Actual:**
- [ ] **Comments:**

---

## Test 4: Team Management

### 4.1 View My Team
- [ ] Go to "My Team" tab
- [ ] **Expected:** See 15 players
- [ ] **Actual:**
- [ ] **Comments:**

### 4.2 Set Captain
- [ ] Select a player
- [ ] Tap "Make Captain"
- [ ] **Expected:** Player marked as C, 2x points
- [ ] **Actual:**
- [ ] **Comments:**

### 4.3 Set Vice-Captain
- [ ] Select another player
- [ ] Tap "Make Vice Captain"
- [ ] **Expected:** Player marked as VC, 1.5x points
- [ ] **Actual:**
- [ ] **Comments:**

---

## Test 5: Match Center

### 5.1 Live Scores
- [ ] Go to Match tab
- [ ] **Expected:** See live matches
- [ ] **Actual:**
- [ ] **Comments:**

### 5.2 Points Update
- [ ] Wait for refresh
- [ ] **Expected:** Points update
- [ ] **Actual:**
- [ ] **Comments:**

---

## Test 6: Standings

### 6.1 View Standings
- [ ] Go to Standings tab
- [ ] **Expected:** See teams ranked by points
- [ ] **Actual:**
- [ ] **Comments:**

### 6.2 Week Filter
- [ ] Tap different week
- [ ] **Expected:** Standings update
- [ ] **Actual:**
- [ ] **Comments:**

---

## Test 7: Player Search

### 7.1 Search by Name
- [ ] Go to Draft/Players
- [ ] Type "Kohli"
- [ ] **Expected:** Filter to matching players
- [ ] **Actual:**
- [ ] **Comments:**

### 7.2 Filter by Team
- [ ] Select "MI" team filter
- [ ] **Expected:** Only MI players shown
- [ ] **Actual:**
- [ ] **Comments:**

### 7.3 Filter by Role
- [ ] Select "Bowler" role
- [ ] **Expected:** Only bowlers shown
- [ ] **Actual:**
- [ ] **Comments:**

---

## Test 8: League Chat

### 8.1 Send Message
- [ ] Open league chat
- [ ] Type message: "Hello everyone!"
- [ ] Tap Send
- [ ] **Expected:** Message appears
- [ ] **Actual:**
- [ ] **Comments:**

### 8.2 Receive Message
- [ ] As other user, send message
- [ ] **Expected:** Message appears in real-time
- [ ] **Actual:**
- [ ] **Comments:**

---

## Test 9: Settings

### 9.1 Toggle Dark Mode
- [ ] Go to Settings
- [ ] Toggle Dark Mode
- [ ] **Expected:** UI switches theme
- [ ] **Actual:**
- [ ] **Comments:**

### 9.2 Notifications
- [ ] Toggle notifications
- [ ] **Expected:** Setting saved
- [ ] **Actual:**
- [ ] **Comments:**

---

## Test 10: Profile

### 10.1 View Profile
- [ ] Go to Profile tab
- [ ] **Expected:** See user info, stats, achievements
- [ ] **Actual:**
- [ ] **Comments:**

### 10.2 Edit Display Name
- [ ] Tap "Edit Profile"
- [ ] Change name to: Updated Name
- [ ] Save
- [ ] **Expected:** Name updated
- [ ] **Actual:**
- [ ] **Comments:**

---

## Bugs & Issues Found

| # | Feature | Issue Description | Severity | Status |
|---|---------|------------------|----------|--------|
| 1 |         |                  |          |        |
| 2 |         |                  |          |        |
| 3 |         |                  |          |        |
| 4 |         |                  |          |        |
| 5 |         |                  |          |        |

---

## Notes & Observations

_______________________________________________________
_______________________________________________________
_______________________________________________________
_______________________________________________________

## Summary

| Category | Tested | Passed | Failed | Not Tested |
|----------|--------|---------|--------|------------|
| Authentication | | | | |
| League Management | | | | |
| Auction Draft | | | | |
| Team Management | | | | |
| Match Center | | | | |
| Standings | | | | |
| Player Search | | | | |
| Chat | | | | |
| Settings | | | | |
| Profile | | | | |

---

## Next Steps

- [ ] Fix critical bugs
- [ ] Re-test failed features
- [ ] Add automated tests for passing features

**Testing Complete:** _____________
