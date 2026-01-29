"""
Database connection and session management.
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


# Convert sync URL to async
DATABASE_URL = settings.database_url.replace(
    "postgresql://", "postgresql+asyncpg://"
)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set True for SQL debugging
    pool_size=5,
    max_overflow=10,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""
    pass


async def get_db() -> AsyncSession:
    """Dependency for getting database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
