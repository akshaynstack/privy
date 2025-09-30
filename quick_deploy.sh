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

log_success "System dependencies installed"

# Step 2: Configure PostgreSQL
log_info "🗄️ Configuring PostgreSQL..."

# Generate secure passwords
POSTGRES_PASSWORD=$(openssl rand -base64 32)
PRIVY_DB_PASSWORD=$(openssl rand -base64 32)

# Configure PostgreSQL
sudo -u postgres psql -c "ALTER USER postgres PASSWORD '$POSTGRES_PASSWORD';"
sudo -u postgres psql -c "CREATE USER privy_prod WITH PASSWORD '$PRIVY_DB_PASSWORD';"
sudo -u postgres psql -c "CREATE DATABASE privy_prod OWNER privy_prod;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE privy_prod TO privy_prod;"

log_success "PostgreSQL configured"

# Step 3: Configure Redis
log_info "🔴 Configuring Redis..."

REDIS_PASSWORD=$(openssl rand -base64 32)

# Backup original config
sudo cp /etc/redis/redis.conf /etc/redis/redis.conf.backup

# Configure Redis
sudo sed -i "s/# requirepass foobared/requirepass $REDIS_PASSWORD/" /etc/redis/redis.conf
sudo sed -i "s/# maxmemory <bytes>/maxmemory 512mb/" /etc/redis/redis.conf
sudo sed -i "s/# maxmemory-policy noeviction/maxmemory-policy allkeys-lru/" /etc/redis/redis.conf

sudo systemctl restart redis-server
sudo systemctl enable redis-server

log_success "Redis configured"

# Step 4: Create application directory
log_info "📁 Setting up application directory..."

APP_DIR="/home/$USER/privy-api"
mkdir -p $APP_DIR
cd $APP_DIR

# Copy application files (assuming they're in current directory)
if [ -f "requirements.txt" ]; then
    log_info "Found application files in current directory"
else
    log_error "Application files not found. Please copy your Privy backend files to: $APP_DIR"
    exit 1
fi

# Step 5: Create virtual environment and install dependencies
log_info "🐍 Setting up Python environment..."

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
ALLOWED_ORIGINS=https://yourdomain.com

# Database Configuration
DATABASE_URL=postgresql+asyncpg://privy_prod:$PRIVY_DB_PASSWORD@localhost:5432/privy_prod
DATABASE_URL_SYNC=postgresql+psycopg://privy_prod:$PRIVY_DB_PASSWORD@localhost:5432/privy_prod

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

export $(cat .env.prod | xargs)
alembic upgrade head

log_success "Database initialized"

# Step 8: Setup fraud detection data
log_info "🛡️ Setting up fraud detection data..."

python setup_fraud_detection.py || python cli.py seed-data --data-type all

log_success "Fraud detection data loaded"

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