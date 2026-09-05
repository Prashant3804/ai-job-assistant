from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.core.config import settings
from app.database.base import Base

import logging
logger = logging.getLogger(__name__)

try:
    db_url = settings.get_db_url()
except Exception as e:
    logger.error("Failed to parse or normalize database connection URL from settings.")
    raise RuntimeError("Invalid database configuration. Please verify your DATABASE_URL environment variable.") from None

# Configure engine kwargs depending on dialect
engine_kwargs = {"echo": False}
if "sqlite" in db_url:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # PostgreSQL / Cloud managed database settings
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20

try:
    async_engine = create_async_engine(db_url, **engine_kwargs)
except Exception as e:
    logger.error("Failed to initialize SQLAlchemy async database engine.")
    raise RuntimeError("Could not initialize database connection engine. Please check your DATABASE_URL.") from None

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def init_db() -> None:
    # Import all models to ensure they are registered with DeclarativeBase before creating tables
    import app.database.models  # noqa: F401
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
