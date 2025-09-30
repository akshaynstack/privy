# app/config.py
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List, Optional
import os
from pathlib import Path


class Settings(BaseSettings):
    """Application settings and configuration."""
    
    # Application settings
    app_name: str = "Privy Fraud Detection API"
    version: str = "1.0.0"
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=True, alias="DEBUG")
    
    # API settings
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    allowed_origins: List[str] = Field(default=["http://localhost:3000", "http://localhost:8000"], alias="ALLOWED_ORIGINS")
    
    # Database settings
    database_url: str = Field(default="postgresql+asyncpg://postgres:postgres@localhost:5432/privy", alias="DATABASE_URL")
    database_url_sync: str = Field(default="postgresql+psycopg://postgres:postgres@localhost:5432/privy", alias="DATABASE_URL_SYNC")
    
    # Redis settings
    redis_url: str = Field(default="redis://localhost:6379", alias="REDIS_URL")
    
    # Celery settings
    celery_broker: str = Field(default="redis://localhost:6379/0", alias="CELERY_BROKER")
    celery_backend: str = Field(default="redis://localhost:6379/1", alias="CELERY_BACKEND")
    
    # Security settings
    secret_key: str = Field(default="your-secret-key-change-this-in-production", alias="SECRET_KEY")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Rate limiting defaults
    default_rate_limit: float = 1.0  # requests per second
    default_rate_capacity: int = 60  # max burst tokens
    
    # External data sources
    disposable_email_url: str = "https://raw.githubusercontent.com/disposable/disposable-email-domains/master/domains.txt"
    
    # MaxMind GeoLite2 License Key
    maxmind_license_key: Optional[str] = Field(default=None, alias="MAXMIND_LICENSE_KEY")
    maxmind_db_path: Optional[str] = Field(default=None, alias="MAXMIND_DB_PATH")
    
    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    
    # Feature flags
    enable_analytics: bool = True
    enable_background_tasks: bool = True
    enable_custom_blacklists: bool = True
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields instead of raising errors
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment.lower() in ["development", "dev", "local"]
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment.lower() in ["production", "prod"]
    
    @property
    def is_testing(self) -> bool:
        """Check if running in testing mode."""
        return self.environment.lower() in ["testing", "test"]
    
    def get_database_url(self, sync: bool = False) -> str:
        """Get the appropriate database URL."""
        if sync:
            return self.database_url_sync
        return self.database_url
    
    def validate_settings(self) -> bool:
        """Validate critical settings."""
        errors = []
        
        if not self.database_url:
            errors.append("DATABASE_URL is required")
            
        if not self.redis_url:
            errors.append("REDIS_URL is required")
            
        if self.is_production and self.secret_key == "your-secret-key-change-this-in-production":
            errors.append("SECRET_KEY must be changed in production")
            
        if errors:
            raise ValueError(f"Configuration validation failed: {', '.join(errors)}")
            
        return True


# Create global settings instance
settings = Settings()

# Validate settings on import
if not settings.is_testing:
    try:
        settings.validate_settings()
    except ValueError as e:
        print(f"Configuration error: {e}")
        raise


# Export commonly used values
DATABASE_URL = settings.database_url
DATABASE_URL_SYNC = settings.database_url_sync
REDIS_URL = settings.redis_url
SECRET_KEY = settings.secret_key
DEBUG = settings.debug