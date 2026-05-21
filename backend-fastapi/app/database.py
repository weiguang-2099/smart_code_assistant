"""
Database connection and session management for Smart Code Assistant.
"""
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

from app.core.config import settings

logger = logging.getLogger(__name__)

# In testing/CI environments DATABASE_URL may be empty; provide a fallback so
# that create_async_engine() does not crash on module import.
_db_url = settings.DATABASE_URL or "sqlite+aiosqlite:///./test.db"

engine = create_async_engine(
    _db_url,
    echo=settings.FASTAPI_ENV == "development",
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()

_query_monitoring_enabled = False


def enable_query_monitoring() -> None:
    """Enable query performance monitoring."""
    global _query_monitoring_enabled
    if _query_monitoring_enabled:
        return

    try:
        from app.core.query_analyzer import setup_query_monitoring
        setup_query_monitoring(engine)
        _query_monitoring_enabled = True
        logger.info("Query monitoring enabled")
    except Exception as e:
        logger.warning(f"Failed to enable query monitoring: {e}")


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
        from app.models import user, project, code_file, document, user_profile  # noqa: F401

        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """
    Close database connections.
    """
    await engine.dispose()
