#!/bin/bash
# Create dedicated user for Privy Fraud Detection API
# This script creates a secure system user to run the application

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then
    log_error "This script must be run as root or with sudo"
    echo "Usage: sudo $0"
    exit 1
fi

log_info "🔐 Creating dedicated user for Privy API"
echo "========================================"

# Configuration
PRIVY_USER="privy"
PRIVY_GROUP="privy"
PRIVY_HOME="/opt/privy"
PRIVY_APP_DIR="$PRIVY_HOME/app"
PRIVY_DATA_DIR="$PRIVY_HOME/data"
PRIVY_LOGS_DIR="$PRIVY_HOME/logs"

# Step 1: Create group
log_info "👥 Creating group: $PRIVY_GROUP"
if getent group $PRIVY_GROUP >/dev/null 2>&1; then
    log_warning "Group $PRIVY_GROUP already exists"
else
    groupadd --system $PRIVY_GROUP
    log_success "Group $PRIVY_GROUP created"
fi

# Step 2: Create user
log_info "👤 Creating user: $PRIVY_USER"
if id "$PRIVY_USER" &>/dev/null; then
    log_warning "User $PRIVY_USER already exists"
else
    useradd \
        --system \
        --gid $PRIVY_GROUP \
        --home-dir $PRIVY_HOME \
        --create-home \
        --shell /bin/bash \
        --comment "Privy Fraud Detection API user" \
        $PRIVY_USER
    log_success "User $PRIVY_USER created"
fi

# Step 3: Create directory structure
log_info "📁 Creating directory structure"
directories=(
    "$PRIVY_HOME"
    "$PRIVY_APP_DIR"
    "$PRIVY_DATA_DIR"
    "$PRIVY_DATA_DIR/maxmind"
    "$PRIVY_LOGS_DIR"
    "$PRIVY_HOME/.ssh"
)

for dir in "${directories[@]}"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        log_info "Created directory: $dir"
    else
        log_info "Directory already exists: $dir"
    fi
done

# Step 4: Set ownership and permissions
log_info "🔒 Setting ownership and permissions"
chown -R $PRIVY_USER:$PRIVY_GROUP $PRIVY_HOME
chmod 755 $PRIVY_HOME
chmod 755 $PRIVY_APP_DIR
chmod 755 $PRIVY_DATA_DIR
chmod 750 $PRIVY_LOGS_DIR
chmod 700 $PRIVY_HOME/.ssh

log_success "Ownership and permissions set"

# Step 5: Add user to necessary groups
log_info "👥 Adding user to necessary groups"

# Add to www-data group for Nginx integration
if getent group www-data >/dev/null 2>&1; then
    usermod -a -G www-data $PRIVY_USER
    log_info "Added $PRIVY_USER to www-data group"
fi

# Add to redis group for Redis access
if getent group redis >/dev/null 2>&1; then
    usermod -a -G redis $PRIVY_USER
    log_info "Added $PRIVY_USER to redis group"
fi

# Step 6: Configure sudo access (limited)
log_info "🔧 Configuring sudo access"
cat > /etc/sudoers.d/privy << EOF
# Allow privy user to restart its own services
$PRIVY_USER ALL=(root) NOPASSWD: /usr/bin/supervisorctl restart privy-*
$PRIVY_USER ALL=(root) NOPASSWD: /usr/bin/supervisorctl status privy-*
$PRIVY_USER ALL=(root) NOPASSWD: /usr/bin/supervisorctl start privy-*
$PRIVY_USER ALL=(root) NOPASSWD: /usr/bin/supervisorctl stop privy-*
$PRIVY_USER ALL=(root) NOPASSWD: /bin/systemctl reload nginx
$PRIVY_USER ALL=(root) NOPASSWD: /bin/systemctl status nginx
EOF

chmod 440 /etc/sudoers.d/privy
log_success "Sudo access configured"

# Step 7: Create application environment script
log_info "📝 Creating environment setup script"
cat > $PRIVY_HOME/setup_env.sh << 'EOF'
#!/bin/bash
# Privy API Environment Setup
# Source this file to set up the environment for the Privy user

export PRIVY_HOME="/opt/privy"
export PRIVY_APP_DIR="$PRIVY_HOME/app"
export PRIVY_DATA_DIR="$PRIVY_HOME/data"
export PRIVY_LOGS_DIR="$PRIVY_HOME/logs"
export PYTHONPATH="$PRIVY_APP_DIR"

# Add Python virtual environment to PATH
if [ -f "$PRIVY_APP_DIR/venv/bin/activate" ]; then
    source "$PRIVY_APP_DIR/venv/bin/activate"
fi

# Load environment variables if they exist
if [ -f "$PRIVY_APP_DIR/.env.prod" ]; then
    export $(cat "$PRIVY_APP_DIR/.env.prod" | grep -v '^#' | xargs)
fi

# Aliases for common operations
alias privy-logs='tail -f $PRIVY_LOGS_DIR/api.log'
alias privy-worker-logs='tail -f $PRIVY_LOGS_DIR/worker.log'
alias privy-restart='sudo supervisorctl restart privy-api privy-worker privy-beat'
alias privy-status='sudo supervisorctl status privy-*'
alias privy-cli='cd $PRIVY_APP_DIR && python cli.py'

echo "🚀 Privy API environment loaded"
echo "📁 App directory: $PRIVY_APP_DIR"
echo "📊 Logs directory: $PRIVY_LOGS_DIR"
echo "🔧 Use 'privy-cli' to run CLI commands"
EOF

chown $PRIVY_USER:$PRIVY_GROUP $PRIVY_HOME/setup_env.sh
chmod 755 $PRIVY_HOME/setup_env.sh

# Step 8: Add environment setup to .bashrc
log_info "🔧 Configuring user shell"
cat >> $PRIVY_HOME/.bashrc << EOF

# Privy API Environment
source $PRIVY_HOME/setup_env.sh
EOF

chown $PRIVY_USER:$PRIVY_GROUP $PRIVY_HOME/.bashrc

# Step 9: Create systemd service files (alternative to supervisor)
log_info "🔧 Creating systemd service files"

# Privy API service
cat > /etc/systemd/system/privy-api.service << EOF
[Unit]
Description=Privy Fraud Detection API
After=network.target postgresql.service redis.service
Wants=postgresql.service redis.service

[Service]
Type=exec
User=$PRIVY_USER
Group=$PRIVY_GROUP
WorkingDirectory=$PRIVY_APP_DIR
Environment=PATH=$PRIVY_APP_DIR/venv/bin
EnvironmentFile=$PRIVY_APP_DIR/.env.prod
ExecStart=$PRIVY_APP_DIR/venv/bin/gunicorn app.main:app -c gunicorn.conf.py
Restart=always
RestartSec=5
StandardOutput=append:$PRIVY_LOGS_DIR/api.log
StandardError=append:$PRIVY_LOGS_DIR/api.log

[Install]
WantedBy=multi-user.target
EOF

# Privy Worker service
cat > /etc/systemd/system/privy-worker.service << EOF
[Unit]
Description=Privy Celery Worker
After=network.target postgresql.service redis.service
Wants=postgresql.service redis.service

[Service]
Type=exec
User=$PRIVY_USER
Group=$PRIVY_GROUP
WorkingDirectory=$PRIVY_APP_DIR
Environment=PATH=$PRIVY_APP_DIR/venv/bin
EnvironmentFile=$PRIVY_APP_DIR/.env.prod
ExecStart=$PRIVY_APP_DIR/venv/bin/celery -A app.workers.celery_app.celery_app worker --loglevel=info --concurrency=4
Restart=always
RestartSec=5
StandardOutput=append:$PRIVY_LOGS_DIR/worker.log
StandardError=append:$PRIVY_LOGS_DIR/worker.log

[Install]
WantedBy=multi-user.target
EOF

# Privy Beat service
cat > /etc/systemd/system/privy-beat.service << EOF
[Unit]
Description=Privy Celery Beat Scheduler
After=network.target postgresql.service redis.service
Wants=postgresql.service redis.service

[Service]
Type=exec
User=$PRIVY_USER
Group=$PRIVY_GROUP
WorkingDirectory=$PRIVY_APP_DIR
Environment=PATH=$PRIVY_APP_DIR/venv/bin
EnvironmentFile=$PRIVY_APP_DIR/.env.prod
ExecStart=$PRIVY_APP_DIR/venv/bin/celery -A app.workers.celery_app.celery_app beat --loglevel=info
Restart=always
RestartSec=5
StandardOutput=append:$PRIVY_LOGS_DIR/beat.log
StandardError=append:$PRIVY_LOGS_DIR/beat.log

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
systemctl daemon-reload

log_success "Systemd services created"

# Step 10: Create deployment helper script
log_info "📦 Creating deployment helper script"
cat > $PRIVY_HOME/deploy_app.sh << 'EOF'
#!/bin/bash
# Deploy Privy API Application
# Run this script as the privy user to deploy the application

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Check if running as privy user
if [ "$(whoami)" != "privy" ]; then
    echo "❌ This script must be run as the privy user"
    echo "Switch to privy user: sudo su - privy"
    exit 1
fi

APP_DIR="/opt/privy/app"
CURRENT_DIR=$(pwd)

log_info "🚀 Deploying Privy API"

# Step 1: Copy application files
if [ "$CURRENT_DIR" != "$APP_DIR" ]; then
    log_info "📁 Copying application files to $APP_DIR"
    
    # Create backup of existing app
    if [ -d "$APP_DIR" ] && [ "$(ls -A $APP_DIR)" ]; then
        backup_dir="/opt/privy/backup-$(date +%Y%m%d-%H%M%S)"
        cp -r "$APP_DIR" "$backup_dir"
        log_info "📦 Backup created: $backup_dir"
    fi
    
    # Copy new files
    cp -r . "$APP_DIR"
    cd "$APP_DIR"
fi

# Step 2: Set up Python environment
log_info "🐍 Setting up Python environment"
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn[gevent]

# Step 3: Set up environment file
log_info "⚙️ Setting up environment"
if [ ! -f ".env.prod" ]; then
    if [ -f ".env.template" ]; then
        cp .env.template .env.prod
        log_info "📝 Created .env.prod from template. Please edit it with your settings."
    else
        log_info "⚠️  No .env.prod found. You'll need to create one."
    fi
fi

# Step 4: Run database migrations
log_info "🗄️ Running database migrations"
if [ -f ".env.prod" ]; then
    export $(cat .env.prod | grep -v '^#' | xargs)
    alembic upgrade head
else
    log_info "⚠️  Skipping migrations - no .env.prod file"
fi

# Step 5: Set up fraud detection data
log_info "🛡️ Setting up fraud detection data"
if [ -f "setup_fraud_detection.py" ]; then
    python setup_fraud_detection.py || python cli.py seed-data --data-type all
else
    python cli.py seed-data --data-type all
fi

# Step 6: Create Gunicorn config if it doesn't exist
if [ ! -f "gunicorn.conf.py" ]; then
    log_info "🦄 Creating Gunicorn configuration"
    cat > gunicorn.conf.py << 'GUNICORN_EOF'
import multiprocessing

bind = "127.0.0.1:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 30
keepalive = 2
max_requests = 1000
max_requests_jitter = 50
preload_app = True
accesslog = "/opt/privy/logs/gunicorn-access.log"
errorlog = "/opt/privy/logs/gunicorn-error.log"
loglevel = "info"
proc_name = "privy-api"
GUNICORN_EOF
fi

# Step 7: Set correct permissions
log_info "🔒 Setting permissions"
find . -type f -name "*.py" -exec chmod 644 {} \;
find . -type f -name "*.sh" -exec chmod 755 {} \;
chmod 755 cli.py

log_success "✅ Deployment completed!"
log_info "Next steps:"
echo "1. Edit .env.prod with your production settings"
echo "2. Start services: sudo systemctl start privy-api privy-worker privy-beat"
echo "3. Enable services: sudo systemctl enable privy-api privy-worker privy-beat"
echo "4. Check status: sudo systemctl status privy-api"
EOF

chown $PRIVY_USER:$PRIVY_GROUP $PRIVY_HOME/deploy_app.sh
chmod 755 $PRIVY_HOME/deploy_app.sh

# Step 11: Create log rotation configuration
log_info "📊 Setting up log rotation"
cat > /etc/logrotate.d/privy << EOF
$PRIVY_LOGS_DIR/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 $PRIVY_USER $PRIVY_GROUP
    postrotate
        sudo systemctl reload privy-api privy-worker privy-beat 2>/dev/null || true
    endscript
}
EOF

log_success "Log rotation configured"

# Step 12: Create user info summary
log_info "📋 Creating user information summary"
cat > $PRIVY_HOME/USER_INFO.txt << EOF
🔐 Privy API User Information
============================

👤 User: $PRIVY_USER
👥 Group: $PRIVY_GROUP
🏠 Home Directory: $PRIVY_HOME
📁 Application Directory: $PRIVY_APP_DIR
📊 Logs Directory: $PRIVY_LOGS_DIR
📊 Data Directory: $PRIVY_DATA_DIR

🔧 Management Commands:
======================

# Switch to privy user
sudo su - privy

# Deploy application (as privy user)
./deploy_app.sh

# Start services
sudo systemctl start privy-api privy-worker privy-beat

# Enable services (auto-start on boot)
sudo systemctl enable privy-api privy-worker privy-beat

# Check service status
sudo systemctl status privy-api
sudo systemctl status privy-worker
sudo systemctl status privy-beat

# View logs
tail -f $PRIVY_LOGS_DIR/api.log
tail -f $PRIVY_LOGS_DIR/worker.log

# Restart services
sudo systemctl restart privy-api
sudo systemctl restart privy-worker

# Run CLI commands (as privy user)
cd $PRIVY_APP_DIR && python cli.py --help

🛡️ Security Features:
=====================
✅ Dedicated system user (non-login)
✅ Restricted home directory permissions
✅ Limited sudo access (only for service management)
✅ Proper file ownership and permissions
✅ Log rotation configured
✅ Group-based access control

📁 Directory Structure:
======================
$PRIVY_HOME/
├── app/                    # Application files
│   ├── venv/              # Python virtual environment
│   ├── .env.prod          # Production environment file
│   └── ...                # Your application code
├── data/                  # Application data
│   └── maxmind/          # MaxMind databases
├── logs/                  # Application logs
├── setup_env.sh          # Environment setup script
├── deploy_app.sh         # Deployment script
└── USER_INFO.txt         # This file

🚀 Next Steps:
=============
1. Copy your application files to $PRIVY_APP_DIR
2. Switch to privy user: sudo su - privy
3. Deploy the application: ./deploy_app.sh
4. Configure production settings in .env.prod
5. Start services: sudo systemctl start privy-api privy-worker privy-beat
EOF

chown $PRIVY_USER:$PRIVY_GROUP $PRIVY_HOME/USER_INFO.txt

log_success "✅ Privy user setup completed!"
echo
echo "========================================"
echo "🎉 User '$PRIVY_USER' is ready!"
echo "========================================"
echo
echo "📋 Summary:"
echo "  User: $PRIVY_USER"
echo "  Home: $PRIVY_HOME"
echo "  App Directory: $PRIVY_APP_DIR"
echo
echo "🔧 Next Steps:"
echo "  1. Switch to privy user: sudo su - privy"
echo "  2. Copy your app files to: $PRIVY_APP_DIR"
echo "  3. Deploy the app: ./deploy_app.sh"
echo "  4. Start services: sudo systemctl start privy-api privy-worker privy-beat"
echo
echo "📖 Full documentation: $PRIVY_HOME/USER_INFO.txt"
echo
log_info "User creation completed successfully!"