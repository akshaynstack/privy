# Fraud Detection Data Sources

## 🎯 Currently Working

### ✅ Disposable Email Detection
- **Source**: https://github.com/disposable/disposable-email-domains
- **Auto-updates**: Via Celery task `ingest_disposable_emails()`
- **Coverage**: 10,000+ disposable email domains
- **Command**: `python cli.py seed-data --type disposable-emails`

### ✅ Custom Blacklists  
- **Source**: Your organization's manual entries
- **Management**: CLI tool or direct database
- **Types**: IP addresses, email domains, ISPs, ASNs

## 🔄 Needs Implementation

### 1. VPN/Proxy IP Detection
**Free Sources:**
```python
# Add this task to workers/tasks.py
@celery_app.task
def update_vpn_ips():
    # Option A: Free proxy lists
    urls = [
        "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt"
    ]
    
    # Option B: VPN provider IP ranges (manual research)
    vpn_ranges = [
        "198.7.58.0/24",   # NordVPN range example
        "185.216.35.0/24", # ExpressVPN range example
    ]
```

**Commercial Sources:**
- IPQualityScore API
- MaxMind GeoIP2 
- IPinfo.io
- AbuseIPDB

### 2. Tor Exit Node Detection
```python
@celery_app.task  
def update_tor_exit_nodes():
    # Official Tor exit node list
    url = "https://check.torproject.org/torbulkexitlist"
    response = httpx.get(url)
    
    redis_conn = redis.Redis.from_url(os.getenv("REDIS_URL"))
    redis_conn.delete("tor_exit_nodes")
    
    for ip in response.text.strip().split('\n'):
        if ip.strip():
            redis_conn.sadd("tor_exit_nodes", ip.strip())
```

### 3. Bad ISP Detection
```python
# Known hosting/VPS providers (higher fraud risk)
bad_isps = [
    "DigitalOcean, LLC",
    "Amazon Technologies Inc.",
    "Google LLC", 
    "Microsoft Corporation",
    "Hetzner Online GmbH",
    "OVH SAS"
]

# Residential ISPs are typically safer:
good_isps = [
    "Comcast Cable",
    "Verizon Fios", 
    "AT&T Internet",
    "BT Group"
]
```

### 4. Geolocation Fraud Patterns
```python
# High-risk countries (customize based on your business)
high_risk_countries = [
    "CN", "RU", "NG", "PK", "BD"  # ISO country codes
]

# Impossible travel detection
# If user was in US 1 hour ago, now in China = suspicious
```

## 🔧 Implementation Commands

### Setup Data Sources
```bash
# 1. Disposable emails (already working)
python cli.py seed-data --type disposable-emails

# 2. Add VPN detection (you need to implement)
python cli.py seed-data --type vpn-ips

# 3. Add Tor detection (you need to implement)  
python cli.py seed-data --type tor-exits

# 4. Add bad ISPs (you need to implement)
python cli.py seed-data --type bad-isps
```

### Manual Blacklist Management
```bash
# Add suspicious IP
python cli.py add-blacklist --org-id "your-org" --type ip --value "1.2.3.4"

# Add suspicious domain
python cli.py add-blacklist --org-id "your-org" --type email_domain --value "suspicious.com"
```

## 📊 Commercial Data Providers

### Recommended APIs:
1. **IPQualityScore** - $40/month
   - VPN/Proxy detection
   - Fraud probability scoring
   - Real-time lookups

2. **MaxMind GeoIP2** - $20/month
   - ISP information
   - Country/city lookup
   - Anonymous proxy detection

3. **AbuseIPDB** - Free tier available
   - Community-driven IP reputation
   - Malicious IP detection

4. **HaveIBeenPwned** - For compromised email detection

## 🎯 Detection Accuracy Tips

### High Accuracy Signals:
- Disposable emails (90%+ accuracy)
- Known Tor exit nodes (99% accuracy)
- Custom blacklists (100% accuracy)

### Medium Accuracy Signals:
- VPN detection (70-80% accuracy - many legitimate users use VPNs)
- Hosting provider IPs (60-70% accuracy)

### Behavioral Signals (Future):
- Multiple accounts from same IP/browser
- Rapid signup patterns
- Impossible geolocation jumps
- Device fingerprinting mismatches

## 🚀 Quick Start (Free Implementation)

To get basic fraud detection working immediately:

```bash
# 1. Get disposable emails working
python cli.py seed-data --type disposable-emails

# 2. Download Tor exit nodes manually
curl https://check.torproject.org/torbulkexitlist > tor_exits.txt
# Then import to Redis set "tor_exit_nodes"

# 3. Create your first custom blacklist
python cli.py create-api-key --org-name "Test Org"
# Use the API to add known bad IPs/domains
```

This gives you immediate fraud detection for the most common attack vectors!