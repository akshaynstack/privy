# app/api/routes.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import verify_api_key
from app.services.scoring import compute_score
from app.db import get_session
from app.services.rate_limiter import RateLimiter
from app.models import ApiKey
import aioredis
import os
import json

router = APIRouter()

# Initialize Redis connection
redis = None
rate_limiter = None


class CheckIn(BaseModel):
    """Input model for fraud check requests."""
    ip: str | None = None
    email: str | None = None
    user_agent: str | None = None
    metadata: dict | None = None


class CheckResponse(BaseModel):
    """Response model for fraud check results."""
    success: bool
    data: dict


@router.on_event("startup")
async def startup_event():
    """Initialize Redis connection on startup."""
    global redis, rate_limiter
    from app.config import settings
    
    try:
        redis = aioredis.from_url(settings.redis_url, decode_responses=True)
        rate_limiter = RateLimiter(redis)
        await redis.ping()  # Test connection
        print("✅ Redis connection established")
    except Exception as e:
        print(f"⚠️  Redis connection failed: {e}")
        # Continue without Redis for development
        redis = None
        rate_limiter = None


@router.post("/v1/check", response_model=CheckResponse)
async def check(
    payload: CheckIn,
    api_key: ApiKey = Depends(verify_api_key),
    session: AsyncSession = Depends(get_session)
):
    """Perform real-time fraud detection check.
    
    This endpoint analyzes the provided data points (IP, email, user agent)
    and returns a risk score with recommended action.
    
    **Rate Limits**: 60 requests per minute per API key
    
    **Risk Levels**:
    - **none** (0-29): Safe to proceed
    - **low** (30-59): Monitor closely  
    - **medium** (60-79): Challenge user (CAPTCHA, 2FA)
    - **high** (80-100): Block or manual review
    """
    
    # 1) Rate limiting check
    if rate_limiter:
        try:
            allowed = await rate_limiter.allow_request(
                api_key.key_id, 
                rate=1.0,  # 1 request per second
                capacity=60  # 60 requests burst
            )
            if not allowed:
                raise HTTPException(
                    status_code=429, 
                    detail="Rate limit exceeded. Please wait before making more requests."
                )
        except Exception as e:
            # Log the error but don't fail the request
            print(f"Rate limiting error: {e}")
    
    # 2) Fast Redis-based checks
    hits = []
    
    if redis:
        try:
            # Check disposable email domains
            if payload.email:
                domain = payload.email.split("@")[-1].lower()
                if await redis.sismember("disposable_email_domains", domain):
                    hits.append("disposable_email")
            
            # Check VPN/Proxy IPs
            if payload.ip:
                if await redis.sismember("vpn_ips", payload.ip):
                    hits.append("vpn_ip")
                if await redis.sismember("tor_exit_nodes", payload.ip):
                    hits.append("tor_exit")
            
        except Exception as e:
            print(f"Redis lookup error: {e}")
            # Continue without Redis checks
    
    # 2.5) Enhanced IP geolocation checks
    if payload.ip:
        try:
            from app.services.geolocation import enhanced_ip_check
            ip_analysis = await enhanced_ip_check(payload.ip)
            
            if ip_analysis.get("is_high_risk_country"):
                hits.append("high_risk_country")
            if ip_analysis.get("is_hosting_provider"):
                hits.append("bad_isp")
                
        except Exception as e:
            print(f"Geolocation check error: {e}")
            # Continue without geolocation checks
    
    # 3) Check custom organization blacklists
    if api_key.org_id:
        from app.crud import BlacklistCRUD
        
        try:
            # Check if IP is blacklisted
            if payload.ip:
                if await BlacklistCRUD.is_blacklisted(session, api_key.org_id, "ip", payload.ip):
                    hits.append("custom_blacklist")
            
            # Check if email domain is blacklisted
            if payload.email:
                domain = payload.email.split("@")[-1].lower()
                if await BlacklistCRUD.is_blacklisted(session, api_key.org_id, "email_domain", domain):
                    hits.append("custom_blacklist")
        except Exception as e:
            print(f"Blacklist check error: {e}")
    
    # 4) Compute risk score with enhanced analysis
    score, level, reasons = compute_score(hits, payload.email, payload.ip)
    
    # Get detailed recommendations
    from app.services.scoring import get_action_recommendations, get_risk_explanation
    action_details = get_action_recommendations(score)
    
    result = {
        "risk_score": score,
        "risk_level": level,
        "reasons": reasons,
        "action": action_details["action"],
        "message": action_details["message"],
        "explanation": get_risk_explanation(score, level),
        "recommendations": action_details["recommendations"]
    }
    
    # 5) Enqueue background DB write (non-blocking)
    try:
        from app.workers.tasks import persist_check
        persist_check.delay({
            "org_id": api_key.org_id,
            "ip": payload.ip,
            "email": payload.email,
            "user_agent": payload.user_agent,
            "result": result,
            "risk_score": score,
            "action": result["action"]
        })
    except Exception as e:
        print(f"Background task error: {e}")
        # Continue without background logging
    
    return CheckResponse(success=True, data=result)


def determine_action(score: int) -> str:
    """Determine recommended action based on risk score."""
    if score >= 80:
        return "block"
    elif score >= 60:
        return "challenge"
    elif score >= 30:
        return "monitor"
    else:
        return "allow"


@router.get("/v1/status")
async def api_status():
    """Get API status and version information."""
    from app.config import settings
    
    status_info = {
        "service": "Privy Fraud Detection API",
        "version": "1.0.0",
        "environment": settings.environment,
        "debug": settings.debug,
        "features": {
            "redis_cache": redis is not None,
            "rate_limiting": rate_limiter is not None,
            "background_tasks": settings.enable_background_tasks,
            "custom_blacklists": settings.enable_custom_blacklists
        }
    }
    
    return status_info