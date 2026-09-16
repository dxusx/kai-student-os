from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import Subject, Task


async def get_or_create_subject(
    session: AsyncSession,
    name: str,
    teacher: Optional[str] = None
) -> Subject:
    """Fetch existing subject by name or create a new one."""
    clean_name = name.strip()
    stmt = select(Subject).where(Subject.name == clean_name)
    result = await session.execute(stmt)
    subject = result.scalar_one_or_none()

    if not subject:
        subject = Subject(name=clean_name, teacher=teacher.strip() if teacher else None)
        session.add(subject)
        await session.commit()
        await session.refresh(subject)
    elif teacher and not subject.teacher:
        subject.teacher = teacher.strip()
        await session.commit()
        await session.refresh(subject)

    return subject


async def get_subjects(session: AsyncSession) -> List[Subject]:
    """Retrieve all registered subjects."""
    stmt = select(Subject).order_by(Subject.name)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_subject_by_id(session: AsyncSession, subject_id: int) -> Optional[Subject]:
    """Retrieve subject by ID."""
    stmt = select(Subject).where(Subject.id == subject_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_task(
    session: AsyncSession,
    subject_id: int,
    title: str,
    task_type: str = "лаба",
    deadline: Optional[datetime] = None,
    status: str = "todo",
    source: str = "manual",
    details: Optional[str] = None,
    file_url: Optional[str] = None,
    file_name: Optional[str] = None,
    external_url: Optional[str] = None,
) -> Task:
    """Create and persist a new assignment task."""
    task = Task(
        subject_id=subject_id,
        title=title.strip(),
        task_type=task_type.strip(),
        deadline=deadline,
        status=status.strip().lower(),
        source=source.strip().lower(),
        details=details.strip() if details else None,
        file_url=file_url.strip() if file_url else None,
        file_name=file_name.strip() if file_name else None,
        external_url=external_url.strip() if external_url else None,
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


async def get_tasks(
    session: AsyncSession,
    status: Optional[str] = None,
    subject_id: Optional[int] = None
) -> List[Task]:
    """Retrieve tasks with optional filtering, preloading Subject."""
    stmt = select(Task).options(selectinload(Task.subject)).order_by(Task.deadline.asc().nullslast(), Task.id.desc())

    if status:
        stmt = stmt.where(Task.status == status.strip().lower())
    if subject_id is not None:
        stmt = stmt.where(Task.subject_id == subject_id)

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_task_by_id(session: AsyncSession, task_id: int) -> Optional[Task]:
    """Retrieve single task by ID with subject loaded."""
    stmt = select(Task).options(selectinload(Task.subject)).where(Task.id == task_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def update_task_status(session: AsyncSession, task_id: int, status: str) -> Optional[Task]:
    """Update task status (e.g. 'todo' -> 'done')."""
    stmt = (
        update(Task)
        .where(Task.id == task_id)
        .values(status=status.strip().lower())
        .returning(Task)
    )
    result = await session.execute(stmt)
    await session.commit()
    return result.scalar_one_or_none()


async def delete_task(session: AsyncSession, task_id: int) -> bool:
    """Delete task by ID."""
    stmt = delete(Task).where(Task.id == task_id)
    result = await session.execute(stmt)
    await session.commit()
    return bool(result.rowcount and result.rowcount > 0)


async def get_task_by_title_and_subject(
    session: AsyncSession,
    subject_id: int,
    title: str
) -> Optional[Task]:
    """Retrieve task by subject ID and title to prevent duplicate entries."""
    stmt = select(Task).where(Task.subject_id == subject_id, Task.title == title.strip())
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def clear_bb_tasks(session: AsyncSession) -> int:
    """Delete all tasks sourced from Blackboard."""
    stmt = delete(Task).where(Task.source == "bb")
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount or 0


