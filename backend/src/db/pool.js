const { Pool } = require('pg');
const log = require('../middleware/logger');

class Database {
  constructor() {
    this.pool = null;
    this.isConnected = false;
  }

  initialize() {
    this.pool = new Pool({
      host: process.env.DB_HOST || 'localhost',
      port: parseInt(process.env.DB_PORT) || 5432,
      database: process.env.DB_NAME || 'ipl_fantasy',
      user: process.env.DB_USER || 'postgres',
      password: process.env.DB_PASSWORD || 'postgres',
      max: parseInt(process.env.DB_POOL_MAX) || 20,
      idleTimeoutMillis: 30000,
      connectionTimeoutMillis: 5000,
    });

    // Event handlers
    this.pool.on('connect', () => {
      this.isConnected = true;
      log.info('New database connection established');
    });

    this.pool.on('error', (err) => {
      log.error('Unexpected database error', { error: err.message });
      this.isConnected = false;
    });

    this.pool.on('remove', () => {
      log.debug('Database connection removed from pool');
    });

    return this;
  }

  // Health check
  async healthCheck() {
    try {
      const result = await this.pool.query('SELECT NOW()');
      return {
        status: 'healthy',
        timestamp: result.rows[0].now,
        poolSize: this.pool.totalCount,
        idleConnections: this.pool.idleCount,
        waitingClients: this.pool.waitingCount
      };
    } catch (error) {
      log.error('Database health check failed', { error: error.message });
      return {
        status: 'unhealthy',
        error: error.message
      };
    }
  }

  // Query with retry logic
  async query(text, params, retryCount = 3) {
    for (let attempt = 1; attempt <= retryCount; attempt++) {
      try {
        const start = Date.now();
        const result = await this.pool.query(text, params);
        const duration = Date.now() - start;
        
        log.debug('Query executed', {
          text: text.substring(0, 100),
          duration: `${duration}ms`,
          rows: result.rowCount
        });
        
        return result;
      } catch (error) {
        log.error('Query failed', {
          error: error.message,
          attempt,
          retryCount
        });
        
        if (attempt === retryCount) {
          throw error;
        }
        
        // Wait before retry (exponential backoff)
        await new Promise(resolve => setTimeout(resolve, 100 * Math.pow(2, attempt)));
      }
    }
  }

  // Transaction helper
  async transaction(callback) {
    const client = await this.pool.connect();
    
    try {
      await client.query('BEGIN');
      const result = await callback(client);
      await client.query('COMMIT');
      return result;
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  // Graceful shutdown
  async shutdown() {
    log.info('Shutting down database pool...');
    
    try {
      await this.pool.end();
      log.info('Database pool closed');
    } catch (error) {
      log.error('Error closing database pool', { error: error.message });
      throw error;
    }
  }
}

// Singleton instance
const database = new Database();

module.exports = database;
