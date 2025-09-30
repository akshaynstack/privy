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
def seed_data(data_type: str = typer.Option("disposable-emails", help="Type of data to seed")):
    """Seed the database with test data."""
    
    if data_type == "disposable-emails":
        from app.workers.tasks import ingest_disposable_emails
        
        typer.echo("🌱 Seeding disposable email domains...")
        result = ingest_disposable_emails.delay(settings.disposable_email_url)
        typer.echo(f"✅ Background task queued: {result.id}")
    else:
        typer.echo(f"❌ Unknown data type: {data_type}", err=True)


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