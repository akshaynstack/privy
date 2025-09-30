# app/services/geolocation.py
"""
Self-hosted IP Geolocation and Intelligence Service using MaxMind GeoLite2 databases

This module provides IP geolocation and intelligence features using MaxMind's
free GeoLite2 databases. No external API calls, complete privacy, unlimited lookups.

Required databases:
- GeoLite2-Country.mmdb - Country lookup
- GeoLite2-City.mmdb - City/location lookup  
- GeoLite2-ASN.mmdb - ISP/ASN lookup

Download from: https://dev.maxmind.com/geoip/geolite2-free-geolocation-data
"""

import geoip2.database
import geoip2.errors
import os
import asyncio
from typing import Optional, Dict, Any, List
from pathlib import Path
import ipaddress

from app.config import settings


class MaxMindGeolocationService:
    """Self-hosted IP Geolocation using MaxMind GeoLite2 databases."""
    
    def __init__(self):
        self.db_path = Path("data/maxmind")
        self.country_reader = None
        self.city_reader = None
        self.asn_reader = None
        self.cache = {}  # Simple in-memory cache
        self._initialize_readers()
    
    def _initialize_readers(self):
        """Initialize MaxMind database readers."""
        try:
            # Country database
            country_db = self.db_path / "GeoLite2-Country.mmdb"
            if country_db.exists():
                self.country_reader = geoip2.database.Reader(str(country_db))
                print(f"✅ Loaded MaxMind Country database: {country_db}")
            else:
                print(f"⚠️  Country database not found: {country_db}")
            
            # City database
            city_db = self.db_path / "GeoLite2-City.mmdb"
            if city_db.exists():
                self.city_reader = geoip2.database.Reader(str(city_db))
                print(f"✅ Loaded MaxMind City database: {city_db}")
            else:
                print(f"⚠️  City database not found: {city_db}")
            
            # ASN database
            asn_db = self.db_path / "GeoLite2-ASN.mmdb"
            if asn_db.exists():
                self.asn_reader = geoip2.database.Reader(str(asn_db))
                print(f"✅ Loaded MaxMind ASN database: {asn_db}")
            else:
                print(f"⚠️  ASN database not found: {asn_db}")
                
        except Exception as e:
            print(f"❌ Error initializing MaxMind readers: {e}")
    
    async def get_ip_info(self, ip: str) -> Dict[str, Any]:
        """Get comprehensive IP information from MaxMind databases."""
        if not ip or not self._is_valid_ip(ip):
            return {"error": "Invalid IP address"}
        
        # Check cache first
        if ip in self.cache:
            return self.cache[ip]
        
        # Run blocking database lookups in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._lookup_ip_sync, ip)
        
        # Cache result
        if result and "error" not in result:
            self.cache[ip] = result
        
        return result
    
    def _lookup_ip_sync(self, ip: str) -> Dict[str, Any]:
        """Synchronous IP lookup (runs in thread pool)."""
        result = {
            "ip": ip,
            "source": "maxmind",
            "databases_used": []
        }
        
        try:
            # Country lookup
            if self.country_reader:
                try:
                    country_response = self.country_reader.country(ip)
                    result.update({
                        "country_code": country_response.country.iso_code,
                        "country": country_response.country.name,
                        "continent_code": country_response.continent.code,
                        "continent": country_response.continent.name,
                        "is_in_european_union": country_response.country.is_in_european_union
                    })
                    result["databases_used"].append("Country")
                except geoip2.errors.AddressNotFoundError:
                    pass
                except Exception as e:
                    print(f"Country lookup error for {ip}: {e}")
            
            # City lookup (includes country data too)
            if self.city_reader:
                try:
                    city_response = self.city_reader.city(ip)
                    result.update({
                        "country_code": city_response.country.iso_code,
                        "country": city_response.country.name,
                        "region_code": city_response.subdivisions.most_specific.iso_code,
                        "region": city_response.subdivisions.most_specific.name,
                        "city": city_response.city.name,
                        "postal_code": city_response.postal.code,
                        "latitude": float(city_response.location.latitude) if city_response.location.latitude else None,
                        "longitude": float(city_response.location.longitude) if city_response.location.longitude else None,
                        "accuracy_radius": city_response.location.accuracy_radius,
                        "timezone": city_response.location.time_zone
                    })
                    result["databases_used"].append("City")
                except geoip2.errors.AddressNotFoundError:
                    pass
                except Exception as e:
                    print(f"City lookup error for {ip}: {e}")
            
            # ASN lookup
            if self.asn_reader:
                try:
                    asn_response = self.asn_reader.asn(ip)
                    result.update({
                        "asn": asn_response.autonomous_system_number,
                        "asn_org": asn_response.autonomous_system_organization,
                        "isp": asn_response.autonomous_system_organization,
                        "organization": asn_response.autonomous_system_organization
                    })
                    result["databases_used"].append("ASN")
                except geoip2.errors.AddressNotFoundError:
                    pass
                except Exception as e:
                    print(f"ASN lookup error for {ip}: {e}")
            
            # Add analysis flags
            result.update(self._analyze_ip_characteristics(ip, result))
            
        except Exception as e:
            return {"ip": ip, "error": str(e), "source": "maxmind"}
        
        return result
    
    def _analyze_ip_characteristics(self, ip: str, geo_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze IP characteristics for fraud detection."""
        characteristics = {
            "is_private": self._is_private_ip(ip),
            "is_hosting_provider": False,
            "is_high_risk_country": False,
            "is_datacenter": False,
            "hosting_indicators": []
        }
        
        # Check if hosting provider based on ASN/ISP
        asn_org = geo_data.get("asn_org", "").lower()
        if asn_org:
            hosting_keywords = [
                "hosting", "cloud", "server", "datacenter", "data center",
                "vps", "dedicated", "colocation", "colo", "aws", "amazon",
                "google", "microsoft", "digitalocean", "vultr", "linode",
                "hetzner", "ovh", "scaleway", "contabo"
            ]
            
            for keyword in hosting_keywords:
                if keyword in asn_org:
                    characteristics["is_hosting_provider"] = True
                    characteristics["hosting_indicators"].append(keyword)
                    break
        
        # Check high-risk countries (sync Redis lookup)
        country_code = geo_data.get("country_code")
        if country_code:
            try:
                import redis as rlib
                rconn = rlib.Redis.from_url(settings.redis_url, decode_responses=True)
                characteristics["is_high_risk_country"] = rconn.sismember(
                    "high_risk_countries", country_code.upper()
                )
            except Exception:
                pass
        
        # Check if datacenter (common datacenter ASNs)
        asn = geo_data.get("asn")
        if asn:
            datacenter_asns = {
                13335,  # Cloudflare
                15169,  # Google
                16509,  # Amazon
                8075,   # Microsoft
                14061,  # DigitalOcean
                20473,  # Choopa/Vultr
                63949,  # Linode
                24940,  # Hetzner
                16276,  # OVH
            }
            if asn in datacenter_asns:
                characteristics["is_datacenter"] = True
        
        return characteristics
    
    def _is_valid_ip(self, ip: str) -> bool:
        """Validate if string is a valid IP address."""
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False
    
    def _is_private_ip(self, ip: str) -> bool:
        """Check if IP is in private ranges."""
        try:
            ip_obj = ipaddress.ip_address(ip)
            return ip_obj.is_private
        except ValueError:
            return False
    
    async def is_high_risk_country(self, ip: str) -> bool:
        """Check if IP is from a high-risk country."""
        ip_info = await self.get_ip_info(ip)
        return ip_info.get("is_high_risk_country", False)
    
    async def is_hosting_provider(self, ip: str) -> bool:
        """Check if IP belongs to a hosting provider."""
        ip_info = await self.get_ip_info(ip)
        return ip_info.get("is_hosting_provider", False) or ip_info.get("is_datacenter", False)
    
    async def get_country_stats(self) -> Dict[str, int]:
        """Get statistics about cached lookups by country."""
        stats = {}
        for ip_data in self.cache.values():
            country = ip_data.get("country", "Unknown")
            stats[country] = stats.get(country, 0) + 1
        return stats
    
    def close(self):
        """Close database readers."""
        try:
            if self.country_reader:
                self.country_reader.close()
            if self.city_reader:
                self.city_reader.close()
            if self.asn_reader:
                self.asn_reader.close()
        except Exception as e:
            print(f"Error closing MaxMind readers: {e}")


# Global instance
maxmind_service = MaxMindGeolocationService()


async def enhanced_ip_check(ip: str) -> Dict[str, Any]:
    """Perform comprehensive IP analysis using MaxMind databases."""
    if not ip:
        return {}
    
    try:
        # Get comprehensive IP info from MaxMind
        ip_info = await maxmind_service.get_ip_info(ip)
        
        if "error" in ip_info:
            return {"error": ip_info["error"]}
        
        # Extract risk factors
        risk_factors = {
            "high_risk_country": ip_info.get("is_high_risk_country", False),
            "hosting_provider": ip_info.get("is_hosting_provider", False),
            "private_ip": ip_info.get("is_private", False),
            "datacenter": ip_info.get("is_datacenter", False)
        }
        
        return {
            "ip_info": ip_info,
            "is_high_risk_country": risk_factors["high_risk_country"],
            "is_hosting_provider": risk_factors["hosting_provider"] or risk_factors["datacenter"],
            "risk_factors": risk_factors,
            "geolocation": {
                "country": ip_info.get("country"),
                "country_code": ip_info.get("country_code"),
                "region": ip_info.get("region"),
                "city": ip_info.get("city"),
                "latitude": ip_info.get("latitude"),
                "longitude": ip_info.get("longitude"),
                "timezone": ip_info.get("timezone")
            },
            "network": {
                "asn": ip_info.get("asn"),
                "isp": ip_info.get("isp"),
                "organization": ip_info.get("organization")
            }
        }
        
    except Exception as e:
        print(f"Enhanced IP check error for {ip}: {e}")
        return {"error": str(e)}