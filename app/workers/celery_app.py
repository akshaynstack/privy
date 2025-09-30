# app/workers/celery_app.py
from celery import Celery
import os

CELERY_BROKER = os.getenv("CELERY_BROKER", "redis://redis:6379/0")
CELERY_BACKEND = os.getenv("CELERY_BACKEND", "redis://redis:6379/1")

celery_app = Celery("signupgate", broker=CELERY_BROKER, backend=CELERY_BACKEND)
celery_app.conf.task_routes = {"app.workers.tasks.*": {"queue": "default"}}