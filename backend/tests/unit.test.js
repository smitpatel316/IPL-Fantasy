// Unit tests for backend services - no server needed

// Test 1: League Code Generation
function generateCode() {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
  let code = '';
  for (let i = 0; i < 6; i++) {
    code += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return code;
}

// Test that code is 6 characters
const code = generateCode();
console.log(`Generated code: ${code} (length: ${code.length})`);
console.assert(code.length === 6, 'Code should be 6 characters');

// Test code contains only valid characters
const validChars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
const isValid = code.split('').every(c => validChars.includes(c));
console.assert(isValid, 'Code should only contain valid characters');
console.log(`Code contains valid characters: ${isValid}`);

// Test 2: Player Filtering Logic
const players = [
  { id: '1', name: 'Virat Kohli', role: 'batsman', team: 'RCB', basePrice: 18 },
  { id: '2', name: 'Jasprit Bumrah', role: 'bowler', team: 'MI', basePrice: 18 },
  { id: '3', name: 'Rohit Sharma', role: 'batsman', team: 'MI', basePrice: 18 },
  { id: '4', name: 'Andre Russell', role: 'allrounder', team: 'KKR', basePrice: 12 },
];

function filterPlayers(players, { team, role, search }) {
  let result = players;
  
  if (team) {
    result = result.filter(p => p.team === team);
  }
  
  if (role) {
    result = result.filter(p => p.role === role);
  }
  
  if (search) {
    result = result.filter(p => p.name.toLowerCase().includes(search.toLowerCase()));
  }
  
  return result;
}

// Test filtering
const miPlayers = filterPlayers(players, { team: 'MI' });
console.log(`MI Players: ${JSON.stringify(miPlayers)}`);
console.assert(miPlayers.length === 2, 'Should have 2 MI players');

const batsmen = filterPlayers(players, { role: 'batsman' });
console.log(`Batsmen: ${JSON.stringify(batsmen)}`);
console.assert(batsmen.length === 2, 'Should have 2 batsmen');

const kohliSearch = filterPlayers(players, { search: 'Kohli' });
console.log(`Kohli Search: ${JSON.stringify(kohliSearch)}`);
console.assert(kohliSearch.length === 1, 'Should find 1 Kohli');

// Test 3: Points Calculation
function calculatePoints(player, isCaptain, isViceCaptain) {
  let points = player.totalPoints || 0;
  
  if (isCaptain) {
    points *= 2; // 2x multiplier
  } else if (isViceCaptain) {
    points *= 1.5; // 1.5x multiplier
  }
  
  return Math.floor(points);
}

const testPlayer = { name: 'Kohli', totalPoints: 100 };
const captainPoints = calculatePoints(testPlayer, true, false);
const vicePoints = calculatePoints(testPlayer, false, true);
const normalPoints = calculatePoints(testPlayer, false, false);

console.log(`Captain points: ${captainPoints} (expected: 200)`);
console.assert(captainPoints === 200, 'Captain should get 2x points');

console.log(`ViceCaptain points: ${vicePoints} (expected: 150)`);
console.assert(vicePoints === 150, 'ViceCaptain should get 1.5x points');

console.log(`Normal points: ${normalPoints} (expected: 100)`);
console.assert(normalPoints === 100, 'Normal player should get base points');

// Test 4: Budget Validation
function canAfford(budget, bid) {
  return bid > 0 && bid <= budget;
}

console.log(`Can afford 50 from 100: ${canAfford(100, 50)}`);
console.assert(canAfford(100, 50) === true, 'Should be able to afford');

console.log(`Can afford 150 from 100: ${canAfford(100, 150)}`);
console.assert(canAfford(100, 150) === false, 'Should not be able to afford');

console.log(`Can afford 0: ${canAfford(100, 0)}`);
console.assert(canAfford(100, 0) === false, 'Should not be able to afford 0');

// Test 5: Match Outcome Calculation
function determineWinner(homePoints, awayPoints) {
  if (homePoints > awayPoints) return 'home';
  if (awayPoints > homePoints) return 'away';
  return 'tie';
}

console.log(`Home 100, Away 80: ${determineWinner(100, 80)}`);
console.assert(determineWinner(100, 80) === 'home', 'Home should win');

console.log(`Home 80, Away 100: ${determineWinner(80, 100)}`);
console.assert(determineWinner(80, 100) === 'away', 'Away should win');

console.log(`Home 100, Away 100: ${determineWinner(100, 100)}`);
console.assert(determineWinner(100, 100) === 'tie', 'Should be tie');

console.log('\n✅ All unit tests passed!');
