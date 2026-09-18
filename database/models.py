from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base declarative class for all models."""
    pass


class Subject(Base):
    """Academic subject / discipline."""
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    teacher: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    tasks: Mapped[List[Task]] = relationship("Task", back_populates="subject", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Subject(id={self.id}, name='{self.name}', teacher='{self.teacher}')>"


class Task(Base):
    """Student assignment or deadline task."""
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    task_type: Mapped[str] = mapped_column(String(50), default="лаба", nullable=False)  # лаба, доклад, конспект, орг
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="todo", nullable=False)  # todo, done
    source: Mapped[str] = mapped_column(String(50), default="manual", nullable=False)  # kai, manual, bb
    file_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    external_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    owner_id: Mapped[Optional[str]] = mapped_column(String(100), default="student_5108", index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    subject: Mapped[Subject] = relationship("Subject", back_populates="tasks")
    attachments: Mapped[List[TaskAttachment]] = relationship("TaskAttachment", back_populates="task", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, title='{self.title}', owner='{self.owner_id}', status='{self.status}', deadline={self.deadline})>"


class User(Base):
    """Registered student or administrative user identity."""
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="student", nullable=False)
    group_num: Mapped[str] = mapped_column(String(20), default="5108", nullable=False)
    subgroup: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<User(id='{self.id}', username='{self.username}', role='{self.role}')>"


class TaskAttachment(Base):
    """File attachment associated with a task."""
    __tablename__ = "task_attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True, nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # relative to sandboxed STORAGE_DIR
    file_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)   # remote Blackboard or external URL
    content_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    task: Mapped[Task] = relationship("Task", back_populates="attachments")

    def __repr__(self) -> str:
        return f"<TaskAttachment(id={self.id}, task_id={self.task_id}, file_name='{self.file_name}', path='{self.file_path}')>"
