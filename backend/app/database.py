"""
TaxShield — Database Configuration
Async SQLAlchemy engine and session setup.
Supports SQLite (dev) and PostgreSQL (production).
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import settings

# Convert sync URL to async URL if needed
db_url = settings.DATABASE_URL
if db_url.startswith("sqlite:///"):
    # SQLite needs the aiosqlite driver for async
    db_url = db_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
elif db_url.startswith("postgresql://"):
    # PostgreSQL needs asyncpg driver for async
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

# Create async engine
engine = create_async_engine(
    db_url,
    echo=settings.DEBUG,
    future=True
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Create base class for models
Base = declarative_base()


async def get_db():
    """Get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

