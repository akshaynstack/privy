# Privy - Fraud Detection API

**Privy** is an open-source fraud detection and risk scoring API service inspired by [SignupGate](https://signupgate.com).  
It provides real-time risk assessment for user signups, email validation, IP reputation checking, and abuse detection to help protect your applications from fraudulent users.

## 🚀 Features

- 🛡️ **Real-time Risk Scoring** — Instant fraud detection with configurable scoring  
- 📧 **Email Validation** — Disposable email detection (10,000+ domains) and pattern analysis
- 🌐 **IP Intelligence** — VPN, Tor, proxy detection with geolocation analysis  
- 🌍 **Geolocation Analysis** — High-risk country detection and ISP analysis
- 🔑 **API Key Management** — Secure authentication with per-organization API keys  
- ⚡ **Rate Limiting** — Token bucket rate limiting with Redis backend  
- 📊 **Analytics & Logging** — Comprehensive check logging and analytics  
- 🚫 **Custom Blacklists** — Organization-specific IP, email, and domain blocking  
- 🔄 **Background Processing** — Async data ingestion with Celery workers
- 🤖 **Automated Data Updates** — Automatic updates of fraud detection databases
- 📋 **Detailed Reporting** — Risk explanations and actionable recommendations  

## 🏗️ Architecture

Built with:
- ⚡ **FastAPI** — High-performance async Python API framework
- 🐘 **PostgreSQL** — Primary database for persistent data
- 🔴 **Redis** — Caching, rate limiting, and fast lookups
- 📦 **SQLModel** — Modern ORM with Pydantic integration
- 🔄 **Alembic** — Database migration management
- 🌿 **Celery** — Distributed task queue for background jobs
- 🐳 **Docker** — Containerized deployment

---

## 📂 Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Configuration and environment variables
│   ├── db.py                # Database connection and session management
│   ├── models.py            # SQLModel database models
│   ├── crud.py              # Database CRUD operations
│   ├── api/
│   │   ├── deps.py          # API dependencies (auth, validation)
│   │   └── routes.py        # API route handlers
│   ├── services/
│   │   ├── scoring.py       # Risk scoring algorithms
│   │   └── rate_limiter.py  # Rate limiting implementation
│   └── workers/
│       ├── celery_app.py    # Celery configuration
│       └── tasks.py         # Background task definitions
├── migrations/              # Alembic database migrations
├── tests/                   # Test suite
├── requirements.txt         # Python dependencies
├── alembic.ini             # Alembic configuration
├── docker-compose.yml      # Development environment
├── Dockerfile              # Container definition
└── .env                    # Environment variables
```  

---

## 🛠️ Setup & Installation

### 1. Clone the repository
```bash
git clone https://github.com/akshaynstack/privy.git
cd privy/backend
```

### 2. Environment Setup

#### Option A: Docker (Recommended)
```bash
# Copy environment template
cp .env.template .env

# Edit .env with your configuration
# Start all services
docker-compose up --build
```

#### Option B: Local Development
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate   # Linux/Mac
.venv\Scripts\activate      # Windows

# Install dependencies
pip install -r requirements.txt

# Setup environment variables
cp .env.template .env
# Edit .env with your database and Redis URLs

# Run database migrations
alembic upgrade head

# Start the API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# In separate terminals, start Redis and Celery worker:
redis-server
celery -A app.workers.celery_app.celery_app worker --loglevel=info
```

### 3. Verify Installation
```bash
# Test the API
curl -X POST "http://localhost:8000/v1/check" \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "ip": "1.2.3.4"}'
```

## 📡 API Reference

**Base URL:** `http://localhost:8000`

### Core Endpoints

```http
POST /v1/check
```
Perform real-time fraud detection check

**Headers:**
- `X-API-Key: {key_id}.{secret}` (required)
- `Content-Type: application/json`

**Request Body:**
```json
{
  "email": "user@example.com",
  "ip": "192.168.1.1",
  "user_agent": "Mozilla/5.0...",
  "metadata": {
    "custom_field": "value"
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "risk_score": 25,
    "risk_level": "low",
    "reasons": ["disposable_email"]
  }
}
```

### Risk Levels
- **none** (0-29): Safe to proceed
- **low** (30-59): Monitor closely
- **medium** (60-79): Challenge user (CAPTCHA, 2FA)
- **high** (80-100): Block or manual review

### Rate Limits
- **Default:** 60 requests per minute per API key
- **Burst:** Up to 60 tokens in bucket
- **Refill:** 1 token per second

### Error Codes
- `401` - Invalid or missing API key
- `429` - Rate limit exceeded
- `422` - Invalid request payload
- `500` - Internal server error

## 🗂️ Data Models

### User
- Multi-tenant organization support
- Email-based authentication
- Automatic UUID generation

### Organization  
- API key scoping
- Custom blacklist management
- Usage analytics

### ApiKey
- Secure key generation with public ID + secret
- bcrypt hashed secrets
- Revocation support

### Check
- Complete request logging
- Risk score tracking
- JSON metadata storage

### Blacklist
- IP addresses, email domains, ISPs, ASNs
- Organization-specific rules
- Reason tracking

---

## 📊 Fraud Detection Features

### Email Analysis
- ✅ Disposable email detection (10,000+ domains)
- ✅ Domain reputation scoring
- ✅ Custom domain blacklists
- 🔄 Real-time email validation

### IP Intelligence  
- ✅ VPN/Proxy detection
- ✅ Tor exit node identification
- ✅ Geolocation analysis
- ✅ ISP reputation scoring
- 🔄 Multiple signups from same IP detection

### Behavioral Analysis
- ✅ Rate limiting per API key
- ✅ Request pattern analysis
- 🔄 Device fingerprinting
- 🔄 Time-based anomaly detection

### Custom Rules
- ✅ Organization blacklists
- ✅ Configurable scoring weights
- 🔄 Machine learning integration
- 🔄 Custom webhook triggers

*Legend: ✅ Implemented | 🔄 Planned*

---

## 📈 Roadmap

### Phase 1 (Current)
- ✅ Core fraud detection API
- ✅ Basic email and IP checks  
- ✅ Rate limiting and API keys
- ✅ Docker deployment

### Phase 2 (Next)
- 🔄 Web dashboard for analytics
- 🔄 Advanced ML-based scoring
- 🔄 Webhook notifications
- 🔄 Bulk data ingestion APIs

### Phase 3 (Future)
- 🔄 Device fingerprinting
- 🔄 Behavioral analytics
- 🔄 Enterprise SSO integration
- 🔄 Custom rule engine UI

## 🔧 Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/privy
DATABASE_URL_SYNC=postgresql://user:pass@localhost:5432/privy

# Redis
REDIS_URL=redis://localhost:6379

# Celery
CELERY_BROKER=redis://localhost:6379/0
CELERY_BACKEND=redis://localhost:6379/1

# API
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=true

# Optional: External data sources
DISPOSABLE_EMAIL_URL=https://raw.githubusercontent.com/disposable/disposable-email-domains/master/domains.txt
```

### Scoring Configuration

Customize risk scoring weights in `app/services/scoring.py`:

```python
WEIGHTS = {
    "disposable_email": 70,
    "vpn_ip": 60,
    "tor_exit": 80,
    "bad_isp": 40,
    "multiple_from_ip": 30,
    "custom_blacklist": 100,
}
```

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_scoring.py -v
```

---

## 🚀 Production Deployment

### Docker Production

```bash
# Build production image
docker build -t privy-api .

# Run with production settings
docker run -p 8000:8000 --env-file .env.prod privy-api
```

### Manual Deployment

1. Set up PostgreSQL and Redis
2. Configure production environment variables
3. Run database migrations: `alembic upgrade head`
4. Start API server: `gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker`
5. Start Celery worker: `celery -A app.workers.celery_app.celery_app worker`

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please read our [Code of Conduct](CODE_OF_CONDUCT.md) and [Security Policy](SECURITY.md).

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🌟 Support

If you find this project useful, please consider:
- ⭐ Starring the repository
- 🐛 Reporting bugs and issues
- 💡 Suggesting new features
- 🤝 Contributing code improvements
- 📢 Sharing with others who might benefit

For support:
- 📖 Check the [documentation](README.md) and [setup guide](UBUNTU_SETUP.md)
- 🐛 Report bugs via [GitHub Issues](https://github.com/yourusername/privy/issues)
- 💬 Join discussions in [GitHub Discussions](https://github.com/yourusername/privy/discussions)
- 🔒 Report security issues via our [Security Policy](SECURITY.md)

---

**Built with ❤️ for developers who want to protect their applications from fraud.**