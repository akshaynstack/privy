# tests/conftest.py
"""Pytest configuration and fixtures for Privy API tests."""

import asyncio
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
import os

from app.main import app
from app.db import get_session
from app.config import settings

# Test database URL (use SQLite for tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,  # Set to True for SQL debugging
    future=True
)

TestAsyncSession = sessionmaker(
    test_engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)


@pytest_asyncio.fixture
async def async_session():
    """Create a test database session."""
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    
    async with TestAsyncSession() as session:
        yield session
    
    # Clean up
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)


@pytest.fixture
def client(async_session):
    """Create a test client with database session override."""
    
    async def get_test_session():
        yield async_session
    
    app.dependency_overrides[get_session] = get_test_session
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
def test_user_data():
    """Sample user data for testing."""
    return {
        "email": "testuser@example.com",
        "password": "testpassword123"
    }


@pytest.fixture
def test_org_data():
    """Sample organization data for testing."""
    return {
        "name": "Test Organization"
    }


@pytest.fixture
def test_check_data():
    """Sample check data for testing."""
    return {
        "email": "suspicious@tempmail.com",
        "ip": "192.168.1.1",
        "user_agent": "Mozilla/5.0 (Test Browser)",
        "metadata": {"source": "test"}
    }


@pytest.fixture
def sample_api_key():
    """Generate a sample API key for testing."""
    return "test_key_id.test_secret_value"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Mock Redis for testing
class MockRedis:
    """Mock Redis client for testing."""
    
    def __init__(self):
        self.data = {}
        self.sets = {}
    
    async def get(self, key):
        return self.data.get(key)
    
    async def set(self, key, value):
        self.data[key] = value
        return True
    
    async def sismember(self, set_name, value):
        return value in self.sets.get(set_name, set())
    
    async def sadd(self, set_name, *values):
        if set_name not in self.sets:
            self.sets[set_name] = set()
        self.sets[set_name].update(values)
        return len(values)
    
    async def eval(self, script, keys=None, args=None):
        # Mock rate limiter always allows requests in tests
        return 1
    
    async def ping(self):
        return True
    
    async def close(self):
        pass


@pytest.fixture
def mock_redis():
    """Mock Redis instance for testing."""
    return MockRedis()