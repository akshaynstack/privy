# app/db.py
import os
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager

from app.config import settings

# Create async engine
engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    future=True,
    echo=settings.debug  # Enable SQL logging in debug mode
)

# Create async session factory
AsyncSessionLocal = sessionmaker(
    engine, 
    expire_on_commit=False, 
    class_=AsyncSession
)


async def init_db():
    """Initialize database tables."""
    # Import all models to ensure they're registered with SQLModel.metadata
    import app.models  # This imports all models
    
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(SQLModel.metadata.create_all)


@asynccontextmanager
async def get_session():
    """Get database session context manager."""
    async with AsyncSessionLocal() as session:
        yield session