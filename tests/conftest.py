"""
Pytest configuration and shared fixtures for KAI Student OS test suite.
Ensures deterministic environment variables and database initialization.
"""

import os
import asyncio
from pathlib import Path
import pytest

# Ensure test auth token is present for test sessions
os.environ.setdefault("APP_AUTH_TOKEN", "test_qa_master_key_2026")
os.environ.setdefault("ENABLE_TUNNEL", "false")

from core.config import settings
if not settings.app_auth_token:
    settings.app_auth_token = "test_qa_master_key_2026"

from database.connection import init_db, async_session
from database import crud


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Ensure database schema and basic reference data exist."""
    async def _init():
        await init_db()
        async with async_session() as session:
            subjs = await crud.get_subjects(session)
            if not subjs:
                await crud.get_or_create_subject(session, name="Высшая математика", teacher="Иванов И. И.")
                await crud.get_or_create_subject(session, name="Физика", teacher="Петров П. П.")
    asyncio.run(_init())
