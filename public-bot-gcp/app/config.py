from typing import Optional
from pydantic import PostgresDsn, RedisDsn, validator, AnyUrl
from pydantic_settings import BaseSettings
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    # Application Settings
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # Database Settings
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    
    # Redis Settings
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_SESSION_TTL: int = int(os.getenv("REDIS_SESSION_TTL", "86400"))  
    
    # OpenAI Settings
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # Connection Pool Settings
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "20"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "10"))
    
    # Validate database URL format
    @validator("DATABASE_URL", pre=True)
    def validate_database_url(cls, v: Optional[str]) -> str:
        if not v:
            raise ValueError("DATABASE_URL is not set in environment variables")
        if not v.startswith(("postgresql://", "postgresql+asyncpg://")):
            raise ValueError("DATABASE_URL must start with postgresql:// or postgresql+asyncpg://")
        # Ensure asyncpg driver is used for async operations
        if v.startswith("postgresql://"):
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v
    
    # Validate Redis URL format
    @validator("REDIS_URL", pre=True)
    def validate_redis_url(cls, v: Optional[str]) -> str:
        if not v:
            raise ValueError("REDIS_URL is not set in environment variables")
        if not v.startswith(("redis://", "rediss://")):
            raise ValueError("REDIS_URL must start with redis:// or rediss://")
        return v

    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

# Create settings instance
settings = Settings()