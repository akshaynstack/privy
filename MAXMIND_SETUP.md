# MaxMind GeoLite2 Setup Guide

## 🌍 Self-Hosted IP Geolocation with MaxMind

Your fraud detection system now uses **MaxMind GeoLite2** databases for IP geolocation instead of external APIs. This provides:

- ✅ **No API rate limits** - Unlimited lookups
- ✅ **Privacy** - No external API calls  
- ✅ **Speed** - Local database lookups (~1ms)
- ✅ **Reliability** - Works offline
- ✅ **Accuracy** - Industry-standard geolocation

## 📥 Database Setup

### Option 1: Automated Setup (Recommended)

```bash
# 1. Get a free MaxMind license key
# Go to: https://www.maxmind.com/en/accounts/current/license-key
# Create account and generate a license key

# 2. Set environment variable
export MAXMIND_LICENSE_KEY="your_license_key_here"

# 3. Download databases automatically
python cli.py update-maxmind
```

### Option 2: Manual Setup

```bash
# 1. Create data directory
mkdir -p data/maxmind

# 2. Download databases manually
# Go to: https://dev.maxmind.com/geoip/geolite2-free-geolocation-data
# Download these files:
# - GeoLite2-Country (Binary / gzip)
# - GeoLite2-City (Binary / gzip) 
# - GeoLite2-ASN (Binary / gzip)

# 3. Extract and place .mmdb files
# Extract the .mmdb files from the downloaded archives
# Copy them to data/maxmind/ with these exact names:
# - GeoLite2-Country.mmdb
# - GeoLite2-City.mmdb  
# - GeoLite2-ASN.mmdb

# 4. Verify setup
python cli.py setup-maxmind
```

## 🔧 CLI Commands

### Setup and Management
```bash
# Check MaxMind database status
python cli.py setup-maxmind

# Update databases (requires license key)
python cli.py update-maxmind

# Test IP geolocation
python cli.py test-geolocation --ip 8.8.8.8
```

### Testing Examples
```bash
# Test Google DNS
python cli.py test-geolocation --ip 8.8.8.8

# Test Cloudflare DNS  
python cli.py test-geolocation --ip 1.1.1.1

# Test your own IP
python cli.py test-geolocation --ip $(curl -s ipinfo.io/ip)
```

## 📊 Database Information

| Database | Purpose | Size | Updates |
|----------|---------|------|---------|
| **GeoLite2-Country** | Country detection | ~6 MB | Monthly |
| **GeoLite2-City** | City/region detection | ~70 MB | Monthly |
| **GeoLite2-ASN** | ISP/ASN detection | ~8 MB | Monthly |

## 🎯 Fraud Detection Integration

The MaxMind databases automatically enhance fraud detection:

### Country Risk Assessment
```python
# Automatically checks if IP is from high-risk country
# Based on your configured high-risk country list in Redis
is_high_risk = await maxmind_service.is_high_risk_country("1.2.3.4")
```

### Hosting Provider Detection  
```python
# Detects if IP belongs to hosting/cloud providers
# Uses ASN and organization name analysis
is_hosting = await maxmind_service.is_hosting_provider("1.2.3.4")
```

### Enhanced API Response
```json
{
  "success": true,
  "data": {
    "risk_score": 45,
    "risk_level": "medium",
    "reasons": ["high_risk_country", "hosting_provider"],
    "geolocation": {
      "country": "Example Country",
      "country_code": "EX",
      "city": "Example City",
      "latitude": 12.345,
      "longitude": 67.890
    },
    "network": {
      "asn": 12345,
      "isp": "Example Hosting Provider",
      "organization": "Example Cloud Services"
    }
  }
}
```

## 🔄 Automatic Updates

### Scheduled Updates (Production)
```python
# Add to your cron job or scheduled tasks
# Update databases monthly (MaxMind releases monthly updates)
0 0 1 * * python cli.py update-maxmind
```

### Celery Periodic Tasks
```python
# Add to your Celery beat schedule
from celery.schedules import crontab

app.conf.beat_schedule = {
    'update-maxmind-monthly': {
        'task': 'app.workers.tasks.download_maxmind_databases',
        'schedule': crontab(day_of_month=1, hour=2, minute=0),  # 1st of month, 2 AM
    },
}
```

## 🏗️ Directory Structure

```
backend/
├── data/
│   └── maxmind/
│       ├── GeoLite2-Country.mmdb    # Country database
│       ├── GeoLite2-City.mmdb       # City/region database
│       └── GeoLite2-ASN.mmdb        # ISP/ASN database
└── app/
    └── services/
        └── geolocation.py           # MaxMind service
```

## ⚡ Performance

### Lookup Speed
- **Country lookup**: ~0.1ms
- **City lookup**: ~0.5ms  
- **ASN lookup**: ~0.1ms
- **Combined lookup**: ~1ms

### Memory Usage
- **Country DB**: ~10 MB RAM
- **City DB**: ~100 MB RAM
- **ASN DB**: ~15 MB RAM
- **Total**: ~125 MB RAM

### Caching
- In-memory LRU cache for repeated lookups
- Cache hit ratio: typically 80-90%
- Cache size: configurable (default: unlimited)

## 🔒 Privacy & Compliance

### Data Privacy
- ✅ No external API calls
- ✅ No data leaves your servers
- ✅ GDPR compliant (no personal data to 3rd parties)
- ✅ Full control over IP data

### License Compliance
- MaxMind GeoLite2 databases are free under Creative Commons license
- Commercial use allowed
- Attribution required in documentation
- Redistribution allowed with attribution

## 🛠️ Troubleshooting

### Database Not Found
```bash
# Check database files exist
ls -la data/maxmind/

# Re-download if missing
python cli.py setup-maxmind
```

### Permission Errors
```bash
# Fix file permissions
chmod 644 data/maxmind/*.mmdb
chown $(whoami):$(whoami) data/maxmind/*.mmdb
```

### Outdated Databases
```bash
# Check database age
stat data/maxmind/*.mmdb

# Update if older than 1 month
python cli.py update-maxmind
```

### Memory Issues
```python
# Reduce memory usage by only loading required databases
# Edit app/services/geolocation.py to comment out unused readers
```

## 🚀 Production Deployment

### Docker Setup
```dockerfile
# Add to your Dockerfile
COPY data/maxmind/ /app/data/maxmind/
RUN chmod 644 /app/data/maxmind/*.mmdb
```

### Environment Variables
```bash
# Required for automated updates
MAXMIND_LICENSE_KEY=your_license_key_here

# Optional: Custom database path
MAXMIND_DB_PATH=/custom/path/to/databases
```

### Health Checks
```bash
# Verify databases are loaded
curl http://localhost:8000/v1/status

# Test specific IP
python cli.py test-geolocation --ip 8.8.8.8
```

## 📈 Benefits Over External APIs

| Feature | External APIs | MaxMind Self-Hosted |
|---------|--------------|-------------------|
| **Rate Limits** | 1,000-50,000/month | Unlimited |
| **Latency** | 50-200ms | <1ms |
| **Privacy** | Data sent to 3rd party | Complete privacy |
| **Reliability** | Depends on external service | Works offline |
| **Cost** | $20-100/month | Free |
| **Customization** | Limited | Full control |

Your fraud detection system is now **enterprise-grade** with self-hosted IP intelligence! 🌍