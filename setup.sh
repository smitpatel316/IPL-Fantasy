#!/bin/bash
set -e

echo "========================================="
echo "  IPL Fantasy Pro - Production Setup"
echo "========================================="

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env from example..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your actual values!"
fi

# Build and start containers
echo ""
echo "Building Docker containers..."
docker-compose build

echo ""
echo "Starting services..."
docker-compose up -d

# Wait for database
echo ""
echo "Waiting for database..."
sleep 5

# Run migrations
echo ""
echo "Running database migrations..."
docker-compose exec api npm run db:migrate

# Seed data
echo ""
echo "Seeding initial data..."
docker-compose exec api npm run db:init

echo ""
echo "========================================="
echo "  Setup Complete! 🎉"
echo "========================================="
echo ""
echo "Services running:"
echo "  - API:        http://localhost:3001"
echo "  - PostgreSQL: localhost:5432"
echo "  - Redis:      localhost:6379"
echo ""
echo "API Health: http://localhost:3001/api/health"
echo ""
echo "To view logs: docker-compose logs -f"
echo "To stop:      docker-compose down"
