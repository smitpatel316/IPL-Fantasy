# iOS E2E Tests

This directory contains E2E tests for the IPL Fantasy Pro iOS app using two frameworks:

1. **XCUITest** - Native iOS testing framework (in parent directory)
2. **Appium** - Cross-platform mobile automation (this directory)

## Prerequisites

### For XCUITests (already set up)
- Xcode
- iOS Simulator or physical device

### For Appium Tests
```bash
# Install Node.js dependencies
cd UITests/Appium
npm install

# Install Appium globally (if not already)
npm install -g appium

# Install Appium drivers
appium driver install xcuitest
appium driver install uiautomator2  # For Android
```

## Running Tests

### XCUITests (via Xcode)
```bash
cd iOS
open IPLFantasyPro.xcodeproj
# Product > Test (⌘U)
```

### XCUITests (via command line)
```bash
xcodebuild test \
  -scheme IPLFantasyPro \
  -destination 'platform=iOS Simulator,name=iPhone 15' \
  -derivedDataPath build
```

### Appium Tests

#### Start Appium Server
```bash
appium --allow-cors
```

#### Run Tests
```bash
# Install dependencies first
npm install

# Run all tests
npm test

# Run with visible browser
npm run test:headed

# Run iOS tests only
npm run test:ios

# Run Android tests only
npm run test:android

# Run on iOS Simulator
npm run test:simulator

# Run specific test file
npm run test:spec
```

## Test Coverage

### Authentication
- Login with valid credentials
- Login with invalid credentials
- Register new user
- Navigation between login/register

### Home Screen
- Display home content
- Scroll content
- Refresh content

### Leagues
- Navigate to leagues
- View league list
- Create new league
- Join league with code

### Draft Room
- Navigate to draft
- Display available players
- Place bid

### My Team
- Navigate to team
- View squad
- Set captain
- Set vice-captain

### Standings
- Navigate to standings
- View standings
- Filter by week

### Navigation
- Tab navigation
- Back navigation

### Performance
- App launch time
- Gesture response time

### Accessibility
- Accessibility labels
- Screen reader support

## Configuration

### Capabilities (caps.json)
Edit `caps.json` to configure:
- Device name
- Platform version
- App path
- Permissions

### Environment Variables
```bash
APPIUM_HOST=localhost      # Appium server host
APPIUM_PORT=4723           # Appium server port
PLATFORM=ios               # Target platform (ios/android)
TEST_ENV=local             # Test environment
APP_URL=http://localhost   # Backend URL
```

## CI/CD Integration

### GitHub Actions Example
```yaml
name: iOS E2E Tests

on: [push, pull_request]

jobs:
  e2e-tests:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Install dependencies
        run: |
          cd iOS/UITests/Appium
          npm install

      - name: Install Appium
        run: npm install -g appium

      - name: Run tests
        run: npm test
```

## Troubleshooting

### Appium Issues
```bash
# Check Appium version
appium --version

# Re-install drivers
appium driver uninstall xcuitest
appium driver install xcuitest

# Clear cached apps
rm -rf ~/.appium
```

### Simulator Issues
```bash
# Boot simulator
xcrun simctl boot "iPhone 15"

# Open simulator
open -a Simulator
```

### Xcode Issues
```bash
# Clean build
xcodebuild clean

# Reset simulator
xcrun simctl erase all
```
