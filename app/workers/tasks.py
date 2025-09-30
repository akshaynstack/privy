# app/workers/tasks.py
from .celery_app import celery_app
import httpx, os, aioredis, asyncio
from app.db import engine
from sqlmodel import SQLModel
from app.models import Blacklist, Check
import json
import ipaddress
from typing import List

redis = aioredis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"), decode_responses=True)

@celery_app.task
def ingest_disposable_emails(url: str = None):
    """Download and store disposable email domains in Redis."""
    if not url:
        url = "https://raw.githubusercontent.com/disposable/disposable-email-domains/master/domains.txt"
    
    try:
        r = httpx.get(url, timeout=30.0)
        if r.status_code != 200:
            return {"success": False, "error": f"HTTP {r.status_code}"}
        
        content = r.text.splitlines()
        
        # Use Redis pipeline for efficiency
        import redis as rlib
        rconn = rlib.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
        
        # Clear existing data
        rconn.delete("disposable_email_domains")
        
        pipe = rconn.pipeline()
        domains_added = 0
        
        for domain in content:
            domain = domain.strip().lower()
            if domain and not domain.startswith("#"):
                pipe.sadd("disposable_email_domains", domain)
                domains_added += 1
        
        pipe.execute()
        return {"success": True, "domains_added": domains_added}
        
    except Exception as e:
        return {"success": False, "error": str(e)}


@celery_app.task
def ingest_tor_exit_nodes():
    """Download and store Tor exit nodes in Redis."""
    urls = [
        "https://check.torproject.org/torbulkexitlist",
        "https://www.dan.me.uk/torlist/"
    ]
    
    import redis as rlib
    rconn = rlib.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
    
    # Clear existing data
    rconn.delete("tor_exit_nodes")
    
    total_ips = 0
    
    for url in urls:
        try:
            r = httpx.get(url, timeout=30.0)
            if r.status_code == 200:
                ips = r.text.strip().split('\n')
                pipe = rconn.pipeline()
                
                for ip in ips:
                    ip = ip.strip()
                    if ip and _is_valid_ip(ip):
                        pipe.sadd("tor_exit_nodes", ip)
                        total_ips += 1
                
                pipe.execute()
                break  # Use first successful source
                
        except Exception as e:
            print(f"Failed to fetch from {url}: {e}")
            continue
    
    return {"success": total_ips > 0, "ips_added": total_ips}


@celery_app.task
def ingest_vpn_proxy_ips():
    """Download and store known VPN/Proxy IPs in Redis."""
    # Free proxy lists (be careful with these in production)
    urls = [
        "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
        "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/proxy.txt"
    ]
    
    import redis as rlib
    rconn = rlib.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
    
    # Don't clear existing data, just add to it
    total_ips = 0
    
    for url in urls:
        try:
            r = httpx.get(url, timeout=30.0)
            if r.status_code == 200:
                lines = r.text.strip().split('\n')
                pipe = rconn.pipeline()
                
                for line in lines:
                    line = line.strip()
                    if ':' in line:  # proxy format ip:port
                        ip = line.split(':')[0]
                    else:
                        ip = line
                    
                    if _is_valid_ip(ip):
                        pipe.sadd("vpn_ips", ip)
                        total_ips += 1
                
                pipe.execute()
                
        except Exception as e:
            print(f"Failed to fetch from {url}: {e}")
            continue
    
    return {"success": total_ips > 0, "ips_added": total_ips}


@celery_app.task  
def ingest_bad_isps():
    """Store known hosting/VPS provider ASNs and ISP names."""
    # Known hosting providers (higher fraud risk)
    bad_isps = [
        "DigitalOcean, LLC",
        "Amazon Technologies Inc.",
        "Amazon.com, Inc.", 
        "Google LLC",
        "Google Cloud Platform",
        "Microsoft Corporation",
        "Hetzner Online GmbH",
        "OVH SAS",
        "Vultr Holdings, LLC",
        "Linode, LLC",
        "Scaleway S.A.S.",
        "Cloudflare, Inc.",
        "Choopa, LLC",
        "HostHatch",
        "Contabo GmbH",
        "IONOS SE"
    ]
    
    # Bad ASNs (Autonomous System Numbers)
    bad_asns = [
        "AS14061",  # DigitalOcean
        "AS16509",  # Amazon
        "AS15169",  # Google
        "AS8075",   # Microsoft
        "AS24940",  # Hetzner
        "AS16276",  # OVH
        "AS20473",  # Choopa/Vultr
        "AS63949",  # Linode
        "AS12876",  # Scaleway
        "AS13335",  # Cloudflare
    ]
    
    import redis as rlib
    rconn = rlib.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
    
    # Clear and populate bad ISPs
    rconn.delete("bad_isps")
    rconn.delete("bad_asns")
    
    pipe = rconn.pipeline()
    
    for isp in bad_isps:
        pipe.sadd("bad_isps", isp.lower())
    
    for asn in bad_asns:
        pipe.sadd("bad_asns", asn.upper())
    
    pipe.execute()
    
    return {
        "success": True, 
        "isps_added": len(bad_isps),
        "asns_added": len(bad_asns)
    }


@celery_app.task
def ingest_high_risk_countries():
    """Store high-risk country codes for geolocation analysis."""
    # High-risk countries based on fraud statistics
    # Customize this list based on your business needs
    high_risk_countries = [
        "CN",  # China
        "RU",  # Russia  
        "NG",  # Nigeria
        "PK",  # Pakistan
        "BD",  # Bangladesh
        "IN",  # India (high volume, mixed risk)
        "VN",  # Vietnam
        "ID",  # Indonesia
        "BR",  # Brazil
        "TR",  # Turkey
        "EG",  # Egypt
        "IR",  # Iran
        "KP",  # North Korea
        "MM",  # Myanmar
    ]
    
    import redis as rlib
    rconn = rlib.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
    
    rconn.delete("high_risk_countries")
    
    pipe = rconn.pipeline()
    for country in high_risk_countries:
        pipe.sadd("high_risk_countries", country.upper())
    
    pipe.execute()
    
    return {"success": True, "countries_added": len(high_risk_countries)}


@celery_app.task
def download_maxmind_databases():
    """Download MaxMind GeoLite2 databases.
    
    Note: You need a MaxMind account and license key for automated downloads.
    Free databases can be downloaded manually from:
    https://dev.maxmind.com/geoip/geolite2-free-geolocation-data
    """
    import gzip
    import shutil
    import tarfile
    from pathlib import Path
    
    # MaxMind license key (required for downloads)
    license_key = os.getenv("MAXMIND_LICENSE_KEY")
    if not license_key:
        return {
            "success": False, 
            "error": "MAXMIND_LICENSE_KEY not set. Download databases manually.",
            "manual_download_url": "https://dev.maxmind.com/geoip/geolite2-free-geolocation-data"
        }
    
    # Create data directory
    data_dir = Path("data/maxmind")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Database URLs (requires license key)
    databases = {
        "GeoLite2-Country": f"https://download.maxmind.com/app/geoip_download?edition_id=GeoLite2-Country&license_key={license_key}&suffix=tar.gz",
        "GeoLite2-City": f"https://download.maxmind.com/app/geoip_download?edition_id=GeoLite2-City&license_key={license_key}&suffix=tar.gz",
        "GeoLite2-ASN": f"https://download.maxmind.com/app/geoip_download?edition_id=GeoLite2-ASN&license_key={license_key}&suffix=tar.gz"
    }
    
    results = {}
    
    for db_name, url in databases.items():
        try:
            print(f"Downloading {db_name}...")
            
            # Download tar.gz file
            response = httpx.get(url, timeout=300.0)  # 5 minute timeout
            if response.status_code != 200:
                results[db_name] = {"success": False, "error": f"HTTP {response.status_code}"}
                continue
            
            # Save tar.gz file
            tar_path = data_dir / f"{db_name}.tar.gz"
            with open(tar_path, "wb") as f:
                f.write(response.content)
            
            # Extract tar.gz
            with tarfile.open(tar_path, "r:gz") as tar:
                # Find the .mmdb file in the archive
                mmdb_file = None
                for member in tar.getmembers():
                    if member.name.endswith(".mmdb"):
                        mmdb_file = member
                        break
                
                if mmdb_file:
                    # Extract the .mmdb file
                    tar.extract(mmdb_file, data_dir)
                    
                    # Move to final location
                    extracted_path = data_dir / mmdb_file.name
                    final_path = data_dir / f"{db_name}.mmdb"
                    
                    if extracted_path.exists():
                        shutil.move(str(extracted_path), str(final_path))
                        results[db_name] = {"success": True, "path": str(final_path)}
                    else:
                        results[db_name] = {"success": False, "error": "mmdb file not found after extraction"}
                else:
                    results[db_name] = {"success": False, "error": "No .mmdb file found in archive"}
            
            # Clean up tar file
            tar_path.unlink(missing_ok=True)
            
            # Clean up extracted directory
            for item in data_dir.iterdir():
                if item.is_dir() and item.name.startswith(db_name):
                    shutil.rmtree(item)
            
        except Exception as e:
            results[db_name] = {"success": False, "error": str(e)}
    
    # Reload the MaxMind service
    try:
        from app.services.geolocation import maxmind_service
        maxmind_service._initialize_readers()
    except Exception as e:
        print(f"Error reloading MaxMind service: {e}")
    
    successful = sum(1 for r in results.values() if r.get("success"))
    total = len(results)
    
    return {
        "success": successful > 0,
        "databases_updated": successful,
        "total_databases": total,
        "results": results
    }


@celery_app.task
def setup_maxmind_manually():
    """Setup instructions for manual MaxMind database installation."""
    from pathlib import Path
    
    data_dir = Path("data/maxmind")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    instructions = {
        "message": "Manual MaxMind setup required",
        "data_directory": str(data_dir.absolute()),
        "required_files": [
            "GeoLite2-Country.mmdb",
            "GeoLite2-City.mmdb", 
            "GeoLite2-ASN.mmdb"
        ],
        "download_steps": [
            "1. Go to https://dev.maxmind.com/geoip/geolite2-free-geolocation-data",
            "2. Create a free MaxMind account",
            "3. Download the following databases:",
            "   - GeoLite2 Country (Binary / gzip)",
            "   - GeoLite2 City (Binary / gzip)", 
            "   - GeoLite2 ASN (Binary / gzip)",
            "4. Extract the .mmdb files",
            f"5. Copy them to: {data_dir.absolute()}",
            "6. Restart the API server"
        ],
        "automation_note": "For automated updates, set MAXMIND_LICENSE_KEY environment variable"
    }
    
    # Check which files exist
    existing_files = []
    missing_files = []
    
    for filename in instructions["required_files"]:
        file_path = data_dir / filename
        if file_path.exists():
            existing_files.append({
                "name": filename,
                "size": file_path.stat().st_size,
                "modified": file_path.stat().st_mtime
            })
        else:
            missing_files.append(filename)
    
    instructions["existing_files"] = existing_files
    instructions["missing_files"] = missing_files
    instructions["setup_complete"] = len(missing_files) == 0
    
@celery_app.task
def update_ip_reputation():
    """Run all IP reputation updates in sequence."""
    results = {}
    
    # Run all data ingestion tasks
    results["disposable_emails"] = ingest_disposable_emails()
    results["tor_nodes"] = ingest_tor_exit_nodes()
    results["vpn_proxies"] = ingest_vpn_proxy_ips()
    results["bad_isps"] = ingest_bad_isps()
    results["high_risk_countries"] = ingest_high_risk_countries()
    
    # Check MaxMind database status
    results["maxmind_status"] = setup_maxmind_manually()
    
    return results


@celery_app.task
def persist_check(payload: dict):
    """Persist a check record to Postgres synchronously."""
    try:
        from sqlalchemy import create_engine
        DATABASE_URL_SYNC = os.getenv("DATABASE_URL_SYNC", "postgresql+psycopg://postgres:postgres@localhost:5432/privy")
        engine = create_engine(DATABASE_URL_SYNC)
        
        with engine.begin() as conn:
            check = Check(**{
                "org_id": payload.get("org_id"),
                "ip": payload.get("ip"),
                "email": payload.get("email"),
                "user_agent": payload.get("user_agent"),
                "result": payload.get("result"),
                "risk_score": payload.get("risk_score"),
                "action": payload.get("action")
            })
            
            # Insert check record
            from sqlalchemy import text
            insert_sql = text("""
                INSERT INTO "check" (id, org_id, ip, email, user_agent, result, risk_score, action, created_at)
                VALUES (:id, :org_id, :ip, :email, :user_agent, :result, :risk_score, :action, :created_at)
            """)
            
            conn.execute(insert_sql, {
                "id": check.id,
                "org_id": check.org_id,
                "ip": check.ip,
                "email": check.email,
                "user_agent": check.user_agent,
                "result": json.dumps(check.result) if check.result else None,
                "risk_score": check.risk_score,
                "action": check.action,
                "created_at": check.created_at
            })
            
        return {"success": True}
        
    except Exception as e:
        print(f"Failed to persist check: {e}")
        return {"success": False, "error": str(e)}


def _is_valid_ip(ip: str) -> bool:
    """Validate if string is a valid IP address."""
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False