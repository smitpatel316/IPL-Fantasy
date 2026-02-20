const pool = require('./pool');

const initDB = async () => {
  const client = await pool.connect();
  
  try {
    await client.query('BEGIN');

    // Users table
    await client.query(`
      CREATE TABLE IF NOT EXISTS users (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        email VARCHAR(255) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        display_name VARCHAR(100) NOT NULL,
        avatar_url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // Leagues table
    await client.query(`
      CREATE TABLE IF NOT EXISTS leagues (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name VARCHAR(100) NOT NULL,
        code VARCHAR(10) UNIQUE NOT NULL,
        commissioner_id UUID REFERENCES users(id),
        max_teams INTEGER DEFAULT 10,
        auction_budget DECIMAL(10,2) DEFAULT 100.00,
        status VARCHAR(20) DEFAULT 'open',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // League members table
    await client.query(`
      CREATE TABLE IF NOT EXISTS league_members (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        league_id UUID REFERENCES leagues(id) ON DELETE CASCADE,
        user_id UUID REFERENCES users(id) ON DELETE CASCADE,
        team_name VARCHAR(100) NOT NULL,
        budget_remaining DECIMAL(10,2) DEFAULT 100.00,
        is_commissioner BOOLEAN DEFAULT FALSE,
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(league_id, user_id)
      )
    `);

    // Players table (IPL player database)
    await client.query(`
      CREATE TABLE IF NOT EXISTS players (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name VARCHAR(100) NOT NULL,
        role VARCHAR(20) NOT NULL,
        team VARCHAR(10) NOT NULL,
        base_price DECIMAL(10,2) NOT NULL,
        image_url TEXT,
        is_overseas BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // Teams table (user's fantasy team)
    await client.query(`
      CREATE TABLE IF NOT EXISTS teams (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID REFERENCES users(id) ON DELETE CASCADE,
        league_id UUID REFERENCES leagues(id) ON DELETE CASCADE,
        name VARCHAR(100) NOT NULL,
        captain_id UUID,
        vice_captain_id UUID,
        total_points INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, league_id)
      )
    `);

    // Team players (junction table)
    await client.query(`
      CREATE TABLE IF NOT EXISTS team_players (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        team_id UUID REFERENCES teams(id) ON DELETE CASCADE,
        player_id UUID REFERENCES players(id),
        purchase_price DECIMAL(10,2) NOT NULL,
        is_playing BOOLEAN DEFAULT FALSE,
        is_captain BOOLEAN DEFAULT FALSE,
        is_vice_captain BOOLEAN DEFAULT FALSE,
        UNIQUE(team_id, player_id)
      )
    `);

    // Auction drafts table
    await client.query(`
      CREATE TABLE IF NOT EXISTS auction_drafts (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        league_id UUID REFERENCES leagues(id) ON DELETE CASCADE,
        status VARCHAR(20) DEFAULT 'pending',
        current_player_id UUID REFERENCES players(id),
        current_bid DECIMAL(10,2) DEFAULT 0,
        current_bidder_id UUID REFERENCES league_members(id),
        timer_seconds INTEGER DEFAULT 60,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // Auction bids table
    await client.query(`
      CREATE TABLE IF NOT EXISTS auction_bids (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        draft_id UUID REFERENCES auction_drafts(id) ON DELETE CASCADE,
        player_id UUID REFERENCES players(id),
        bidder_id UUID REFERENCES league_members(id),
        bid_amount DECIMAL(10,2) NOT NULL,
        is_winning BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // Matchups table
    await client.query(`
      CREATE TABLE IF NOT EXISTS matchups (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        league_id UUID REFERENCES leagues(id) ON DELETE CASCADE,
        week INTEGER NOT NULL,
        home_team_id UUID REFERENCES teams(id),
        away_team_id UUID REFERENCES teams(id),
        home_points INTEGER DEFAULT 0,
        away_points INTEGER DEFAULT 0,
        home_wins INTEGER DEFAULT 0,
        away_wins INTEGER DEFAULT 0,
        is_completed BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // Weekly scores table
    await client.query(`
      CREATE TABLE IF NOT EXISTS weekly_scores (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        team_id UUID REFERENCES teams(id) ON DELETE CASCADE,
        matchup_id UUID REFERENCES matchups(id) ON DELETE CASCADE,
        week INTEGER NOT NULL,
        points INTEGER DEFAULT 0,
        category_wins INTEGER DEFAULT 0,
        category_losses INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // Player points (real-time scoring)
    await client.query(`
      CREATE TABLE IF NOT EXISTS player_points (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        player_id UUID REFERENCES players(id),
        match_id VARCHAR(50),
        points INTEGER DEFAULT 0,
        runs INTEGER DEFAULT 0,
        wickets INTEGER DEFAULT 0,
        catches INTEGER DEFAULT 0,
        strike_rate DECIMAL(10,2),
        economy DECIMAL(10,2),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

    await client.query('COMMIT');
    console.log('Database tables created successfully!');
    
  } catch (error) {
    await client.query('ROLLBACK');
    console.error('Error initializing database:', error);
    throw error;
  } finally {
    client.release();
  }
};

// Seed initial players
const seedPlayers = async () => {
  const players = [
    // Mumbai Indians
    { name: 'Rohit Sharma', role: 'batsman', team: 'MI', base_price: 18.0 },
    { name: 'Jasprit Bumrah', role: 'bowler', team: 'MI', base_price: 18.0 },
    { name: 'Hardik Pandya', role: 'allrounder', team: 'MI', base_price: 16.0 },
    { name: 'Suryakumar Yadav', role: 'batsman', team: 'MI', base_price: 14.0 },
    { name: 'Ishan Kishan', role: 'wicketkeeper', team: 'MI', base_price: 12.0 },
    { name: 'Tilak Varma', role: 'batsman', team: 'MI', base_price: 8.0 },
    
    // Chennai Super Kings
    { name: 'MS Dhoni', role: 'wicketkeeper', team: 'CSK', base_price: 12.0 },
    { name: 'Ruturaj Gaikwad', role: 'batsman', team: 'CSK', base_price: 12.0 },
    { name: 'Ravindra Jadeja', role: 'allrounder', team: 'CSK', base_price: 14.0 },
    { name: 'Deepak Chahar', role: 'bowler', team: 'CSK', base_price: 8.0 },
    
    // Royal Challengers Bangalore
    { name: 'Virat Kohli', role: 'batsman', team: 'RCB', base_price: 18.0 },
    { name: 'Faf du Plessis', role: 'batsman', team: 'RCB', base_price: 12.0 },
    { name: 'Mohammed Siraj', role: 'bowler', team: 'RCB', base_price: 10.0 },
    { name: 'Glenn Maxwell', role: 'allrounder', team: 'RCB', base_price: 12.0, is_overseas: true },
    
    // Kolkata Knight Riders
    { name: 'Shreyas Iyer', role: 'batsman', team: 'KKR', base_price: 12.0 },
    { name: 'Andre Russell', role: 'allrounder', team: 'KKR', base_price: 12.0, is_overseas: true },
    { name: 'Sunil Narine', role: 'allrounder', team: 'KKR', base_price: 10.0, is_overseas: true },
    
    // Delhi Capitals
    { name: 'Rishabh Pant', role: 'wicketkeeper', team: 'DC', base_price: 14.0 },
    { name: 'David Warner', role: 'batsman', team: 'DC', base_price: 12.0, is_overseas: true },
    { name: 'Axar Patel', role: 'allrounder', team: 'DC', base_price: 10.0 },
    { name: 'Kuldeep Yadav', role: 'bowler', team: 'DC', base_price: 10.0 },
    
    // Lucknow Super Giants
    { name: 'KL Rahul', role: 'wicketkeeper', team: 'LSG', base_price: 14.0 },
    { name: 'Mohammed Shami', role: 'bowler', team: 'LSG', base_price: 14.0 },
    { name: 'Nicholas Pooran', role: 'batsman', team: 'LSG', base_price: 10.0, is_overseas: true },
    
    // Gujarat Titans
    { name: 'Shubman Gill', role: 'batsman', team: 'GT', base_price: 16.0 },
    { name: 'Rashid Khan', role: 'bowler', team: 'GT', base_price: 14.0, is_overseas: true },
    { name: 'Hardik Pandya', role: 'allrounder', team: 'GT', base_price: 16.0 },
    
    // Rajasthan Royals
    { name: 'Sanju Samson', role: 'wicketkeeper', team: 'RR', base_price: 10.0 },
    { name: 'Yashasvi Jaiswal', role: 'batsman', team: 'RR', base_price: 10.0 },
    { name: 'Ravichandran Ashwin', role: 'allrounder', team: 'RR', base_price: 12.0 },
    { name: 'Yuzvendra Chahal', role: 'bowler', team: 'RR', base_price: 10.0 },
    
    // Sunrisers Hyderabad
    { name: 'Aiden Markram', role: 'batsman', team: 'SRH', base_price: 10.0, is_overseas: true },
    { name: 'Bhuvneshwar Kumar', role: 'bowler', team: 'SRH', base_price: 12.0 },
    { name: 'T Natarajan', role: 'bowler', team: 'SRH', base_price: 8.0 },
  ];

  for (const player of players) {
    await pool.query(
      `INSERT INTO players (name, role, team, base_price, is_overseas) 
       VALUES ($1, $2, $3, $4, $5) 
       ON CONFLICT DO NOTHING`,
      [player.name, player.role, player.team, player.base_price, player.is_overseas || false]
    );
  }
  
  console.log('Player database seeded!');
};

initDB()
  .then(() => seedPlayers())
  .then(() => process.exit(0))
  .catch((err) => {
    console.error('Failed to initialize database:', err);
    process.exit(1);
  });
