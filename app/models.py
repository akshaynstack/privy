# app/models.py
from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field
from sqlalchemy import JSON, Column
from uuid import uuid4

def gen_uuid():
    return str(uuid4())

class User(SQLModel, table=True):
    id: str = Field(default_factory=gen_uuid, primary_key=True)
    email: str
    password_hash: Optional[str]
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Organization(SQLModel, table=True):
    id: str = Field(default_factory=gen_uuid, primary_key=True)
    name: str
    owner_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ApiKey(SQLModel, table=True):
    id: str = Field(default_factory=gen_uuid, primary_key=True)       # numeric id for lookups
    name: Optional[str]
    key_id: str = Field(index=True, nullable=False, unique=True)      # public id part
    hashed_secret: str                                                # hashed secret (bcrypt)
    org_id: Optional[str] = None
    revoked: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Check(SQLModel, table=True):
    id: str = Field(default_factory=gen_uuid, primary_key=True)
    org_id: Optional[str] = None
    ip: Optional[str] = None
    email: Optional[str] = None
    user_agent: Optional[str] = None
    result: Optional[dict] = Field(default=None, sa_column=Column(JSON))   # jsonb
    risk_score: Optional[int] = None
    action: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Blacklist(SQLModel, table=True):
    id: str = Field(default_factory=gen_uuid, primary_key=True)
    org_id: Optional[str] = None
    type: str   # 'ip'|'email_domain'|'isp'|'asn'
    value: str
    reason: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)