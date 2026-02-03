"""
Database connection and session management for Smart Code Assistant.
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

from app.core.config import settings

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.FASTAPI_ENV == "development",
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for all models
Base = declarative_base()


async def get_db() -> AsyncSession:
    """
    Dependency function to get database session.

    Yields:
        AsyncSession: Database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """
    Initialize database tables.
    This creates all tables defined in models.
    """
    async with engine.begin() as conn:
        # Import all models here to ensure they are registered with Base
        from app.models import user, project, code_file  # noqa: F401

        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """
    Close database connections.
    """
    await engine.dispose()
