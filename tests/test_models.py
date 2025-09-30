# tests/test_models.py
"""Tests for database models."""

import pytest
from datetime import datetime
from app.models import User, Organization, ApiKey, Check, Blacklist


class TestModels:
    """Test cases for SQLModel database models."""
    
    def test_user_model_creation(self):
        """Test User model creation and validation."""
        user = User(
            email="test@example.com",
            password_hash="hashed_password"
        )
        
        assert user.email == "test@example.com"
        assert user.password_hash == "hashed_password"
        assert isinstance(user.created_at, datetime)
        assert user.id is not None  # UUID should be generated
    
    def test_organization_model_creation(self):
        """Test Organization model creation."""
        org = Organization(
            name="Test Org",
            owner_id="user-123"
        )
        
        assert org.name == "Test Org"
        assert org.owner_id == "user-123"
        assert isinstance(org.created_at, datetime)
        assert org.id is not None
    
    def test_api_key_model_creation(self):
        """Test ApiKey model creation."""
        api_key = ApiKey(
            name="Test Key",
            key_id="test_key_123",
            hashed_secret="hashed_secret",
            org_id="org-123"
        )
        
        assert api_key.name == "Test Key"
        assert api_key.key_id == "test_key_123"
        assert api_key.hashed_secret == "hashed_secret"
        assert api_key.org_id == "org-123"
        assert api_key.revoked is False  # Default value
        assert isinstance(api_key.created_at, datetime)
    
    def test_check_model_creation(self):
        """Test Check model creation."""
        check = Check(
            org_id="org-123",
            ip="192.168.1.1",
            email="test@example.com",
            user_agent="Test Browser",
            result={"risk_score": 50, "reasons": ["test"]},
            risk_score=50,
            action="monitor"
        )
        
        assert check.org_id == "org-123"
        assert check.ip == "192.168.1.1"
        assert check.email == "test@example.com"
        assert check.result["risk_score"] == 50
        assert check.risk_score == 50
        assert check.action == "monitor"
        assert isinstance(check.created_at, datetime)
    
    def test_blacklist_model_creation(self):
        """Test Blacklist model creation."""
        blacklist = Blacklist(
            org_id="org-123",
            type="ip",
            value="192.168.1.100",
            reason="Suspicious activity"
        )
        
        assert blacklist.org_id == "org-123"
        assert blacklist.type == "ip"
        assert blacklist.value == "192.168.1.100"
        assert blacklist.reason == "Suspicious activity"
        assert isinstance(blacklist.created_at, datetime)
    
    def test_model_relationships(self):
        """Test that models can reference each other properly."""
        # This is more of a structure test since we don't have explicit relationships defined
        user = User(email="owner@example.com")
        org = Organization(name="Test Org", owner_id=user.id)
        api_key = ApiKey(
            name="Test Key",
            key_id="key123",
            hashed_secret="secret",
            org_id=org.id
        )
        
        # Verify the relationships work at the ID level
        assert api_key.org_id == org.id
        assert org.owner_id == user.id
    
    def test_uuid_generation(self):
        """Test that UUIDs are properly generated and unique."""
        user1 = User(email="user1@example.com")
        user2 = User(email="user2@example.com")
        
        assert user1.id != user2.id
        assert len(user1.id) > 0
        assert len(user2.id) > 0
        assert isinstance(user1.id, str)
        assert isinstance(user2.id, str)