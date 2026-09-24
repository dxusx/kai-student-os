from __future__ import annotations

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.config import settings
from database.models import Base

# Create asynchronous engine
engine = create_async_engine(
    settings.database_url,
    echo=False,
    future=True
)

# Async session factory
async_session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def init_db() -> None:
    """Create all database tables if they do not exist and apply schema migrations."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        def _migrate_schema(sync_conn):
            cursor = sync_conn.connection.cursor()
            cursor.execute("PRAGMA table_info(tasks)")
            columns = [row[1] for row in cursor.fetchall()]
            if columns and "owner_id" not in columns:
                cursor.execute("ALTER TABLE tasks ADD COLUMN owner_id VARCHAR(100) DEFAULT 'student_5108'")
            if columns:
                cursor.execute("CREATE INDEX IF NOT EXISTS ix_tasks_owner_id ON tasks (owner_id)")

            cursor.execute("PRAGMA table_info(subjects)")
            sub_columns = [row[1] for row in cursor.fetchall()]
            if sub_columns and "canonical_id" not in sub_columns:
                cursor.execute("ALTER TABLE subjects ADD COLUMN canonical_id VARCHAR(50)")
            if sub_columns:
                cursor.execute("CREATE INDEX IF NOT EXISTS ix_subjects_canonical_id ON subjects (canonical_id)")

        await conn.run_sync(_migrate_schema)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency / context helper to yield an async database session."""
    async with async_session() as session:
        yield session
