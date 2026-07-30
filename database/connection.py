"""Database Connection Manager

This module provides async database connection management using SQLAlchemy,
with support for connection pooling and migrations.
"""

from __future__ import annotations

import logging
from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncEngine,
    AsyncConnection
)
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from config.settings import get_settings


logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages database connections and sessions.
    
    This class handles the lifecycle of database connections,
    providing async session management and initialization.
    """
    
    def __init__(self):
        self._engine: Optional[AsyncEngine] = None
        self._async_session_maker: Optional[async_sessionmaker] = None
        self._initialized: bool = False
    
    async def initialize(self) -> None:
        """Initialize the database engine and session maker."""
        if self._initialized:
            logger.debug("Database already initialized")
            return
        
        settings = get_settings()
        
        # Determine which database URL to use
        if settings.use_sqlite:
            database_url = "sqlite+aiosqlite:///./data/bot_database.db"
            logger.info("Using SQLite database for development")
        else:
            database_url = settings.database_url
            logger.info(f"Using configured database: {database_url}")
        
        # Create engine with appropriate settings
        if settings.use_sqlite:
            self._engine = create_async_engine(
                database_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                echo=settings.log_level == "DEBUG"
            )
        else:
            self._engine = create_async_engine(
                database_url,
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=20,
                echo=settings.log_level == "DEBUG"
            )
        
        # Create session maker
        self._async_session_maker = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False
        )
        
        self._initialized = True
        logger.info("✅ Database initialized successfully")
    
    async def close(self) -> None:
        """Close all database connections."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._async_session_maker = None
            self._initialized = False
            logger.info("Database connections closed")
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get a database session context manager.
        
        Yields:
            AsyncSession: An async database session.
            
        Example:
            async with db_manager.get_session() as session:
                # Use session here
                pass
        """
        if not self._initialized:
            await self.initialize()
        
        session = self._async_session_maker()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
    
    async def create_tables(self) -> None:
        """Create all database tables."""
        if not self._initialized:
            await self.initialize()
        
        from models.database_models import Base
        
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("✅ Database tables created successfully")
    
    async def drop_tables(self) -> None:
        """Drop all database tables (use with caution!)."""
        if not self._initialized:
            await self.initialize()
        
        from models.database_models import Base
        
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        
        logger.warning("⚠️ All database tables dropped")
    
    @property
    def is_initialized(self) -> bool:
        """Check if the database is initialized."""
        return self._initialized


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_database_manager() -> DatabaseManager:
    """Get the global database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Convenience function to get a database session.
    
    Yields:
        AsyncSession: An async database session.
    """
    db_manager = get_database_manager()
    async with db_manager.get_session() as session:
        yield session
