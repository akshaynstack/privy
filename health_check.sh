#!/bin/bash
# Production Health Check Script for Privy API

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_service() {
    local service=$1
    local description=$2
    local command=$3
    
    if eval $command > /dev/null 2>&1; then
        echo -e "✅ ${GREEN}$description${NC}"
        return 0
    else
        echo -e "❌ ${RED}$description${NC}"
        return 1
    fi
}

echo "🏥 Privy API Health Check"
echo "========================="

# Check system services
echo "🔧 System Services:"
check_service "nginx" "Nginx Web Server" "systemctl is-active nginx"
check_service "postgresql" "PostgreSQL Database" "systemctl is-active postgresql"
check_service "redis" "Redis Cache" "systemctl is-active redis-server"

echo

# Check application services
echo "🚀 Application Services:"
check_service "api" "Privy API" "supervisorctl status privy-api | grep RUNNING"
check_service "worker" "Celery Worker" "supervisorctl status privy-worker | grep RUNNING"
check_service "beat" "Celery Beat" "supervisorctl status privy-beat | grep RUNNING"

echo

# Check API endpoints
echo "🌐 API Endpoints:"
check_service "health" "Health Endpoint" "curl -f http://localhost:8000/health"
check_service "docs" "API Documentation" "curl -f http://localhost:8000/docs"

echo

# Check database connectivity
echo "🗄️ Database:"
check_service "postgres" "PostgreSQL Connection" "sudo -u postgres psql -c 'SELECT 1;'"

echo

# Check Redis connectivity
echo "🔴 Redis:"
if [ -f ".env.prod" ]; then
    REDIS_PASS=$(grep REDIS_URL .env.prod | cut -d':' -f3 | cut -d'@' -f1)
    check_service "redis" "Redis Connection" "redis-cli -a $REDIS_PASS ping"
else
    check_service "redis" "Redis Connection" "redis-cli ping"
fi

echo

# Check disk space
echo "💾 Resources:"
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -lt 80 ]; then
    echo -e "✅ ${GREEN}Disk Usage: ${DISK_USAGE}%${NC}"
else
    echo -e "⚠️ ${YELLOW}Disk Usage: ${DISK_USAGE}% (High)${NC}"
fi

# Check memory usage
MEM_USAGE=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')
if [ $MEM_USAGE -lt 80 ]; then
    echo -e "✅ ${GREEN}Memory Usage: ${MEM_USAGE}%${NC}"
else
    echo -e "⚠️ ${YELLOW}Memory Usage: ${MEM_USAGE}% (High)${NC}"
fi

# Check load average
LOAD_AVG=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')
echo -e "📊 ${GREEN}Load Average: ${LOAD_AVG}${NC}"

echo
echo "========================="
echo "🎯 Quick Commands:"
echo "View logs: tail -f logs/api.log"
echo "Restart API: sudo supervisorctl restart privy-api"
echo "Check all services: sudo supervisorctl status"
echo "Monitor system: htop"