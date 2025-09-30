# Makefile for Privy Fraud Detection API
# Common development and deployment commands

.PHONY: help install dev test lint format build docker-build docker-up docker-down migrate seed clean

# Default target
help:
	@echo "Privy Fraud Detection API - Available Commands:"
	@echo ""
	@echo "🚀 Development:"
	@echo "  make install     - Install dependencies"
	@echo "  make dev         - Start development server"
	@echo "  make test        - Run tests"
	@echo "  make lint        - Run code linting"
	@echo "  make format      - Format code"
	@echo ""
	@echo "🐳 Docker:"
	@echo "  make docker-build - Build Docker images"
	@echo "  make docker-up    - Start Docker services"
	@echo "  make docker-down  - Stop Docker services"
	@echo ""
	@echo "🗄️  Database:"
	@echo "  make migrate      - Run database migrations"
	@echo "  make migration    - Create new migration"
	@echo "  make seed         - Seed database with test data"
	@echo ""
	@echo "🔑 API Management:"
	@echo "  make create-key   - Create new API key"
	@echo "  make test-api     - Test API connectivity"
	@echo ""
	@echo "🧹 Maintenance:"
	@echo "  make clean        - Clean temporary files"

# Development setup
install:
	pip install -r requirements.txt

# Development server
dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Testing
test:
	pytest tests/ -v

test-cov:
	pytest tests/ --cov=app --cov-report=html --cov-report=term-missing

# Code quality
lint:
	flake8 app/ tests/
	mypy app/

format:
	black app/ tests/
	isort app/ tests/

# Docker commands
docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

# Database management
migrate:
	alembic upgrade head

migration:
	@read -p "Migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"

seed:
	python cli.py seed-data --type disposable-emails

# API management
create-key:
	@read -p "Organization name: " org; \
	read -p "Key name (optional): " key; \
	python cli.py create-api-key --org-name "$$org" --key-name "$$key"

test-api:
	python cli.py test-api

# Maintenance
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/

# Production deployment
deploy-prod:
	@echo "🚀 Deploying to production..."
	docker-compose -f docker-compose.prod.yml up -d --build

# Development helpers
shell:
	python -c "import asyncio; from app.db import get_session; print('Database shell ready')"

worker:
	celery -A app.workers.celery_app.celery_app worker --loglevel=info

beat:
	celery -A app.workers.celery_app.celery_app beat --loglevel=info

# Backup and restore
backup-db:
	@echo "Creating database backup..."
	# Add your backup command here

restore-db:
	@echo "Restoring database from backup..."
	# Add your restore command here