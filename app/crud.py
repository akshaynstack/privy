# app/crud.py
from typing import Optional, List, Dict, Any
from sqlmodel import Session, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
import secrets
import string
from passlib.context import CryptContext

from app.models import User, Organization, ApiKey, Check, Blacklist


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def generate_api_key() -> tuple[str, str]:
    """Generate a new API key pair (key_id, secret)."""
    # Generate public key_id (shorter, URL-safe)
    key_id = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))
    
    # Generate secret (longer, more secure)
    secret = ''.join(secrets.choice(string.ascii_letters + string.digits + '-_') for _ in range(32))
    
    return key_id, secret


class UserCRUD:
    """CRUD operations for User model."""
    
    @staticmethod
    async def create(session: AsyncSession, email: str, password: Optional[str] = None) -> User:
        """Create a new user."""
        password_hash = pwd_context.hash(password) if password else None
        
        user = User(
            email=email.lower().strip(),
            password_hash=password_hash
        )
        
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user
    
    @staticmethod
    async def get_by_id(session: AsyncSession, user_id: str) -> Optional[User]:
        """Get user by ID."""
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_by_email(session: AsyncSession, email: str) -> Optional[User]:
        """Get user by email."""
        stmt = select(User).where(User.email == email.lower().strip())
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def update_password(session: AsyncSession, user_id: str, new_password: str) -> bool:
        """Update user password."""
        user = await UserCRUD.get_by_id(session, user_id)
        if not user:
            return False
            
        user.password_hash = pwd_context.hash(new_password)
        await session.commit()
        return True
    
    @staticmethod
    async def verify_password(user: User, password: str) -> bool:
        """Verify user password."""
        if not user.password_hash:
            return False
        return pwd_context.verify(password, user.password_hash)


class OrganizationCRUD:
    """CRUD operations for Organization model."""
    
    @staticmethod
    async def create(session: AsyncSession, name: str, owner_id: str) -> Organization:
        """Create a new organization."""
        org = Organization(
            name=name.strip(),
            owner_id=owner_id
        )
        
        session.add(org)
        await session.commit()
        await session.refresh(org)
        return org
    
    @staticmethod
    async def get_by_id(session: AsyncSession, org_id: str) -> Optional[Organization]:
        """Get organization by ID."""
        stmt = select(Organization).where(Organization.id == org_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_by_owner(session: AsyncSession, owner_id: str) -> List[Organization]:
        """Get all organizations owned by a user."""
        stmt = select(Organization).where(Organization.owner_id == owner_id)
        result = await session.execute(stmt)
        return result.scalars().all()


class ApiKeyCRUD:
    """CRUD operations for ApiKey model."""
    
    @staticmethod
    async def create(session: AsyncSession, name: str, org_id: str) -> tuple[ApiKey, str]:
        """Create a new API key and return the key with its secret."""
        key_id, secret = generate_api_key()
        hashed_secret = pwd_context.hash(secret)
        
        api_key = ApiKey(
            name=name.strip() if name else None,
            key_id=key_id,
            hashed_secret=hashed_secret,
            org_id=org_id
        )
        
        session.add(api_key)
        await session.commit()
        await session.refresh(api_key)
        
        # Return the full key string that client will use
        full_key = f"{key_id}.{secret}"
        return api_key, full_key
    
    @staticmethod
    async def get_by_key_id(session: AsyncSession, key_id: str) -> Optional[ApiKey]:
        """Get API key by key_id."""
        stmt = select(ApiKey).where(
            ApiKey.key_id == key_id,
            ApiKey.revoked == False
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_by_org(session: AsyncSession, org_id: str) -> List[ApiKey]:
        """Get all API keys for an organization."""
        stmt = select(ApiKey).where(ApiKey.org_id == org_id)
        result = await session.execute(stmt)
        return result.scalars().all()
    
    @staticmethod
    async def revoke(session: AsyncSession, key_id: str) -> bool:
        """Revoke an API key."""
        api_key = await ApiKeyCRUD.get_by_key_id(session, key_id)
        if not api_key:
            return False
            
        api_key.revoked = True
        await session.commit()
        return True
    
    @staticmethod
    def verify_secret(api_key: ApiKey, secret: str) -> bool:
        """Verify API key secret."""
        return pwd_context.verify(secret, api_key.hashed_secret)


class CheckCRUD:
    """CRUD operations for Check model."""
    
    @staticmethod
    async def create(session: AsyncSession, **kwargs) -> Check:
        """Create a new check record."""
        check = Check(**kwargs)
        session.add(check)
        await session.commit()
        await session.refresh(check)
        return check
    
    @staticmethod
    async def get_by_id(session: AsyncSession, check_id: str) -> Optional[Check]:
        """Get check by ID."""
        stmt = select(Check).where(Check.id == check_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_by_org(session: AsyncSession, org_id: str, limit: int = 100, offset: int = 0) -> List[Check]:
        """Get checks for an organization with pagination."""
        stmt = (
            select(Check)
            .where(Check.org_id == org_id)
            .order_by(Check.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await session.execute(stmt)
        return result.scalars().all()
    
    @staticmethod
    async def get_recent_by_ip(session: AsyncSession, ip: str, hours: int = 24) -> List[Check]:
        """Get recent checks for an IP address."""
        since = datetime.utcnow() - timedelta(hours=hours)
        stmt = (
            select(Check)
            .where(Check.ip == ip, Check.created_at >= since)
            .order_by(Check.created_at.desc())
        )
        result = await session.execute(stmt)
        return result.scalars().all()
    
    @staticmethod
    async def get_stats_by_org(session: AsyncSession, org_id: str, days: int = 30) -> Dict[str, Any]:
        """Get check statistics for an organization."""
        since = datetime.utcnow() - timedelta(days=days)
        
        # This would be more complex in a real implementation
        # For now, return basic counts
        stmt = select(Check).where(
            Check.org_id == org_id,
            Check.created_at >= since
        )
        result = await session.execute(stmt)
        checks = result.scalars().all()
        
        total_checks = len(checks)
        high_risk = len([c for c in checks if c.risk_score and c.risk_score >= 80])
        medium_risk = len([c for c in checks if c.risk_score and 60 <= c.risk_score < 80])
        low_risk = len([c for c in checks if c.risk_score and 30 <= c.risk_score < 60])
        safe = len([c for c in checks if c.risk_score and c.risk_score < 30])
        
        return {
            "total_checks": total_checks,
            "high_risk": high_risk,
            "medium_risk": medium_risk,
            "low_risk": low_risk,
            "safe": safe,
            "period_days": days
        }


class BlacklistCRUD:
    """CRUD operations for Blacklist model."""
    
    @staticmethod
    async def create(session: AsyncSession, org_id: str, type_: str, value: str, reason: Optional[str] = None) -> Blacklist:
        """Create a new blacklist entry."""
        blacklist = Blacklist(
            org_id=org_id,
            type=type_,
            value=value.lower().strip(),
            reason=reason
        )
        
        session.add(blacklist)
        await session.commit()
        await session.refresh(blacklist)
        return blacklist
    
    @staticmethod
    async def get_by_org_and_type(session: AsyncSession, org_id: str, type_: str) -> List[Blacklist]:
        """Get blacklist entries by organization and type."""
        stmt = select(Blacklist).where(
            Blacklist.org_id == org_id,
            Blacklist.type == type_
        )
        result = await session.execute(stmt)
        return result.scalars().all()
    
    @staticmethod
    async def is_blacklisted(session: AsyncSession, org_id: str, type_: str, value: str) -> bool:
        """Check if a value is blacklisted."""
        stmt = select(Blacklist).where(
            Blacklist.org_id == org_id,
            Blacklist.type == type_,
            Blacklist.value == value.lower().strip()
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none() is not None
    
    @staticmethod
    async def delete(session: AsyncSession, blacklist_id: str) -> bool:
        """Delete a blacklist entry."""
        stmt = select(Blacklist).where(Blacklist.id == blacklist_id)
        result = await session.execute(stmt)
        blacklist = result.scalar_one_or_none()
        
        if not blacklist:
            return False
            
        await session.delete(blacklist)
        await session.commit()
        return True