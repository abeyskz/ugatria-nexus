"""
Database connection and initialization for PostgreSQL with pgvector
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
import logging

from app.core.config import settings
from app.models.memory import Base

logger = logging.getLogger(__name__)

# Global variables
engine = None
SessionLocal = None


async def init_db():
    """Initialize database connection and create tables"""
    global engine, SessionLocal
    
    logger.info(f"Connecting to database: {settings.database_url}")
    
    # Create async engine
    engine = create_async_engine(
        settings.database_url,
        echo=settings.DEBUG,
        pool_pre_ping=True,
        pool_recycle=3600,
    )
    
    # Create session factory
    SessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    # Create tables and enable pgvector extension
    async with engine.begin() as conn:
        # Enable pgvector extension
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            logger.info("pgvector extension enabled")
        except Exception as e:
            logger.warning(f"Could not enable pgvector extension: {e}")
        
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created")


async def close_db():
    """Close database connection"""
    global engine
    
    if engine:
        await engine.dispose()
        logger.info("Database connection closed")


async def get_db() -> AsyncSession:
    """Dependency to get database session"""
    if not SessionLocal:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    
    async with SessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()


async def execute_raw_sql(query: str, params: dict = None) -> list:
    """Execute raw SQL query"""
    if not engine:
        raise RuntimeError("Database not initialized")
    
    async with engine.begin() as conn:
        result = await conn.execute(text(query), params or {})
        return result.fetchall()


# Health check function
async def check_db_health() -> bool:
    """Check database connection health"""
    try:
        await execute_raw_sql("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
