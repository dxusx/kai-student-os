"""
Unit tests for Database layer and CRUD operations.
Verifies Subject and Task models, async session, relationships, and queries.
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from database.models import Base, Subject, Task
from database import crud


async def test_database_crud():
    # Use in-memory SQLite database for clean test isolation
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False, future=True)
    async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        # 1. Subject get or create
        subj1 = await crud.get_or_create_subject(session, name="Физика", teacher="Шарипова А. А.")
        assert subj1.id is not None
        assert subj1.name == "Физика"
        assert subj1.teacher == "Шарипова А. А."

        # Fetch same subject again -> should return existing
        subj1_dup = await crud.get_or_create_subject(session, name="Физика")
        assert subj1_dup.id == subj1.id

        # Create second subject
        subj2 = await crud.get_or_create_subject(session, name="Информатика", teacher="Иванов И. И.")
        all_subjects = await crud.get_subjects(session)
        assert len(all_subjects) == 2

        # 2. Task creation
        dl = datetime.now() + timedelta(days=3)
        task1 = await crud.create_task(
            session=session,
            subject_id=subj1.id,
            title="Лабораторная работа №1 (Маятник)",
            task_type="лаба",
            deadline=dl,
            status="todo",
            source="kai",
            details="Оформить отчет и графики"
        )
        assert task1.id is not None
        assert task1.status == "todo"

        task2 = await crud.create_task(
            session=session,
            subject_id=subj2.id,
            title="Конспект лекции 1",
            task_type="конспект",
            status="done"
        )
        assert task2.id is not None

        # 3. Task queries and filtering
        todo_tasks = await crud.get_tasks(session, status="todo")
        assert len(todo_tasks) == 1
        assert todo_tasks[0].title == "Лабораторная работа №1 (Маятник)"
        assert todo_tasks[0].subject.name == "Физика"

        done_tasks = await crud.get_tasks(session, status="done")
        assert len(done_tasks) == 1
        assert done_tasks[0].subject.name == "Информатика"

        # Filter by subject
        physics_tasks = await crud.get_tasks(session, subject_id=subj1.id)
        assert len(physics_tasks) == 1

        # 4. Update task status
        updated_task = await crud.update_task_status(session, task1.id, status="done")
        assert updated_task is not None
        assert updated_task.status == "done"

        remaining_todo = await crud.get_tasks(session, status="todo")
        assert len(remaining_todo) == 0

        # 5. Delete task
        deleted = await crud.delete_task(session, task1.id)
        assert deleted is True

        fetch_deleted = await crud.get_task_by_id(session, task1.id)
        assert fetch_deleted is None

    await engine.dispose()
    print("Database CRUD tests passed successfully!")


if __name__ == "__main__":
    asyncio.run(test_database_crud())
