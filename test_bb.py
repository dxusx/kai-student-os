"""
Verification script for Sprint 3: Blackboard Learn (bb.kai.ru) scraper.
Authenticates in headless mode using Playwright,
persists session in data/bb_session.json,
scrapes courses, assignments, and /bbcswebdav/ file links,
and syncs them to SQLite database.
"""

import asyncio
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)

from core.config import settings
from database.connection import init_db, async_session
from database.crud import get_tasks
from services.bb_scraper import BlackboardScraper



async def main():
    print("=" * 75)
    print("🎓 КНИТУ-КАИ | ИНТЕГРАЦИЯ С BLACKBOARD LEARN (СПРИНТ 3)")
    print("=" * 75)
    print(f"🔗 URL портала: {settings.bb_url}")
    print(f"👤 Логин студента: {settings.bb_login}")
    print("=" * 75)

    # 1. Инициализация базы данных
    await init_db()
    print("✅ База данных SQLite подключена и проверена.")

    # 2. Запуск скрейпера Blackboard
    print("\n🚀 Запуск скрейпера Blackboard (Playwright Chromium Headless)...")
    scraper = BlackboardScraper()
    result = await scraper.run_sync()

    # 3. Проверка результатов авторизации
    print("\n" + "=" * 75)
    print("📊 ОТЧЕТ О СИНХРОНИЗАЦИИ BLACKBOARD")
    print("=" * 75)

    if not result.is_authenticated:
        print(f"❌ Ошибка авторизации: {result.error}")
        return

    print("🔐 Авторизация: УСПЕШНО ✅ (сессия сохранена в data/bb_session.json)")
    print(f"📚 Найдено курсов студента: {len(result.courses)}")

    total_tasks_found = 0
    for idx, course in enumerate(result.courses, 1):
        task_count = len(course.tasks)
        total_tasks_found += task_count
        print(f"\n[{idx}] 📖 Курс: {course.title}")
        print(f"    🔗 Ссылка: {course.url}")
        print(f"    📝 Найдено заданий/материалов: {task_count}")

        if course.tasks:
            for t_idx, t in enumerate(course.tasks, 1):
                files_count = len(t.attachments)
                files_info = f" | 📎 Файлов методичек: {files_count}" if files_count else ""
                print(f"      {t_idx}. [{t.task_type.upper()}] {t.title}{files_info}")
                for att in t.attachments:
                    print(f"         ↳ Файл: {att.name}")

    print("\n" + "-" * 75)
    print(f"ИТОГО НАЙДЕНО МАТЕРИАЛОВ: {total_tasks_found}")
    print(f"➕ Добавлено новых задач в SQLite: {result.tasks_created}")
    print(f"🔄 Пропущено существующих (дедупликация): {result.tasks_skipped}")
    print("-" * 75)

    # 4. Проверка записей в базе данных SQLite
    print("\n📋 ПРОВЕРКА ЗАДАЧ ИЗ BLACKBOARD В БАЗЕ ДАННЫХ:")
    async with async_session() as session:
        bb_tasks = await get_tasks(session)
        bb_tasks_filtered = [t for t in bb_tasks if t.source == "bb"]

    print(f"Всего задач в SQLite с источником source='bb': {len(bb_tasks_filtered)}")
    for idx, t in enumerate(bb_tasks_filtered[:10], 1):
        subj_name = t.subject.name if t.subject else "Без предмета"
        print(f"  {idx}. [{t.task_type.upper()}] {t.title}")
        print(f"     Предмет: {subj_name}")
        print(f"     Статус: {t.status} | Источник: {t.source}")

    if len(bb_tasks_filtered) > 10:
        print(f"  ... и еще {len(bb_tasks_filtered) - 10} задач(и)")

    print("=" * 75)
    print("✅ Спринт 3: Синхронизация Blackboard с базой данных завершена успешно!")
    print("=" * 75)


if __name__ == "__main__":
    asyncio.run(main())
