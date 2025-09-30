# app/workers/tasks.py
from .celery_app import celery_app
import httpx, os, aioredis, asyncio
from app.db import engine
from sqlmodel import SQLModel
from app.models import Blacklist, Check
import json

redis = aioredis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"), decode_responses=True)

@celery_app.task
def ingest_disposable_emails(url: str):
    # synchronous worker: use httpx sync
    r = httpx.get(url, timeout=30.0)
    if r.status_code != 200:
        return False
    content = r.text.splitlines()
    # write to redis set
    # we use pipeline-like approach
    import redis as rlib
    rconn = rlib.Redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379"))
    pipe = rconn.pipeline()
    for d in content:
        d = d.strip().lower()
        if not d or d.startswith("#"):
            continue
        pipe.sadd("disposable_email_domains", d)
    pipe.execute()
    return True

@celery_app.task
def persist_check(payload: dict):
    # persist a check record to Postgres synchronously (SQLModel sync)
    from sqlalchemy import create_engine
    DATABASE_URL_SYNC = os.getenv("DATABASE_URL_SYNC", "postgresql+psycopg://postgres:postgres@db:5432/postgres")
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
        conn.execute(SQLModel.metadata.tables['check'].insert(), check.dict())
    return True