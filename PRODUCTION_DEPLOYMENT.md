# Production Deployment Guide - Ubuntu 22.04

## 🚀 Making Privy Fraud Detection API Live

This guide will help you deploy your fraud detection API to production on Ubuntu 22.04.

## 📋 Prerequisites Checklist

```bash
# Verify Ubuntu version
lsb_release -a

# Verify Python version (should be 3.10+)
python3 --version

# Verify you have the project
ls -la /path/to/your/privy/backend
```

## 🔧 Production Setup

### Step 1: System Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required system packages
sudo apt install -y \
    nginx \
    supervisor \
    certbot \
    python3-certbot-nginx \
    ufw \
    fail2ban \
    htop \
    curl \
    git

# Install PostgreSQL and Redis if not already installed
sudo apt install -y postgresql postgresql-contrib redis-server
```

### Step 2: Configure PostgreSQL for Production

```bash
# Secure PostgreSQL installation
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'secure_postgres_password';"

# Create production database and user
sudo -u postgres psql -c "CREATE USER privy_prod WITH PASSWORD 'secure_privy_password';"
sudo -u postgres psql -c "CREATE DATABASE privy_prod OWNER privy_prod;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE privy_prod TO privy_prod;"

# Configure PostgreSQL for production
sudo nano /etc/postgresql/14/main/postgresql.conf
# Update these settings:
# listen_addresses = 'localhost'
# max_connections = 100
# shared_buffers = 256MB

# Configure authentication
sudo nano /etc/postgresql/14/main/pg_hba.conf
# Ensure local connections use md5:
# local   all             all                                     md5

# Restart PostgreSQL
sudo systemctl restart postgresql
sudo systemctl enable postgresql
```

### Step 3: Configure Redis for Production

```bash
# Configure Redis
sudo nano /etc/redis/redis.conf

# Set these configurations:
# bind 127.0.0.1 ::1
# requirepass your_secure_redis_password
# maxmemory 512mb
# maxmemory-policy allkeys-lru
# save 900 1
# save 300 10
# save 60 10000

# Restart Redis
sudo systemctl restart redis-server
sudo systemctl enable redis-server

# Test Redis
redis-cli -a your_secure_redis_password ping
```

### Step 4: Application Deployment

```bash
# Create application user
sudo useradd -m -s /bin/bash privy
sudo usermod -aG sudo privy

# Switch to application user
sudo su - privy

# Create application directory
mkdir -p /home/privy/app
cd /home/privy/app

# Copy your application files
# (Copy from your development environment)
# Or clone from git:
# git clone https://github.com/yourusername/privy.git .

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install additional production packages
pip install gunicorn[gevent] supervisor psutil
```

### Step 5: Production Environment Configuration

```bash
# Create production .env file
cd /home/privy/app
cp .env.template .env.prod

# Edit production environment
nano .env.prod
```

```bash
# Production Environment Variables
APP_NAME="Privy Fraud Detection API"
VERSION="1.0.0"
ENVIRONMENT=production
DEBUG=false

# API Configuration
API_HOST=127.0.0.1
API_PORT=8000
ALLOWED_ORIGINS=https://yourdomain.com,https://api.yourdomain.com

# Database Configuration (UPDATE WITH YOUR SECURE PASSWORDS)
DATABASE_URL=postgresql+asyncpg://privy_prod:secure_privy_password@localhost:5432/privy_prod
DATABASE_URL_SYNC=postgresql+psycopg://privy_prod:secure_privy_password@localhost:5432/privy_prod

# Redis Configuration (UPDATE WITH YOUR SECURE PASSWORD)
REDIS_URL=redis://:your_secure_redis_password@localhost:6379
CELERY_BROKER=redis://:your_secure_redis_password@localhost:6379/0
CELERY_BACKEND=redis://:your_secure_redis_password@localhost:6379/1

# Security Settings (GENERATE A SECURE KEY!)
SECRET_KEY=$(openssl rand -hex 32)

# Rate Limiting
DEFAULT_RATE_LIMIT=2.0
DEFAULT_RATE_CAPACITY=120

# Logging
LOG_LEVEL=INFO

# Feature Flags
ENABLE_ANALYTICS=true
ENABLE_BACKGROUND_TASKS=true
ENABLE_CUSTOM_BLACKLISTS=true

# MaxMind (if you have a license key)
MAXMIND_LICENSE_KEY=your_maxmind_license_key_here
```

### Step 6: Database Setup

```bash
# Run database migrations
source venv/bin/activate
export $(cat .env.prod | xargs)
alembic upgrade head

# Setup fraud detection data
python setup_fraud_detection.py

# Create your first production API key
python cli.py create-api-key --org-name "Production Org" --key-name "Production Key"
# SAVE THE API KEY SECURELY!
```

### Step 7: Gunicorn Configuration

```bash
# Create Gunicorn configuration
nano /home/privy/app/gunicorn.conf.py
```

```python
# Gunicorn configuration file
import multiprocessing

# Server socket
bind = "127.0.0.1:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
timeout = 30
keepalive = 2

# Restart workers after this many requests
max_requests = 1000
max_requests_jitter = 50

# Logging
accesslog = "/home/privy/logs/gunicorn-access.log"
errorlog = "/home/privy/logs/gunicorn-error.log"
loglevel = "info"

# Process naming
proc_name = "privy-api"

# Server mechanics
daemon = False
pidfile = "/home/privy/app/gunicorn.pid"
user = "privy"
group = "privy"
tmp_upload_dir = None

# SSL (if using SSL termination at app level)
# keyfile = "/path/to/keyfile"
# certfile = "/path/to/certfile"
```

```bash
# Create logs directory
mkdir -p /home/privy/logs
```

### Step 8: Supervisor Configuration

```bash
# Exit from privy user
exit

# Create supervisor configurations
sudo nano /etc/supervisor/conf.d/privy-api.conf
```

```ini
[program:privy-api]
command=/home/privy/app/venv/bin/gunicorn app.main:app -c gunicorn.conf.py
directory=/home/privy/app
user=privy
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/home/privy/logs/api.log
environment=PATH="/home/privy/app/venv/bin"
```

```bash
# Create Celery worker configuration
sudo nano /etc/supervisor/conf.d/privy-worker.conf
```

```ini
[program:privy-worker]
command=/home/privy/app/venv/bin/celery -A app.workers.celery_app.celery_app worker --loglevel=info --concurrency=4
directory=/home/privy/app
user=privy
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/home/privy/logs/worker.log
environment=PATH="/home/privy/app/venv/bin"
```

```bash
# Create Celery beat configuration
sudo nano /etc/supervisor/conf.d/privy-beat.conf
```

```ini
[program:privy-beat]
command=/home/privy/app/venv/bin/celery -A app.workers.celery_app.celery_app beat --loglevel=info
directory=/home/privy/app
user=privy
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/home/privy/logs/beat.log
environment=PATH="/home/privy/app/venv/bin"
```

```bash
# Update supervisor
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start all

# Check status
sudo supervisorctl status
```

### Step 9: Nginx Configuration

```bash
# Create Nginx configuration
sudo nano /etc/nginx/sites-available/privy-api
```

```nginx
server {
    listen 80;
    server_name yourdomain.com api.yourdomain.com;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;

    # Main API location
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Buffer settings
        proxy_buffering on;
        proxy_buffer_size 128k;
        proxy_buffers 4 256k;
        proxy_busy_buffers_size 256k;
    }

    # Health check endpoint (no rate limiting)
    location /health {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        access_log off;
    }

    # API documentation
    location /docs {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Block access to sensitive endpoints
    location ~ ^/(admin|internal) {
        deny all;
        return 404;
    }

    # Logging
    access_log /var/log/nginx/privy-access.log;
    error_log /var/log/nginx/privy-error.log;
}
```

```bash
# Enable the site
sudo ln -s /etc/nginx/sites-available/privy-api /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default

# Test Nginx configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
sudo systemctl enable nginx
```

### Step 10: SSL Certificate with Let's Encrypt

```bash
# Get SSL certificate
sudo certbot --nginx -d yourdomain.com -d api.yourdomain.com

# Test auto-renewal
sudo certbot renew --dry-run

# Auto-renewal is handled by systemd timer
sudo systemctl status snap.certbot.renew.timer
```

### Step 11: Firewall Configuration

```bash
# Configure UFW firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (update port if you use custom SSH port)
sudo ufw allow 22/tcp

# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status
```

### Step 12: Security Hardening

```bash
# Configure fail2ban
sudo nano /etc/fail2ban/jail.local
```

```ini
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = 22
filter = sshd
logpath = /var/log/auth.log

[nginx-http-auth]
enabled = true
filter = nginx-http-auth
logpath = /var/log/nginx/*error.log

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
logpath = /var/log/nginx/*error.log
```

```bash
# Start fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### Step 13: Monitoring Setup

```bash
# Create monitoring script
sudo nano /home/privy/monitor.sh
```

```bash
#!/bin/bash
# Privy API Monitoring Script

# Check if API is responding
curl -s http://localhost:8000/health > /dev/null
if [ $? -ne 0 ]; then
    echo "$(date): API is not responding" >> /home/privy/logs/monitor.log
    sudo supervisorctl restart privy-api
fi

# Check PostgreSQL
sudo -u postgres psql -c "SELECT 1;" > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "$(date): PostgreSQL is not responding" >> /home/privy/logs/monitor.log
fi

# Check Redis
redis-cli -a your_secure_redis_password ping > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "$(date): Redis is not responding" >> /home/privy/logs/monitor.log
fi

# Check disk space
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 80 ]; then
    echo "$(date): Disk usage is high: ${DISK_USAGE}%" >> /home/privy/logs/monitor.log
fi
```

```bash
# Make executable
sudo chmod +x /home/privy/monitor.sh

# Add to crontab
sudo crontab -e
# Add line:
# */5 * * * * /home/privy/monitor.sh
```

## 🧪 Production Testing

### Test the Deployment

```bash
# 1. Check all services are running
sudo supervisorctl status
sudo systemctl status nginx postgresql redis-server

# 2. Test API directly
curl http://localhost:8000/health

# 3. Test through Nginx
curl http://yourdomain.com/health

# 4. Test with SSL
curl https://yourdomain.com/health

# 5. Test fraud detection
curl -X POST "https://yourdomain.com/v1/check" \
  -H "X-API-Key: your-production-api-key" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@tempmail.com", "ip": "1.2.3.4"}'
```

## 📊 Performance Optimization

### Database Optimization

```sql
-- Connect to PostgreSQL
sudo -u postgres psql privy_prod

-- Create indexes for better performance
CREATE INDEX CONCURRENTLY idx_check_org_id_created_at ON "check" (org_id, created_at DESC);
CREATE INDEX CONCURRENTLY idx_check_ip ON "check" (ip);
CREATE INDEX CONCURRENTLY idx_check_email ON "check" (email);
CREATE INDEX CONCURRENTLY idx_blacklist_org_type_value ON blacklist (org_id, type, value);
CREATE INDEX CONCURRENTLY idx_apikey_key_id ON apikey (key_id);

-- Analyze tables
ANALYZE;
```

### Redis Optimization

```bash
# Monitor Redis memory usage
redis-cli -a your_secure_redis_password info memory

# Monitor Redis performance
redis-cli -a your_secure_redis_password monitor
```

## 🔄 Deployment Automation

Create deployment script:

```bash
# Create deployment script
nano /home/privy/deploy.sh
```

```bash
#!/bin/bash
# Privy API Deployment Script

set -e

echo "🚀 Deploying Privy API..."

# Pull latest code (if using git)
cd /home/privy/app
git pull origin main

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Update fraud detection data
python cli.py seed-data --data-type all

# Restart services
sudo supervisorctl restart privy-api
sudo supervisorctl restart privy-worker
sudo supervisorctl restart privy-beat

# Test deployment
sleep 5
curl -f http://localhost:8000/health || exit 1

echo "✅ Deployment completed successfully!"
```

```bash
chmod +x /home/privy/deploy.sh
```

## 📈 Scaling Considerations

### Horizontal Scaling

```bash
# For high traffic, you can:
# 1. Add more Gunicorn workers
# 2. Run multiple API instances behind load balancer
# 3. Use Redis cluster for Redis scaling
# 4. Use PostgreSQL read replicas
```

### Load Balancer Configuration (if needed)

```nginx
# /etc/nginx/nginx.conf
upstream privy_api {
    server 127.0.0.1:8000;
    server 127.0.0.1:8001;  # Additional instance
    server 127.0.0.1:8002;  # Additional instance
}

server {
    location / {
        proxy_pass http://privy_api;
    }
}
```

Your Privy Fraud Detection API is now **LIVE** and production-ready! 🎉

## 📱 API Endpoints (Live)

- **Health Check**: `https://yourdomain.com/health`
- **API Docs**: `https://yourdomain.com/docs`
- **Fraud Check**: `POST https://yourdomain.com/v1/check`

## 🛠️ Management Commands

```bash
# View logs
sudo tail -f /home/privy/logs/api.log
sudo tail -f /home/privy/logs/worker.log

# Restart services
sudo supervisorctl restart privy-api
sudo supervisorctl restart privy-worker

# Update fraud data
sudo su - privy
cd app && source venv/bin/activate
python cli.py seed-data --data-type all
```