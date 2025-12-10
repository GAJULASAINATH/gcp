# app/db/session.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.pool import NullPool
from app.config import settings
from app.db.base_class import Base

# Use psycopg (async) driver for better PgBouncer compatibility
# Note: Use postgresql+psycopg (not psycopg://)
DATABASE_URL = settings.DATABASE_URL.replace(
    "postgresql+asyncpg://", 
    "postgresql+psycopg://"
)

engine = create_async_engine(
    DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    poolclass=NullPool,  # NullPool is recommended with PgBouncer
    connect_args={
        "application_name": "whatsapp_bot",
        # For psycopg, we can set prepared statement settings here if needed
        "prepare_threshold": None,  # Disable prepared statements
    }
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

async def get_db():
    """Dependency function for FastAPI to get database sessions."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def init_db():
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def close_db():
    """Close database engine and clean up connections."""
    await engine.dispose()