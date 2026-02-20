const pool = require('./pool');

// Migration runner
const migrate = async () => {
  const client = await pool.connect();
  
  try {
    await client.query('BEGIN');
    
    // Create migrations tracking table
    await client.query(`
      CREATE TABLE IF NOT EXISTS migrations (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL UNIQUE,
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);
    
    // Track applied migrations
    const appliedMigrations = new Set();
    const result = await client.query('SELECT name FROM migrations');
    result.rows.forEach(row => appliedMigrations.add(row.name));
    
    // Migration: Add refresh token support
    if (!appliedMigrations.has('add_refresh_tokens')) {
      await client.query(`
        ALTER TABLE users ADD COLUMN IF NOT EXISTS refresh_token TEXT;
        ALTER TABLE users ADD COLUMN IF NOT EXISTS refresh_token_expires TIMESTAMP;
        INSERT INTO migrations (name) VALUES ('add_refresh_tokens');
        console.log('Applied: add_refresh_tokens');
      }
    }
    
    // Migration: Add player stats
    if (!appliedMigrations.has('add_player_stats')) {
      await client.query(`
        CREATE TABLE IF NOT EXISTS player_season_stats (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          player_id UUID REFERENCES players(id),
          season VARCHAR(10) NOT NULL,
          matches INTEGER DEFAULT 0,
          runs INTEGER DEFAULT 0,
          wickets INTEGER DEFAULT 0,
          catches INTEGER DEFAULT 0,
          avg_score DECIMAL(10,2),
          strike_rate DECIMAL(10,2),
          economy DECIMAL(10,2),
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(player_id, season)
        );
        INSERT INTO migrations (name) VALUES ('add_player_stats');
        console.log('Applied: add_player_stats');
      }
    }
    
    // Migration: Add live scores cache
    if (!appliedMigrations.has('add_live_scores')) {
      await client.query(`
        CREATE TABLE IF NOT EXISTS live_scores_cache (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          match_id VARCHAR(50) UNIQUE NOT NULL,
          data JSONB NOT NULL,
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX idx_live_scores_match ON live_scores_cache(match_id);
        INSERT INTO migrations (name) VALUES ('add_live_scores');
        console.log('Applied: add_live_scores');
      }
    }
    
    // Migration: Add user preferences
    if (!appliedMigrations.has('add_user_preferences')) {
      await client.query(`
        CREATE TABLE IF NOT EXISTS user_preferences (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id UUID REFERENCES users(id) UNIQUE,
          notifications_enabled BOOLEAN DEFAULT TRUE,
          dark_mode BOOLEAN DEFAULT TRUE,
          language VARCHAR(10) DEFAULT 'en',
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        INSERT INTO migrations (name) VALUES ('add_user_preferences');
        console.log('Applied: add_user_preferences');
      }
    }
    
    // Migration: Add audit log
    if (!appliedMigrations.has('add_audit_log')) {
      await client.query(`
        CREATE TABLE IF NOT EXISTS audit_log (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id UUID REFERENCES users(id),
          action VARCHAR(50) NOT NULL,
          entity_type VARCHAR(50),
          entity_id UUID,
          details JSONB,
          ip_address VARCHAR(45),
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX idx_audit_user ON audit_log(user_id);
        CREATE INDEX idx_audit_action ON audit_log(action);
        CREATE INDEX idx_audit_created ON audit_log(created_at);
        INSERT INTO migrations (name) VALUES ('add_audit_log');
        console.log('Applied: add_audit_log');
      }
    }
    
    await client.query('COMMIT');
    console.log('All migrations applied successfully!');
    
  } catch (error) {
    await client.query('ROLLBACK');
    console.error('Migration error:', error);
    throw error;
  } finally {
    client.release();
  }
};

// Run migrations
migrate()
  .then(() => process.exit(0))
  .catch((err) => {
    console.error('Migration failed:', err);
    process.exit(1);
  });
