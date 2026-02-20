.PHONY: help install dev test build docker-up docker-down clean lint

help:
	@echo "IPL Fantasy Pro - Available Commands"
	@echo "===================================="
	@echo "make install    - Install dependencies"
	@echo "make dev       - Start development server"
	@echo "make test      - Run tests"
	@echo "make lint      - Run linter"
	@echo "make docker-up - Start Docker services"
	@echo "make docker-down - Stop Docker services"
	@echo "make clean     - Clean node_modules"
	@echo "make db-init   - Initialize database"
	@echo "make db-migrate - Run migrations"

install:
	cd backend && npm install
	cd iOS && pod install

dev:
	cd backend && npm run dev

test:
	cd backend && npm test

lint:
	cd backend && npm run lint

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

clean:
	rm -rf backend/node_modules
	rm -rf iOS/Pods
	rm -rf iOS/build

db-init:
	cd backend && npm run db:init

db-migrate:
	cd backend && npm run db:migrate

build:
	cd backend && npm run build
