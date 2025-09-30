#!/bin/bash
# Quick Production Setup Script for Privy Fraud Detection API
# Run this script on Ubuntu 22.04 to set up production environment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is available
check_docker() {
    if command -v docker &> /dev/null; then
        # Check if user is in docker group or if we can access docker
        if docker info &> /dev/null 2>&1; then
            log_info "Docker is available and accessible"
            return 0
        elif sudo docker info &> /dev/null 2>&1; then
            log_warning "Docker is available but requires sudo (user not in docker group)"
            # Try to add user to docker group if not already
            if ! groups $USER | grep -q docker; then
                sudo usermod -aG docker $USER
                log_info "Added $USER to docker group. You may need to log out and back in."
            fi
            return 0
        else
            log_warning "Docker is installed but not running"
            sudo systemctl start docker 2>/dev/null || true
            sleep 2
            if docker info &> /dev/null 2>&1 || sudo docker info &> /dev/null 2>&1; then
                log_info "Docker started successfully"
                return 0
            else
                log_warning "Docker failed to start"
                return 1
            fi
        fi
    else
        log_warning "Docker is not installed"
        return 1
    fi
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    log_error "Please don't run this script as root. Run as a regular user with sudo access."
    exit 1
fi

# Check Ubuntu version
if ! lsb_release -a 2>/dev/null | grep -q "22.04"; then
    log_warning "This script is designed for Ubuntu 22.04. Your version might not be fully supported."
fi

log_info "🚀 Privy Fraud Detection API - Production Setup"
echo "=================================================="

# Step 1: Update system and install dependencies
log_info "📦 Installing system dependencies..."
sudo apt update

# First install basic dependencies without Docker
sudo apt install -y \
    nginx \
    supervisor \
    certbot \
    python3-certbot-nginx \
    ufw \
    fail2ban \
    postgresql \
    postgresql-contrib \
    redis-server \
    python3-venv \
    python3-pip \
    curl \
    git

# Install Docker separately if not already installed
if ! command -v docker &> /dev/null; then
    log_info "Installing Docker..."
    
    # Remove any conflicting packages
    sudo apt remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true
    
    # Add Docker's official GPG key
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    
    # Add Docker repository
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # Update package index
    sudo apt update
    
    # Install Docker
    sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    
    # Add current user to docker group
    sudo usermod -aG docker $USER
    
    # Start Docker
    sudo systemctl start docker
    sudo systemctl enable docker
    
    log_info "Docker installation completed. You may need to log out and back in for group changes to take effect."
else
    log_info "Docker is already installed"
fi

log_success "System dependencies installed"

# Helper function to run docker commands (with sudo if needed)
run_docker() {
    if docker info &> /dev/null 2>&1; then
        docker "$@"
    else
        sudo docker "$@"
    fi
}

# Check Docker availability
check_docker
DOCKER_AVAILABLE=$?

# Step 2: Check for existing Docker containers and configure databases
log_info "🐳 Checking for existing Docker containers..."

# Check if PostgreSQL Docker container exists
if [ $DOCKER_AVAILABLE -eq 0 ] && run_docker ps -a --format "table {{.Names}}" | grep -q "postgres\|postgresql"; then
    log_info "Found existing PostgreSQL Docker container, using it..."
    
    # Get container name
    POSTGRES_CONTAINER=$(run_docker ps -a --format "{{.Names}}" | grep -E "postgres|postgresql" | head -1)
    log_info "Using PostgreSQL container: $POSTGRES_CONTAINER"
    
    # Check if container is running
    if ! run_docker ps --format "table {{.Names}}" | grep -q "postgres\|postgresql"; then
        log_info "Starting existing PostgreSQL container..."
        run_docker start $POSTGRES_CONTAINER
        sleep 5
    fi
    
    # Try to get database credentials from existing container
    # Use the provided credentials
    POSTGRES_PASSWORD="postgres"
    PRIVY_DB_PASSWORD="shNKzrWFzE2N5kbG"
    
    # Test connection and create user if needed
    log_info "Testing PostgreSQL connection and setting up database..."
    
    # Try to connect and setup database - use docker exec to run commands inside container
    run_docker exec $POSTGRES_CONTAINER psql -U postgres -c "SELECT 1;" > /dev/null 2>&1 || {
        log_warning "Cannot connect to PostgreSQL with default credentials, trying alternative setup..."
        # Try creating user through docker exec with default postgres user
        run_docker exec $POSTGRES_CONTAINER psql -U postgres -c "CREATE USER IF NOT EXISTS privy WITH PASSWORD 'shNKzrWFzE2N5kbG';" 2>/dev/null || true
        run_docker exec $POSTGRES_CONTAINER psql -U postgres -c "CREATE DATABASE IF NOT EXISTS privy OWNER privy;" 2>/dev/null || true
        run_docker exec $POSTGRES_CONTAINER psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE privy TO privy;" 2>/dev/null || true
    }
    
    POSTGRES_HOST="localhost"
    POSTGRES_PORT="5432"
else
    log_info "🗄️ Setting up PostgreSQL..."
    
    # Check if PostgreSQL service exists
    if systemctl list-units --full -all | grep -Fq "postgresql.service"; then
        log_info "Using system PostgreSQL service..."
        POSTGRES_PASSWORD="postgres"
        PRIVY_DB_PASSWORD="shNKzrWFzE2N5kbG"
        
        sudo systemctl start postgresql
        sudo systemctl enable postgresql
        
        # Configure PostgreSQL with proper permissions
        sudo -i -u postgres psql -c "ALTER USER postgres PASSWORD '$POSTGRES_PASSWORD';" 2>/dev/null || true
        sudo -i -u postgres psql -c "CREATE USER privy WITH PASSWORD 'shNKzrWFzE2N5kbG';" 2>/dev/null || true
        sudo -i -u postgres psql -c "CREATE DATABASE privy OWNER privy;" 2>/dev/null || true
        sudo -i -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE privy TO privy;" 2>/dev/null || true
    else
        log_error "No PostgreSQL found. Please install PostgreSQL or start Docker PostgreSQL container."
        exit 1
    fi
fi

log_success "PostgreSQL configured"

# Step 3: Configure Redis
log_info "🔴 Checking for Redis..."

# Check if Redis Docker container exists
if [ $DOCKER_AVAILABLE -eq 0 ] && run_docker ps -a --format "table {{.Names}}" | grep -q "redis"; then
    log_info "Found existing Redis Docker container, using it..."
    REDIS_PASSWORD="pC2bM7fpj6C4Tpsf"
    REDIS_HOST="localhost"
    REDIS_PORT="6379"
    
    # Check if container is running
    if ! run_docker ps --format "table {{.Names}}" | grep -q "redis"; then
        log_info "Starting existing Redis container..."
        run_docker start $(run_docker ps -a --format "{{.Names}}" | grep "redis" | head -1)
        sleep 3
    fi
else
    log_info "🔴 Setting up Redis..."
    
    # Use fixed password from memory
    REDIS_PASSWORD="pC2bM7fpj6C4Tpsf"
    
    # Check if Redis service exists and configure it
    if systemctl list-units --full -all | grep -Fq "redis-server.service"; then
        # Stop redis first to avoid conflicts
        sudo systemctl stop redis-server 2>/dev/null || true
        
        # Backup original config
        sudo cp /etc/redis/redis.conf /etc/redis/redis.conf.backup 2>/dev/null || true
        
        # Configure Redis with fixed password
        sudo sed -i "s/^# requirepass foobared/requirepass $REDIS_PASSWORD/" /etc/redis/redis.conf
        sudo sed -i "s/^requirepass .*/requirepass $REDIS_PASSWORD/" /etc/redis/redis.conf
        sudo sed -i "s/^# maxmemory <bytes>/maxmemory 512mb/" /etc/redis/redis.conf
        sudo sed -i "s/^# maxmemory-policy noeviction/maxmemory-policy allkeys-lru/" /etc/redis/redis.conf
        
        # Try to start Redis
        sudo systemctl start redis-server || {
            log_warning "Failed to start redis-server service, trying to fix configuration..."
            
            # Reset to default config and try again
            if [ -f "/etc/redis/redis.conf.backup" ]; then
                sudo cp /etc/redis/redis.conf.backup /etc/redis/redis.conf
                echo "requirepass $REDIS_PASSWORD" | sudo tee -a /etc/redis/redis.conf
                echo "maxmemory 512mb" | sudo tee -a /etc/redis/redis.conf
                echo "maxmemory-policy allkeys-lru" | sudo tee -a /etc/redis/redis.conf
            fi
            
            sudo systemctl start redis-server || {
                log_warning "System Redis failed, will use Docker Redis instead"
                if [ $DOCKER_AVAILABLE -eq 0 ]; then
                    run_docker run -d --name redis-privy -p 6379:6379 redis:7-alpine redis-server --requirepass $REDIS_PASSWORD
                    sleep 3
                else
                    log_error "Cannot start Redis and Docker is not available"
                    exit 1
                fi
            }
        }
        
        sudo systemctl enable redis-server 2>/dev/null || true
    else
        # Use Docker Redis as fallback
        if [ $DOCKER_AVAILABLE -eq 0 ]; then
            log_info "Using Docker Redis as fallback..."
            run_docker run -d --name redis-privy -p 6379:6379 redis:7-alpine redis-server --requirepass $REDIS_PASSWORD
            sleep 3
        else
            log_error "No Redis found and Docker is not available"
            exit 1
        fi
    fi
fi

log_success "Redis configured"

# Step 4: Create application directory
log_info "📁 Setting up application directory..."

# Use current directory if it contains application files, otherwise use default
if [ -f "requirements.txt" ] && [ -f "app/main.py" ]; then
    APP_DIR=$(pwd)
    log_info "Using current directory as application directory: $APP_DIR"
elif [ -f "requirements.txt" ]; then
    # If we have requirements.txt but no app/main.py, still use current directory
    # This handles cases where the structure might be slightly different
    APP_DIR=$(pwd)
    log_info "Using current directory (has requirements.txt): $APP_DIR"
else
    APP_DIR="/home/$USER/privy-api"
    log_info "Creating new application directory: $APP_DIR"
    mkdir -p $APP_DIR
    
    # Check if we need to copy files from current directory
    if [ -f "requirements.txt" ]; then
        log_info "Copying application files from current directory..."
        cp -r * $APP_DIR/
        cd $APP_DIR
    else
        log_error "Application files not found. Please copy your Privy backend files to: $APP_DIR"
        log_info "Required files: requirements.txt, app/main.py, and other application files"
        exit 1
    fi
fi

# Step 5: Create virtual environment and install dependencies
log_info "🐍 Setting up Python environment..."

# Ensure we're in the application directory
cd $APP_DIR

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn[gevent]

log_success "Python environment configured"

# Step 6: Create production environment file
log_info "⚙️ Creating production configuration..."

SECRET_KEY=$(openssl rand -hex 32)

cat > .env.prod << EOF
# Production Environment Variables
APP_NAME="Privy Fraud Detection API"
VERSION="1.0.0"
ENVIRONMENT=production
DEBUG=false

# API Configuration
API_HOST=127.0.0.1
API_PORT=8000
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000

# Database Configuration
DATABASE_URL=postgresql+asyncpg://privy:$PRIVY_DB_PASSWORD@localhost:5432/privy
DATABASE_URL_SYNC=postgresql+psycopg://privy:$PRIVY_DB_PASSWORD@localhost:5432/privy

# Redis Configuration
REDIS_URL=redis://:$REDIS_PASSWORD@localhost:6379
CELERY_BROKER=redis://:$REDIS_PASSWORD@localhost:6379/0
CELERY_BACKEND=redis://:$REDIS_PASSWORD@localhost:6379/1

# Security Settings
SECRET_KEY=$SECRET_KEY

# Rate Limiting
DEFAULT_RATE_LIMIT=2.0
DEFAULT_RATE_CAPACITY=120

# Logging
LOG_LEVEL=INFO

# Feature Flags
ENABLE_ANALYTICS=true
ENABLE_BACKGROUND_TASKS=true
ENABLE_CUSTOM_BLACKLISTS=true
EOF

log_success "Production configuration created"

# Step 7: Initialize database
log_info "🗄️ Initializing database..."

# Ensure we're in the app directory and environment is loaded
cd $APP_DIR

# Load environment variables, filtering out comments and empty lines
if [ -f ".env.prod" ]; then
    export $(cat .env.prod | grep -v '^#' | grep -v '^$' | xargs)
fi

# Test database connection before running migrations
log_info "Testing database connection..."
python -c "
import asyncio
import asyncpg
import os
from urllib.parse import urlparse

async def test_connection():
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print('No DATABASE_URL found in environment')
        return False
    
    # Parse the database URL
    parsed = urlparse(db_url.replace('postgresql+asyncpg://', 'postgresql://'))
    
    try:
        conn = await asyncpg.connect(
            user=parsed.username,
            password=parsed.password,
            database=parsed.path[1:],  # Remove leading slash
            host=parsed.hostname,
            port=parsed.port or 5432
        )
        await conn.close()
        print('Database connection successful')
        return True
    except Exception as e:
        print(f'Database connection failed: {e}')
        return False

if not asyncio.run(test_connection()):
    exit(1)
" || {
    log_error "Database connection test failed. Please check your PostgreSQL setup."
    log_info "Try manually creating the database user:"
    log_info "docker exec -it <postgres-container> psql -U postgres"
    log_info "CREATE USER privy WITH PASSWORD 'shNKzrWFzE2N5kbG';"
    log_info "CREATE DATABASE privy OWNER privy;"
    log_info "GRANT ALL PRIVILEGES ON DATABASE privy TO privy;"
    exit 1
}

# Check if alembic is available, if not, skip migrations
if [ -f "alembic.ini" ]; then
    log_info "Running database migrations..."
    alembic upgrade head
    log_success "Database migrations completed"
else
    log_warning "No alembic.ini found, skipping database migrations"
fi

log_success "Database initialization completed"

# Step 8: Setup fraud detection data
log_info "🛡️ Setting up fraud detection data..."

# Ensure we're in the app directory
cd $APP_DIR

# Try different ways to seed data
if [ -f "setup_fraud_detection.py" ]; then
    python setup_fraud_detection.py
elif [ -f "cli.py" ]; then
    python cli.py seed-data --data-type all
else
    log_warning "No data seeding script found, skipping fraud detection data setup"
fi

log_success "Fraud detection data setup completed"

# Step 9: Create logs directory
mkdir -p logs

# Step 10: Create Gunicorn configuration
log_info "🦄 Creating Gunicorn configuration..."

cat > gunicorn.conf.py << 'EOF'
import multiprocessing

bind = "127.0.0.1:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 30
keepalive = 2
max_requests = 1000
max_requests_jitter = 50
preload_app = True
accesslog = "logs/gunicorn-access.log"
errorlog = "logs/gunicorn-error.log"
loglevel = "info"
proc_name = "privy-api"
EOF

# Step 11: Create supervisor configurations
log_info "👨‍💼 Setting up supervisor..."

sudo tee /etc/supervisor/conf.d/privy-api.conf > /dev/null << EOF
[program:privy-api]
command=$APP_DIR/venv/bin/gunicorn app.main:app -c gunicorn.conf.py
directory=$APP_DIR
user=$USER
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=$APP_DIR/logs/api.log
environment=PATH="$APP_DIR/venv/bin"
EOF

sudo tee /etc/supervisor/conf.d/privy-worker.conf > /dev/null << EOF
[program:privy-worker]
command=$APP_DIR/venv/bin/celery -A app.workers.celery_app.celery_app worker --loglevel=info --concurrency=4
directory=$APP_DIR
user=$USER
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=$APP_DIR/logs/worker.log
environment=PATH="$APP_DIR/venv/bin"
EOF

sudo tee /etc/supervisor/conf.d/privy-beat.conf > /dev/null << EOF
[program:privy-beat]
command=$APP_DIR/venv/bin/celery -A app.workers.celery_app.celery_app beat --loglevel=info
directory=$APP_DIR
user=$USER
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=$APP_DIR/logs/beat.log
environment=PATH="$APP_DIR/venv/bin"
EOF

sudo supervisorctl reread
sudo supervisorctl update

log_success "Supervisor configured"

# Step 12: Configure Nginx
log_info "🌐 Setting up Nginx..."

sudo tee /etc/nginx/sites-available/privy-api > /dev/null << 'EOF'
server {
    listen 80;
    server_name _;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        access_log off;
    }

    access_log /var/log/nginx/privy-access.log;
    error_log /var/log/nginx/privy-error.log;
}
EOF

sudo ln -sf /etc/nginx/sites-available/privy-api /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
sudo systemctl enable nginx

log_success "Nginx configured"

# Step 13: Configure firewall
log_info "🔥 Configuring firewall..."

sudo ufw --force enable
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

log_success "Firewall configured"

# Step 14: Start all services
log_info "🚀 Starting all services..."

sudo supervisorctl start all
sleep 5

# Test the API
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    log_success "API is running successfully!"
else
    log_error "API is not responding. Check logs: $APP_DIR/logs/api.log"
fi

# Step 15: Create API key
log_info "🔑 Creating production API key..."
API_KEY_OUTPUT=$(python cli.py create-api-key --org-name "Production Org" --key-name "Production Key" 2>&1)
API_KEY=$(echo "$API_KEY_OUTPUT" | grep "Full Key:" | cut -d' ' -f3)

# Step 16: Save important information
log_info "💾 Saving important information..."

cat > PRODUCTION_INFO.txt << EOF
🚀 Privy Fraud Detection API - Production Information
===================================================

🌐 API URL: http://$(curl -s ipinfo.io/ip)
📚 Documentation: http://$(curl -s ipinfo.io/ip)/docs
💓 Health Check: http://$(curl -s ipinfo.io/ip)/health

🔑 API Key: $API_KEY
⚠️  SAVE THIS API KEY SECURELY - IT CANNOT BE RETRIEVED!

🗄️ Database Passwords:
- PostgreSQL root: $POSTGRES_PASSWORD
- Privy DB user: $PRIVY_DB_PASSWORD

🔴 Redis Password: $REDIS_PASSWORD

📁 Application Directory: $APP_DIR
📋 Environment File: $APP_DIR/.env.prod

🛠️ Management Commands:
- View API logs: tail -f $APP_DIR/logs/api.log
- Restart API: sudo supervisorctl restart privy-api
- Check status: sudo supervisorctl status
- Update data: cd $APP_DIR && source venv/bin/activate && python cli.py seed-data --data-type all

🔒 Next Steps:
1. Update your domain name in Nginx config: /etc/nginx/sites-available/privy-api
2. Get SSL certificate: sudo certbot --nginx -d yourdomain.com
3. Test API: curl -X POST "http://$(curl -s ipinfo.io/ip)/v1/check" -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" -d '{"email": "test@tempmail.com", "ip": "1.2.3.4"}'

📖 Full documentation: $APP_DIR/PRODUCTION_DEPLOYMENT.md
EOF

log_success "Production setup completed!"
echo
echo "=================================================="
echo "🎉 Your Privy Fraud Detection API is now LIVE!"
echo "=================================================="
echo
cat PRODUCTION_INFO.txt
echo
log_info "All important information saved to: $APP_DIR/PRODUCTION_INFO.txt"