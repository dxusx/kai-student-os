"""
Test Environment & Deterministic Seed Fixtures for KAI Student OS QA Suite.
Operates with 100% isolation in data/test_qa/ on port 8899.
NEVER modifies production DB (kai_assistant.db) or touches port 8000.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import socket
import sys
import threading
import time
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import uvicorn

# Repo root
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Isolated Test Directories
TEST_DATA_DIR = REPO_ROOT / "data" / "test_qa"
TEST_DB_PATH = TEST_DATA_DIR / "kai_qa.db"
TEST_STORAGE_DIR = TEST_DATA_DIR / "attachments"
TEST_SYNC_STATE_FILE = TEST_DATA_DIR / "sync_state.json"
TEST_PORT = 8899
TEST_HOST = "127.0.0.1"
BASE_URL = f"http://{TEST_HOST}:{TEST_PORT}"

# Configure environment variables BEFORE importing core modules
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_PATH}"
os.environ["WEB_PORT"] = str(TEST_PORT)
os.environ["WEB_HOST"] = TEST_HOST
os.environ["ENABLE_TUNNEL"] = "false"
os.environ["APP_AUTH_TOKEN"] = "test_qa_master_key_2026"

from core.config import settings
# Force override settings instance values
settings.database_url = f"sqlite+aiosqlite:///{TEST_DB_PATH}"
settings.web_port = TEST_PORT
settings.web_host = TEST_HOST
settings.enable_tunnel = False
settings.app_auth_token = "test_qa_master_key_2026"

import api.app as api_module
# Patch storage and sync state in api_module
api_module.STORAGE_DIR = TEST_STORAGE_DIR
api_module.SYNC_STATE_FILE = TEST_SYNC_STATE_FILE

from sqlalchemy import delete, select
from database.connection import async_session, engine, init_db
from database.crud import (
    create_task,
    create_task_attachment,
    get_or_create_subject,
    get_or_create_user,
)
from database.models import Base, Subject, Task, TaskAttachment, User
from services.auth_service import create_user_token


class ServerThread(threading.Thread):
    """Runs uvicorn FastAPI server in background thread."""
    def __init__(self, app, host: str, port: int):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.app = app
        self.server: Optional[uvicorn.Server] = None
        self._is_ready = threading.Event()

    def run(self):
        config = uvicorn.Config(
            app=self.app,
            host=self.host,
            port=self.port,
            log_level="warning",
            access_log=False,
        )
        self.server = uvicorn.Server(config)
        self.server.run()

    def stop(self):
        if self.server:
            self.server.should_exit = True


_server_thread: Optional[ServerThread] = None


def is_port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def create_sample_files():
    """Create real binary PDF, DOCX, and ZIP attachment files for testing."""
    TEST_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Real Minimal PDF
    pdf_path = TEST_STORAGE_DIR / "lab1_manual.pdf"
    pdf_content = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /Resources <<>> /MediaBox [0 0 612 792] >>\nendobj\n"
        b"xref\n0 4\n0000000000 65535 f \n0000000010 00000 n \n0000000060 00000 n \n0000000117 00000 n \n"
        b"trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n212\n%%EOF\n"
    )
    with open(pdf_path, "wb") as f:
        f.write(pdf_content)

    # 2. Real Minimal DOCX (ZIP archive with [Content_Types].xml)
    docx_path = TEST_STORAGE_DIR / "guidelines.docx"
    with zipfile.ZipFile(docx_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
        zf.writestr("word/document.xml", '<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>KAI QA Test Document Guidelines</w:t></w:r></w:p></w:body></w:document>')

    # 3. Real Minimal ZIP archive
    zip_path = TEST_STORAGE_DIR / "starter_code.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("main.py", '# Starter code for lab 1\nprint("Hello KAI 5108")\n')
        zf.writestr("README.txt", "Extract and run main.py\n")

    # 4. User B private file (for isolation test)
    b_file_path = TEST_STORAGE_DIR / "bob_private_notes.txt"
    with open(b_file_path, "wb") as f:
        f.write(b"TOP SECRET: Bob Private Exam Solutions")


async def seed_database():
    """Seed test database with users, subjects, tasks, and attachments."""
    TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)
    await init_db()

    async with async_session() as session:
        # Clear existing test data
        await session.execute(delete(TaskAttachment))
        await session.execute(delete(Task))
        await session.execute(delete(Subject))
        await session.execute(delete(User))
        await session.commit()

        # Seed Users
        user_alice = await get_or_create_user(session, user_id="user_alice", username="alice", role="student", group_num="5108", subgroup=2)
        user_bob = await get_or_create_user(session, user_id="user_bob", username="bob", role="student", group_num="5109", subgroup=1)
        user_admin = await get_or_create_user(session, user_id="user_admin", username="admin", role="admin", group_num="5108", subgroup=2)

        # Seed Subjects
        subj_physics = await get_or_create_subject(session, name="Физика")
        subj_math = await get_or_create_subject(session, name="Математический анализ")
        subj_circuits = await get_or_create_subject(session, name="Схемотехника")
        subj_history = await get_or_create_subject(session, name="История науки")
        subj_ee = await get_or_create_subject(session, name="Электротехника")
        subj_phil = await get_or_create_subject(session, name="Философия")
        subj_discrete = await get_or_create_subject(session, name="Дискретная математика")

        now = datetime.now(timezone.utc)

        # 10 Tasks for User Alice
        # Task 1: Overdue 3 days (лаба, physics)
        t1 = await create_task(
            session=session,
            subject_id=subj_physics.id,
            title="Лабораторная работа №1: Измерения",
            task_type="лаба",
            deadline=now - timedelta(days=3),
            status="todo",
            source="manual",
            owner_id="user_alice",
            details="Изучить погрешности измерений штангенциркулем и микрометром.",
        )
        # Attachment for Task 1 (PDF)
        await create_task_attachment(
            session=session,
            task_id=t1.id,
            file_name="lab1_manual.pdf",
            file_path="lab1_manual.pdf",
            content_type="application/pdf",
        )

        # Task 2: Overdue 1 day (домашнее задание, math)
        t2 = await create_task(
            session=session,
            subject_id=subj_math.id,
            title="Расчетно-графическая работа по пределам",
            task_type="домашнее задание",
            deadline=now - timedelta(days=1),
            status="todo",
            source="manual",
            owner_id="user_alice",
            details="Решить типовой расчет, варианты 1-15.",
        )

        # Task 3: Due Today (лаба, circuits)
        t3 = await create_task(
            session=session,
            subject_id=subj_circuits.id,
            title="Отчет по лабораторной работе: Диоды",
            task_type="лаба",
            deadline=now + timedelta(hours=4),
            status="todo",
            source="bb",
            owner_id="user_alice",
            details="Снять вольт-амперную характеристику полупроводникового диода.",
        )
        # Attachment for Task 3 (DOCX)
        await create_task_attachment(
            session=session,
            task_id=t3.id,
            file_name="guidelines.docx",
            file_path="guidelines.docx",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

        # Task 4: Due Tomorrow (доклад, history)
        t4 = await create_task(
            session=session,
            subject_id=subj_history.id,
            title="Реферат: Развитие радиотехники в XX веке",
            task_type="доклад",
            deadline=now + timedelta(days=1),
            status="todo",
            source="manual",
            owner_id="user_alice",
            details="Объем 15-20 страниц, список источников не менее 10.",
        )

        # Task 5: Due in 3 days (тест, electrical)
        t5 = await create_task(
            session=session,
            subject_id=subj_ee.id,
            title="Онлайн-тест: Законы Кирхгофа",
            task_type="тест",
            deadline=now + timedelta(days=3),
            status="todo",
            source="bb",
            owner_id="user_alice",
            details="Тест в Blackboard, 20 вопросов, 40 минут.",
        )

        # Task 6: Due Next Week (лаба, circuits)
        t6 = await create_task(
            session=session,
            subject_id=subj_circuits.id,
            title="Лабораторная работа №2: Транзисторы",
            task_type="лаба",
            deadline=now + timedelta(days=7),
            status="todo",
            source="bb",
            owner_id="user_alice",
            details="Исследование биполярного транзистора в схеме с ОЭ.",
        )
        # Attachment for Task 6 (ZIP)
        await create_task_attachment(
            session=session,
            task_id=t6.id,
            file_name="starter_code.zip",
            file_path="starter_code.zip",
            content_type="application/zip",
        )

        # Task 7: No deadline (конспект, philosophy)
        t7 = await create_task(
            session=session,
            subject_id=subj_phil.id,
            title="Конспект первоисточников: Античная философия",
            task_type="конспект",
            deadline=None,
            status="todo",
            source="manual",
            owner_id="user_alice",
            details="Прочитать диалоги Платона: Государство, Федон.",
        )

        # Task 8: Done task 1 (лаба, physics)
        t8 = await create_task(
            session=session,
            subject_id=subj_physics.id,
            title="Лабораторная работа №0: Вводный инструктаж",
            task_type="лаба",
            deadline=now - timedelta(days=10),
            status="done",
            source="manual",
            owner_id="user_alice",
            details="Пройти инструктаж по технике безопасности в лаборатории.",
        )

        # Task 9: Done task 2 (расчет, physics)
        t9 = await create_task(
            session=session,
            subject_id=subj_physics.id,
            title="Типовой расчет №1: Кинематика",
            task_type="домашнее задание",
            deadline=now - timedelta(days=5),
            status="done",
            source="manual",
            owner_id="user_alice",
            details="Сдано преподавателю на занятии.",
        )

        # Task 10: With external URL (курсовая, circuits)
        t10 = await create_task(
            session=session,
            subject_id=subj_circuits.id,
            title="Курсовой проект: Проектирование усилителя НЧ",
            task_type="курсовая",
            deadline=now + timedelta(days=21),
            status="todo",
            source="bb",
            owner_id="user_alice",
            external_url="https://bb.kai.ru/webapps/blackboard/execute/courseMain?course_id=_5108_1",
            details="Пояснительная записка и принципиальная схема в САПР.",
        )

        # 2 Tasks for User Bob (Strict Isolation check)
        tb1 = await create_task(
            session=session,
            subject_id=subj_discrete.id,
            title="Bob Task 1: Graph Theory Assignment",
            task_type="домашнее задание",
            deadline=now + timedelta(days=2),
            status="todo",
            source="manual",
            owner_id="user_bob",
            details="Bob's strictly confidential task on graphs.",
        )
        await create_task_attachment(
            session=session,
            task_id=tb1.id,
            file_name="bob_private_notes.txt",
            file_path="bob_private_notes.txt",
            content_type="text/plain",
        )

        tb2 = await create_task(
            session=session,
            subject_id=subj_discrete.id,
            title="Bob Task 2: Combinatorics Quiz",
            task_type="тест",
            deadline=now + timedelta(days=4),
            status="todo",
            source="manual",
            owner_id="user_bob",
            details="Bob quiz preparation.",
        )

        await session.commit()

    # Seed sync state (recent 5 minutes ago)
    recent_sync = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    with open(TEST_SYNC_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"last_successful_sync": recent_sync, "source": "test_seed"}, f)


def get_alice_token() -> str:
    return create_user_token(user_id="user_alice", username="alice", role="student", group_num="5108", subgroup=2)


def get_bob_token() -> str:
    return create_user_token(user_id="user_bob", username="bob", role="student", group_num="5109", subgroup=1)


def get_admin_token() -> str:
    return create_user_token(user_id="user_admin", username="admin", role="admin", group_num="5108", subgroup=2)


def start_test_server():
    """Start isolated FastAPI server on port 8899."""
    global _server_thread
    if _server_thread and _server_thread.is_alive():
        return

    if is_port_open(TEST_HOST, TEST_PORT):
        # Already running
        return

    _server_thread = ServerThread(app=api_module.app, host=TEST_HOST, port=TEST_PORT)
    _server_thread.start()

    # Wait for server to become responsive
    deadline = time.time() + 10.0
    while time.time() < deadline:
        if is_port_open(TEST_HOST, TEST_PORT):
            time.sleep(0.3)
            return
        time.sleep(0.1)
    raise RuntimeError(f"Test server failed to start on {TEST_HOST}:{TEST_PORT}")


def stop_test_server():
    """Stop test server."""
    global _server_thread
    if _server_thread:
        _server_thread.stop()
        _server_thread = None
        time.sleep(0.5)


_original_parse_task = None
_original_lab_summary = None


def setup_local_mocks():
    """Mock external services (Gemini, etc.) for deterministic fast execution in local mode."""
    global _original_parse_task, _original_lab_summary
    from services.gemini_service import GeminiService, LabSummary
    if _original_parse_task is None:
        _original_parse_task = GeminiService.parse_natural_task
    if _original_lab_summary is None:
        _original_lab_summary = GeminiService.summarize_lab_work

    def mock_parse_natural_task(self, text: str, subject_names: List[str]) -> Dict[str, Any]:
        if not text or not text.strip():
            raise ValueError("Текст не может быть пустым")
        subj = subject_names[0] if subject_names else "Физика"
        for s in subject_names:
            if s.lower() in text.lower():
                subj = s
                break
        task_type = "лаба" if "лаб" in text.lower() else ("доклад" if "реферат" in text.lower() else "задание")
        deadline_raw = "следующий вторник" if "вторник" in text.lower() else ("пятница" if "пятниц" in text.lower() else None)
        return {
            "subject": subj,
            "title": text.strip()[:60],
            "task_type": task_type,
            "deadline_raw": deadline_raw,
            "deadline_iso": "2026-09-29T18:00:00" if deadline_raw else None,
            "requirements": "Выполнить в соответствии с методическими указаниями.",
            "auditorium": "227 (5 зд.)",
            "materials_summary": "Методичка №1",
            "_metadata": {"cached": False, "duration_ms": 12, "provider": "mock-gemini"}
        }

    def mock_summarize_lab_work(self, title: str, details: str = "", file_text: Optional[str] = None, cache_user_id: Optional[str] = None) -> Dict[str, Any]:
        return {
            "summary": "Краткая суть работы: " + str(title),
            "to_bring": ["Методические указания", "Тетрадь для записей"],
            "key_steps": ["Шаг 1: Изучить теоретическую часть", "Шаг 2: Собрать лабораторную установку", "Шаг 3: Снять показания"],
            "_metadata": {"cached": False, "duration_ms": 15, "provider": "mock-gemini"}
        }

    GeminiService.parse_natural_task = mock_parse_natural_task
    GeminiService.summarize_lab_work = mock_summarize_lab_work


def teardown_local_mocks():
    """Restore original external service methods."""
    global _original_parse_task, _original_lab_summary
    from services.gemini_service import GeminiService
    if _original_parse_task is not None:
        GeminiService.parse_natural_task = _original_parse_task
        _original_parse_task = None
    if _original_lab_summary is not None:
        GeminiService.summarize_lab_work = _original_lab_summary
        _original_lab_summary = None


def setup_test_environment(mode: str = "local"):
    """Full setup: directories, sample files, database seed, server start, and local mocks."""
    TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)
    create_sample_files()
    asyncio.run(seed_database())
    if mode == "local":
        setup_local_mocks()
    start_test_server()


def teardown_test_environment(keep_data: bool = False):
    """Teardown server, mocks, and optionally clean test data directory."""
    teardown_local_mocks()
    stop_test_server()
    if not keep_data and TEST_DATA_DIR.exists():
        try:
            # Wait for file handles to release
            time.sleep(0.5)
            shutil.rmtree(TEST_DATA_DIR, ignore_errors=True)
        except Exception:
            pass
