#!/usr/bin/env python3
"""
Privy Fraud Detection Setup Script

This script sets up the complete fraud detection system with all data sources.
Run this after setting up your environment to get full fraud detection capability.
"""

import asyncio
import sys
import os
import time
import redis

# Add the app directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config import settings
from app.db import init_db
from app.workers.tasks import (
    ingest_disposable_emails,
    ingest_tor_exit_nodes, 
    ingest_vpn_proxy_ips,
    ingest_bad_isps,
    ingest_high_risk_countries
)


async def setup_database():
    """Initialize database tables."""
    print("🗄️  Setting up database...")
    try:
        await init_db()
        print("✅ Database tables created successfully")
        return True
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        return False


def test_redis_connection():
    """Test Redis connection."""
    print("🔴 Testing Redis connection...")
    try:
        r = redis.Redis.from_url(settings.redis_url, decode_responses=True)
        r.ping()
        print("✅ Redis connection successful")
        return True
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return False


def setup_fraud_data():
    """Set up all fraud detection data sources."""
    print("🛡️  Setting up fraud detection data...")
    
    tasks = [
        ("Disposable Email Domains", ingest_disposable_emails),
        ("Tor Exit Nodes", ingest_tor_exit_nodes),
        ("VPN/Proxy IPs", ingest_vpn_proxy_ips),
        ("Bad ISPs", ingest_bad_isps),
        ("High-Risk Countries", ingest_high_risk_countries)
    ]
    
    results = {}
    
    for name, task_func in tasks:
        print(f"  📥 Loading {name}...")
        try:
            result = task_func()
            if isinstance(result, dict) and result.get("success"):
                print(f"  ✅ {name}: {result}")
                results[name] = True
            else:
                print(f"  ⚠️  {name}: {result}")
                results[name] = False
        except Exception as e:
            print(f"  ❌ {name}: {e}")
            results[name] = False
    
    return results


async def create_demo_api_key():
    """Create a demo API key for testing."""
    print("🔑 Creating demo API key...")
    try:
        from app.db import get_session
        from app.crud import UserCRUD, OrganizationCRUD, ApiKeyCRUD
        
        async with get_session() as session:
            # Create demo user
            user = await UserCRUD.create(session, "demo@privy.dev")
            
            # Create demo organization
            org = await OrganizationCRUD.create(session, "Demo Organization", user.id)
            
            # Create API key
            api_key, full_key = await ApiKeyCRUD.create(session, "Demo Key", org.id)
            
            print("✅ Demo API key created successfully!")
            print(f"   Organization: Demo Organization")
            print(f"   Key: {full_key}")
            print("   ⚠️  Save this key - you'll need it for testing!")
            
            return full_key
            
    except Exception as e:
        print(f"❌ Failed to create demo API key: {e}")
        return None


def check_data_status():
    """Check the status of all fraud detection data."""
    print("📊 Checking data status...")
    
    try:
        r = redis.Redis.from_url(settings.redis_url, decode_responses=True)
        
        datasets = [
            ("disposable_email_domains", "Disposable Email Domains"),
            ("tor_exit_nodes", "Tor Exit Nodes"),
            ("vpn_ips", "VPN/Proxy IPs"),
            ("bad_isps", "Bad ISPs"),
            ("bad_asns", "Bad ASNs"),
            ("high_risk_countries", "High-Risk Countries")
        ]
        
        total_entries = 0
        
        for key, name in datasets:
            count = r.scard(key)
            status = "✅" if count > 0 else "❌"
            print(f"  {status} {name}: {count:,} entries")
            total_entries += count
        
        print(f"📈 Total entries loaded: {total_entries:,}")
        return total_entries > 0
        
    except Exception as e:
        print(f"❌ Failed to check data status: {e}")
        return False


async def test_fraud_detection(api_key: str):
    """Test the fraud detection API."""
    print("🧪 Testing fraud detection...")
    
    try:
        import httpx
        
        test_cases = [
            {
                "name": "Clean Email + IP",
                "data": {"email": "john@gmail.com", "ip": "8.8.8.8"}
            },
            {
                "name": "Disposable Email",
                "data": {"email": "test@tempmail.com", "ip": "1.2.3.4"}
            },
            {
                "name": "Suspicious Patterns",
                "data": {"email": "user12345@fakeemail.com", "ip": "192.168.1.1"}
            }
        ]
        
        for test_case in test_cases:
            print(f"  🔍 Testing: {test_case['name']}")
            
            try:
                response = httpx.post(
                    f"http://{settings.api_host}:{settings.api_port}/v1/check",
                    headers={
                        "X-API-Key": api_key,
                        "Content-Type": "application/json"
                    },
                    json=test_case["data"],
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    data = result.get("data", {})
                    score = data.get("risk_score", 0)
                    level = data.get("risk_level", "unknown")
                    action = data.get("action", "unknown")
                    
                    print(f"    Score: {score}/100, Level: {level.upper()}, Action: {action.upper()}")
                else:
                    print(f"    ❌ HTTP {response.status_code}: {response.text}")
                    
            except Exception as e:
                print(f"    ❌ Test failed: {e}")
        
        print("✅ Fraud detection tests completed")
        return True
        
    except Exception as e:
        print(f"❌ Failed to test fraud detection: {e}")
        return False


async def main():
    """Main setup function."""
    print("🚀 Privy Fraud Detection Setup")
    print("=" * 50)
    
    # 1. Test Redis connection
    if not test_redis_connection():
        print("❌ Setup failed: Redis connection required")
        return False
    
    # 2. Setup database
    if not await setup_database():
        print("❌ Setup failed: Database initialization required")
        return False
    
    # 3. Setup fraud detection data
    fraud_results = setup_fraud_data()
    successful_loads = sum(fraud_results.values())
    total_loads = len(fraud_results)
    
    print(f"📊 Fraud data setup: {successful_loads}/{total_loads} successful")
    
    # 4. Check data status
    if not check_data_status():
        print("⚠️  Warning: No fraud detection data loaded")
    
    # 5. Create demo API key
    api_key = await create_demo_api_key()
    
    # 6. Test the API if we have a key
    if api_key:
        print("\n" + "=" * 50)
        print("🧪 Running API Tests...")
        await test_fraud_detection(api_key)
    
    print("\n" + "=" * 50)
    print("🎉 Setup Complete!")
    print("\n📚 Next Steps:")
    print("1. Start the API server: uvicorn app.main:app --reload")
    print("2. Start Celery worker: celery -A app.workers.celery_app.celery_app worker --loglevel=info")
    print("3. Visit http://localhost:8000/docs for API documentation")
    
    if api_key:
        print(f"4. Use this API key for testing: {api_key}")
    
    print("\n🔧 CLI Commands:")
    print("- Check data status: python cli.py check-data-status")
    print("- Create API key: python cli.py create-api-key --org-name 'Your Org'")
    print("- Test API: python cli.py test-fraud-check --email test@example.com --api-key YOUR_KEY")
    print("- Update data: python cli.py seed-data --data-type all")
    
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)