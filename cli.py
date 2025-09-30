# cli.py - Command line interface for Privy API management
"""
CLI tool for managing Privy fraud detection API.

Usage:
    python cli.py create-api-key --org-name "My Organization" --key-name "Production Key"
    python cli.py create-migration --message "Add new table"
    python cli.py seed-data --type disposable-emails
"""

import asyncio
import typer
from typing import Optional
import sys
import os

# Add the app directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db import get_session
from app.crud import UserCRUD, OrganizationCRUD, ApiKeyCRUD
from app.config import settings

app = typer.Typer(help="Privy Fraud Detection API CLI")


@app.command()
def create_api_key(
    org_name: str = typer.Option(..., help="Organization name"),
    key_name: Optional[str] = typer.Option(None, help="API key name"),
    owner_email: str = typer.Option("admin@example.com", help="Owner email")
):
    """Create a new API key for an organization."""
    
    async def _create_key():
        async with get_session() as session:
            # Create or get user
            user = await UserCRUD.get_by_email(session, owner_email)
            if not user:
                user = await UserCRUD.create(session, owner_email)
                typer.echo(f"✅ Created user: {owner_email}")
            
            # Create or get organization
            orgs = await OrganizationCRUD.get_by_owner(session, user.id)
            org = None
            for o in orgs:
                if o.name == org_name:
                    org = o
                    break
            
            if not org:
                org = await OrganizationCRUD.create(session, org_name, user.id)
                typer.echo(f"✅ Created organization: {org_name}")
            
            # Create API key
            api_key, full_key = await ApiKeyCRUD.create(
                session, 
                key_name or f"{org_name} Key",
                org.id
            )
            
            typer.echo("\n🔑 API Key Created Successfully!")
            typer.echo(f"   Organization: {org_name}")
            typer.echo(f"   Key Name: {api_key.name}")
            typer.echo(f"   Key ID: {api_key.key_id}")
            typer.echo(f"   Full Key: {full_key}")
            typer.echo("\n⚠️  IMPORTANT: Save this key securely. It cannot be retrieved again!")
            typer.echo(f"   Use in X-API-Key header: {full_key}")
    
    asyncio.run(_create_key())


@app.command()
def list_api_keys(org_name: Optional[str] = None):
    """List all API keys, optionally filtered by organization."""
    
    async def _list_keys():
        async with get_session() as session:
            if org_name:
                # List keys for specific org
                # This would require additional CRUD methods
                typer.echo(f"Listing keys for organization: {org_name}")
            else:
                typer.echo("Listing all API keys...")
                # Would need to implement this in CRUD
    
    asyncio.run(_list_keys())


@app.command() 
def revoke_api_key(key_id: str):
    """Revoke an API key."""
    
    async def _revoke_key():
        async with get_session() as session:
            success = await ApiKeyCRUD.revoke(session, key_id)
            if success:
                typer.echo(f"✅ API key {key_id} has been revoked")
            else:
                typer.echo(f"❌ API key {key_id} not found", err=True)
    
    asyncio.run(_revoke_key())


@app.command()
def init_db():
    """Initialize database tables."""
    
    async def _init():
        from app.db import init_db
        await init_db()
        typer.echo("✅ Database tables initialized")
    
    asyncio.run(_init())


@app.command()
def create_migration(message: str):
    """Create a new Alembic migration."""
    import subprocess
    
    cmd = f'alembic revision --autogenerate -m "{message}"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        typer.echo(f"✅ Migration created: {message}")
        typer.echo(result.stdout)
    else:
        typer.echo(f"❌ Failed to create migration: {result.stderr}", err=True)


@app.command()
def migrate():
    """Run database migrations."""
    import subprocess
    
    result = subprocess.run("alembic upgrade head", shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        typer.echo("✅ Database migrations completed")
        typer.echo(result.stdout)
    else:
        typer.echo(f"❌ Migration failed: {result.stderr}", err=True)


@app.command()
def seed_data(data_type: str = typer.Option("all", help="Type of data to seed")):
    """Seed the database with fraud detection data."""
    
    if data_type == "disposable-emails":
        from app.workers.tasks import ingest_disposable_emails
        typer.echo("🌱 Seeding disposable email domains...")
        result = ingest_disposable_emails.delay()
        typer.echo(f"✅ Background task queued: {result.id}")
        
    elif data_type == "tor-nodes":
        from app.workers.tasks import ingest_tor_exit_nodes
        typer.echo("🌱 Seeding Tor exit nodes...")
        result = ingest_tor_exit_nodes.delay()
        typer.echo(f"✅ Background task queued: {result.id}")
        
    elif data_type == "vpn-ips":
        from app.workers.tasks import ingest_vpn_proxy_ips
        typer.echo("🌱 Seeding VPN/Proxy IPs...")
        result = ingest_vpn_proxy_ips.delay()
        typer.echo(f"✅ Background task queued: {result.id}")
        
    elif data_type == "bad-isps":
        from app.workers.tasks import ingest_bad_isps
        typer.echo("🌱 Seeding bad ISPs...")
        result = ingest_bad_isps.delay()
        typer.echo(f"✅ Background task queued: {result.id}")
        
    elif data_type == "high-risk-countries":
        from app.workers.tasks import ingest_high_risk_countries
        typer.echo("🌱 Seeding high-risk countries...")
        result = ingest_high_risk_countries.delay()
        typer.echo(f"✅ Background task queued: {result.id}")
        
    elif data_type == "all":
        from app.workers.tasks import update_ip_reputation
        typer.echo("🌱 Seeding all fraud detection data...")
        result = update_ip_reputation.delay()
        typer.echo(f"✅ Background task queued: {result.id}")
        typer.echo("\n📊 This will populate:")
        typer.echo("  - Disposable email domains (~10,000)")
        typer.echo("  - Tor exit nodes (~1,000)")
        typer.echo("  - VPN/Proxy IPs (varies)")
        typer.echo("  - Bad ISP names and ASNs")
        typer.echo("  - High-risk country codes")
        
    else:
        typer.echo(f"❌ Unknown data type: {data_type}", err=True)
        typer.echo("Available types: disposable-emails, tor-nodes, vpn-ips, bad-isps, high-risk-countries, all")


@app.command()
def test_api():
    """Test API connectivity and basic functionality."""
    import httpx
    
    try:
        response = httpx.get(f"http://{settings.api_host}:{settings.api_port}/health")
        if response.status_code == 200:
            typer.echo("✅ API is responding")
            data = response.json()
            typer.echo(f"   Status: {data.get('status')}")
            typer.echo(f"   Version: {data.get('version')}")
            typer.echo(f"   Environment: {data.get('environment')}")
        else:
            typer.echo(f"❌ API returned status code: {response.status_code}")
    except Exception as e:
        typer.echo(f"❌ Failed to connect to API: {e}")


@app.command()
def add_blacklist(
    org_id: str = typer.Option(..., help="Organization ID"),
    type_: str = typer.Option(..., help="Blacklist type (ip, email_domain, isp, asn)"),
    value: str = typer.Option(..., help="Value to blacklist"),
    reason: Optional[str] = typer.Option(None, help="Reason for blacklisting")
):
    """Add entry to organization blacklist."""
    
    async def _add_blacklist():
        async with get_session() as session:
            from app.crud import BlacklistCRUD
            
            blacklist = await BlacklistCRUD.create(
                session, org_id, type_, value, reason
            )
            
            typer.echo(f"✅ Added to blacklist:")
            typer.echo(f"   Type: {type_}")
            typer.echo(f"   Value: {value}")
            typer.echo(f"   Reason: {reason or 'No reason provided'}")
    
    asyncio.run(_add_blacklist())


@app.command()
def check_data_status():
    """Check status of fraud detection data in Redis."""
    import redis as rlib
    
    try:
        rconn = rlib.Redis.from_url(settings.redis_url, decode_responses=True)
        
        typer.echo("📊 Fraud Detection Data Status:")
        typer.echo("="*50)
        
        # Check each data set
        datasets = [
            ("disposable_email_domains", "Disposable Email Domains"),
            ("tor_exit_nodes", "Tor Exit Nodes"),
            ("vpn_ips", "VPN/Proxy IPs"),
            ("bad_isps", "Bad ISPs"),
            ("bad_asns", "Bad ASNs"),
            ("high_risk_countries", "High-Risk Countries")
        ]
        
        for key, name in datasets:
            try:
                count = rconn.scard(key)
                status = "✅" if count > 0 else "❌"
                typer.echo(f"{status} {name}: {count:,} entries")
            except Exception as e:
                typer.echo(f"❌ {name}: Error - {e}")
        
        typer.echo("="*50)
        
        # Test Redis connection
        ping_result = rconn.ping()
        typer.echo(f"🔴 Redis Connection: {'✅ OK' if ping_result else '❌ Failed'}")
        
    except Exception as e:
        typer.echo(f"❌ Failed to connect to Redis: {e}", err=True)


@app.command()
def setup_maxmind():
    """Setup MaxMind GeoLite2 databases."""
    from app.workers.tasks import setup_maxmind_manually, download_maxmind_databases
    
    typer.echo("🌍 MaxMind GeoLite2 Database Setup")
    typer.echo("=" * 50)
    
    # Check current status
    status = setup_maxmind_manually()
    
    typer.echo(f"📁 Data directory: {status['data_directory']}")
    
    if status["existing_files"]:
        typer.echo("\n✅ Existing databases:")
        for file_info in status["existing_files"]:
            size_mb = file_info["size"] / (1024 * 1024)
            typer.echo(f"  - {file_info['name']} ({size_mb:.1f} MB)")
    
    if status["missing_files"]:
        typer.echo("\n❌ Missing databases:")
        for filename in status["missing_files"]:
            typer.echo(f"  - {filename}")
        
        typer.echo("\n📥 Download Steps:")
        for step in status["download_steps"]:
            typer.echo(f"  {step}")
        
        # Try automated download if license key available
        import os
        if os.getenv("MAXMIND_LICENSE_KEY"):
            if typer.confirm("\nMaxMind license key found. Download automatically?"):
                typer.echo("🔄 Downloading databases...")
                result = download_maxmind_databases()
                
                if result["success"]:
                    typer.echo(f"✅ Downloaded {result['databases_updated']}/{result['total_databases']} databases")
                else:
                    typer.echo("❌ Automated download failed. Please download manually.")
        else:
            typer.echo("\n💡 For automated downloads, set MAXMIND_LICENSE_KEY environment variable")
    else:
        typer.echo("\n🎉 All MaxMind databases are installed!")


@app.command()
def update_maxmind():
    """Update MaxMind databases."""
    from app.workers.tasks import download_maxmind_databases
    
    typer.echo("🔄 Updating MaxMind databases...")
    result = download_maxmind_databases.delay()
    typer.echo(f"✅ Background task queued: {result.id}")


@app.command()
def test_geolocation(
    ip: str = typer.Option(..., help="IP address to test")
):
    """Test IP geolocation with MaxMind databases."""
    
    async def _test_geo():
        from app.services.geolocation import enhanced_ip_check
        
        typer.echo(f"🌍 Testing IP geolocation for: {ip}")
        typer.echo("=" * 50)
        
        result = await enhanced_ip_check(ip)
        
        if "error" in result:
            typer.echo(f"❌ Error: {result['error']}")
            return
        
        ip_info = result.get("ip_info", {})
        geolocation = result.get("geolocation", {})
        network = result.get("network", {})
        risk_factors = result.get("risk_factors", {})
        
        # Basic info
        typer.echo(f"IP: {ip}")
        typer.echo(f"Source: {ip_info.get('source', 'Unknown')}")
        typer.echo(f"Databases: {', '.join(ip_info.get('databases_used', []))}")
        
        # Geolocation
        typer.echo("\n🌍 Geolocation:")
        typer.echo(f"  Country: {geolocation.get('country')} ({geolocation.get('country_code')})")
        typer.echo(f"  Region: {geolocation.get('region')}")
        typer.echo(f"  City: {geolocation.get('city')}")
        
        lat, lon = geolocation.get('latitude'), geolocation.get('longitude')
        if lat and lon:
            typer.echo(f"  Coordinates: {lat:.4f}, {lon:.4f}")
        
        typer.echo(f"  Timezone: {geolocation.get('timezone')}")
        
        # Network info
        typer.echo("\n🌐 Network:")
        typer.echo(f"  ISP: {network.get('isp')}")
        typer.echo(f"  Organization: {network.get('organization')}")
        typer.echo(f"  ASN: {network.get('asn')}")
        
        # Risk factors
        typer.echo("\n⚠️  Risk Factors:")
        for factor, value in risk_factors.items():
            status = "🔴 YES" if value else "🟢 NO"
            typer.echo(f"  {factor.replace('_', ' ').title()}: {status}")
        
        # Overall assessment
        is_high_risk = result.get("is_high_risk_country", False)
        is_hosting = result.get("is_hosting_provider", False)
        
        typer.echo("\n📊 Assessment:")
        if is_high_risk or is_hosting:
            typer.echo("  🔴 HIGH RISK - Additional verification recommended")
        elif any(risk_factors.values()):
            typer.echo("  🟡 MEDIUM RISK - Monitor closely")
        else:
            typer.echo("  🟢 LOW RISK - Appears legitimate")
    
@app.command()
def test_fraud_check(
    email: Optional[str] = typer.Option(None, help="Email to test"),
    ip: Optional[str] = typer.Option(None, help="IP to test"),
    api_key: Optional[str] = typer.Option(None, help="API key to use")
):
    """Test fraud detection with sample data."""
    import httpx
    
    if not email and not ip:
        # Use default test data
        email = "test@tempmail.com"
        ip = "1.2.3.4"
    
    if not api_key:
        typer.echo("⚠️  No API key provided. You need to create one first.")
        typer.echo("Run: python cli.py create-api-key --org-name 'Test Org'")
        return
    
    test_data = {}
    if email:
        test_data["email"] = email
    if ip:
        test_data["ip"] = ip
    
    try:
        response = httpx.post(
            f"http://{settings.api_host}:{settings.api_port}/v1/check",
            headers={
                "X-API-Key": api_key,
                "Content-Type": "application/json"
            },
            json=test_data,
            timeout=30.0
        )
        
        if response.status_code == 200:
            result = response.json()
            data = result.get("data", {})
            
            typer.echo("🛡️  Fraud Check Results:")
            typer.echo("="*50)
            typer.echo(f"Risk Score: {data.get('risk_score', 0)}/100")
            typer.echo(f"Risk Level: {data.get('risk_level', 'unknown').upper()}")
            typer.echo(f"Action: {data.get('action', 'unknown').upper()}")
            typer.echo(f"Message: {data.get('message', 'No message')}")
            
            reasons = data.get("reasons", [])
            if reasons:
                typer.echo("\nDetected Issues:")
                for reason in reasons:
                    typer.echo(f"  - {reason}")
            
            recommendations = data.get("recommendations", [])
            if recommendations:
                typer.echo("\nRecommendations:")
                for rec in recommendations:
                    typer.echo(f"  - {rec}")
                    
        else:
            typer.echo(f"❌ API request failed: {response.status_code}")
            typer.echo(f"Response: {response.text}")
            
    except Exception as e:
        typer.echo(f"❌ Failed to test fraud check: {e}", err=True)


@app.command()
def config():
    """Show current configuration."""
    typer.echo("📋 Current Configuration:")
    typer.echo(f"   Environment: {settings.environment}")
    typer.echo(f"   Debug: {settings.debug}")
    typer.echo(f"   API Host: {settings.api_host}:{settings.api_port}")
    typer.echo(f"   Database: {settings.database_url}")
    typer.echo(f"   Redis: {settings.redis_url}")
    typer.echo(f"   Features:")
    typer.echo(f"     - Analytics: {settings.enable_analytics}")
    typer.echo(f"     - Background Tasks: {settings.enable_background_tasks}")
    typer.echo(f"     - Custom Blacklists: {settings.enable_custom_blacklists}")


if __name__ == "__main__":
    app()