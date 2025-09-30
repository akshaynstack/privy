# Ubuntu 22.04 Setup Guide for Privy Fraud Detection API

## 🐧 System Requirements
- Ubuntu 22.04 LTS
- Python 3.11+ (recommended) or Python 3.10+
- PostgreSQL 14+
- Redis 6+

## 📦 Install System Dependencies

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Python and development tools
sudo apt install -y python3 python3-pip python3-venv python3-dev

# Install PostgreSQL
sudo apt install -y postgresql postgresql-contrib libpq-dev

# Install Redis
sudo apt install -y redis-server

# Install additional build tools
sudo apt install -y build-essential git curl
```

## 🗄️ Setup PostgreSQL

```bash
# Start PostgreSQL service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
sudo -u postgres psql -c "CREATE USER privy WITH PASSWORD 'shNKzrWFzE2N5kbG';"
sudo -u postgres psql -c "CREATE DATABASE privy OWNER privy;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE privy TO privy;"

# Test connection
psql -h localhost -U privy -d privy -c "SELECT version();"
```

## 🔴 Setup Redis with Password

```bash
# Edit Redis configuration
sudo nano /etc/redis/redis.conf

# Add/uncomment these lines:
# requirepass pC2bM7fpj6C4Tpsf
# bind 127.0.0.1 ::1

# Restart Redis
sudo systemctl restart redis-server
sudo systemctl enable redis-server

# Test Redis connection
redis-cli -a pC2bM7fpj6C4Tpsf ping
```

## 🚀 Setup Privy API

```bash
# Clone your project (or copy files)
cd /home/$USER
mkdir -p projects
cd projects
# Copy your backend folder here

cd backend

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Initialize database
python cli.py init-db

# Create initial migration (if needed)
alembic revision --autogenerate -m "Initial tables"
alembic upgrade head

# Create your first API key
python cli.py create-api-key --org-name "Development Org" --key-name "Dev Key"
```

## 🔧 Environment Configuration

Your `.env` file is already configured for localhost services:

```bash
# PostgreSQL on localhost
DATABASE_URL=postgresql+asyncpg://privy:shNKzrWFzE2N5kbG@localhost:5432/privy
DATABASE_URL_SYNC=postgresql+psycopg://privy:shNKzrWFzE2N5kbG@localhost:5432/privy

# Redis on localhost with password
REDIS_URL=redis://:pC2bM7fpj6C4Tpsf@localhost:6379
CELERY_BROKER=redis://:pC2bM7fpj6C4Tpsf@localhost:6379/0
CELERY_BACKEND=redis://:pC2bM7fpj6C4Tpsf@localhost:6379/1
```

## 🏃‍♂️ Running the Application

### Terminal 1: Start API Server
```bash
cd /path/to/backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Terminal 2: Start Celery Worker (optional)
```bash
cd /path/to/backend
source .venv/bin/activate
celery -A app.workers.celery_app.celery_app worker --loglevel=info
```

### Terminal 3: Start Celery Beat (optional)
```bash
cd /path/to/backend
source .venv/bin/activate
celery -A app.workers.celery_app.celery_app beat --loglevel=info
```

## 🧪 Test the Setup

```bash
# Test API health
curl http://localhost:8000/health

# Test with API key (after creating one)
curl -X POST "http://localhost:8000/v1/check" \
  -H "X-API-Key: your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@tempmail.com", "ip": "1.2.3.4"}'
```

## 🐳 Alternative: Docker Setup

If you prefer Docker on Ubuntu:

```bash
# Install Docker
sudo apt install -y docker.io docker-compose
sudo usermod -aG docker $USER
# Log out and back in

# Start with Docker
docker-compose up --build
```

## 🛠️ Useful Commands

```bash
# Check service status
sudo systemctl status postgresql
sudo systemctl status redis-server

# View logs
sudo journalctl -u postgresql
sudo journalctl -u redis-server

# Connect to PostgreSQL
psql -h localhost -U privy -d privy

# Connect to Redis
redis-cli -a pC2bM7fpj6C4Tpsf

# Run tests
pytest tests/ -v

# Create API key
python cli.py create-api-key --org-name "My Org"

# Check API status
python cli.py test-api
```

## 🔧 Troubleshooting

### PostgreSQL Connection Issues
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Check PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-*.log
```

### Redis Connection Issues
```bash
# Check Redis status
sudo systemctl status redis-server

# Test Redis manually
redis-cli -a pC2bM7fpj6C4Tpsf ping
```

### Python Package Issues
```bash
# If psycopg installation fails
sudo apt install -y libpq-dev python3-dev

# If other build issues
sudo apt install -y build-essential
```

## 🎯 Benefits of Ubuntu Setup

✅ **Better Python Package Support** - Native compilation works smoothly  
✅ **Easier PostgreSQL Setup** - Package manager handles everything  
✅ **Redis Integration** - Simple configuration and management  
✅ **Performance** - Native Linux performance for async operations  
✅ **Production-Ready** - Same environment as typical deployment targets  
✅ **Docker Support** - Better Docker experience on Linux  

Your project will run much more smoothly on Ubuntu! 🚀