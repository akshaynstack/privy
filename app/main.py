# app/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

from app.api.routes import router as api_router
from app.db import init_db
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager - handles startup and shutdown events."""
    # Startup
    print("🚀 Starting Privy Fraud Detection API...")
    
    # Initialize database tables
    try:
        await init_db()
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise
    
    # Test Redis connection
    try:
        import aioredis
        redis = aioredis.from_url(settings.redis_url, decode_responses=True)
        await redis.ping()
        await redis.close()
        print("✅ Redis connection successful")
    except Exception as e:
        print(f"⚠️  Redis connection failed: {e}")
    
    print(f"🌐 API server starting on {settings.api_host}:{settings.api_port}")
    print(f"📚 Documentation available at: http://{settings.api_host}:{settings.api_port}/docs")
    
    yield
    
    # Shutdown
    print("👋 Shutting down Privy API...")


# Create FastAPI application
app = FastAPI(
    title="Privy - Fraud Detection API",
    description="""
    🛡️ **Privy** provides real-time fraud detection and risk scoring for user signups.
    
    ## Features
    
    - **Email Validation**: Detect disposable emails and suspicious domains
    - **IP Intelligence**: Identify VPNs, proxies, and Tor exit nodes  
    - **Risk Scoring**: Configurable scoring with multiple detection methods
    - **Rate Limiting**: Token bucket rate limiting per API key
    - **Custom Blacklists**: Organization-specific blocking rules
    - **Analytics**: Comprehensive logging and reporting
    
    ## Authentication
    
    All endpoints require an API key in the `X-API-Key` header:
    ```
    X-API-Key: {key_id}.{secret}
    ```
    
    ## Rate Limits
    
    - **Default**: 60 requests per minute per API key
    - **Burst**: Up to 60 tokens in bucket  
    - **Refill**: 1 token per second
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="")


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint - API health check."""
    return {
        "message": "🛡️ Privy Fraud Detection API",
        "version": "1.0.0",
        "status": "healthy",
        "docs": "/docs"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed health check endpoint."""
    health_status = {
        "status": "healthy",
        "version": "1.0.0",
        "environment": settings.environment,
        "services": {}
    }
    
    # Check database connection
    try:
        from app.db import engine
        from sqlalchemy import text
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        health_status["services"]["database"] = "healthy"
    except Exception as e:
        health_status["services"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check Redis connection
    try:
        import aioredis
        redis = aioredis.from_url(settings.redis_url, decode_responses=True)
        await redis.ping()
        await redis.close()
        health_status["services"]["redis"] = "healthy"
    except Exception as e:
        health_status["services"]["redis"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
        
    return health_status


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug"
    )