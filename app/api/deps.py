# app/api/deps.py
from fastapi import Header, HTTPException, Depends
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db import get_session
from app.models import ApiKey
import secrets

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def verify_api_key(
    x_api_key: str = Header(..., description="API key in format: key_id.secret"),
    session: AsyncSession = Depends(get_session)
) -> ApiKey:
    """
    Verify API key from X-API-Key header.
    
    Expected format: "key_id.secret"
    Returns the ApiKey instance if valid.
    """
    try:
        key_id, secret = x_api_key.split(".", 1)
    except ValueError:
        raise HTTPException(
            status_code=401, 
            detail="Invalid API key format. Expected: key_id.secret"
        )
    
    # Look up the API key by key_id
    stmt = select(ApiKey).where(
        ApiKey.key_id == key_id,
        ApiKey.revoked == False
    )
    result = await session.execute(stmt)
    api_key = result.scalar_one_or_none()
    
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    
    # Verify the secret using the safer method
    if not ApiKeyCRUD.verify_secret(api_key, secret):
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    
    return api_key


async def get_current_session() -> AsyncSession:
    """Get current database session (alias for dependency injection)."""
    async with get_session() as session:
        yield session