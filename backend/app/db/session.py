import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG, pool_size=20, max_overflow=10)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    try:
        from app.db.base import Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created/verified successfully")
    except Exception as e:
        logger.warning(f"create_all failed, trying alembic: {e}")
        try:
            from alembic.config import Config
            from alembic.command import upgrade
            alembic_cfg = Config("alembic.ini")
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, upgrade, alembic_cfg, "head")
        except Exception as e2:
            logger.error(f"Both create_all and alembic failed: {e2}")
