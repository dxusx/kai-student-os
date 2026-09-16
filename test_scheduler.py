"""
Verification script for Sprint 4: Proactive scheduler and notification alerts.
Manually triggers job_evening_alert() and delivers real alert to user in Telegram.
"""

import asyncio
import logging
import socket
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent))

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from core.config import settings
from database.connection import init_db
from scheduler.jobs import NotificationScheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("test_scheduler")


async def main():
    print("=" * 75)
    print("🎓 КНИТУ-КАИ | ТЕСТИРОВАНИЕ ПРОАКТИВНОГО ПЛАНИРОВЩИКА (СПРИНТ 4)")
    print("=" * 75)
    print(f"👤 Получатель (TG_USER_ID): {settings.tg_user_id}")
    print(f"👥 Группа: {settings.kai_group}, Подгруппа: {settings.kai_subgroup}")
    print(f"🔗 Реверс-прокси: {settings.tg_api_base_url or 'Прямое подключение'}")
    print("=" * 75)

    if not settings.bot_token:
        print("❌ Ошибка: BOT_TOKEN не указан в .env!")
        return

    if not settings.tg_user_id:
        print("❌ Ошибка: TG_USER_ID не указан в .env! Задайте ID для получения уведомлений.")
        return

    # 1. Инициализация базы данных
    await init_db()
    print("✅ База данных SQLite подключена.")

    # 2. Инициализация Bot
    session = None
    if settings.tg_api_base_url:
        from aiogram.client.session.aiohttp import AiohttpSession
        from aiogram.client.telegram import TelegramAPIServer

        api_server = TelegramAPIServer.from_base(settings.tg_api_base_url)
        session = AiohttpSession(api=api_server)
        session._connector_init["family"] = socket.AF_INET

    bot = Bot(
        token=settings.bot_token,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    try:
        # 3. Инициализация NotificationScheduler
        scheduler = NotificationScheduler(bot=bot)
        print("\n🚀 Запуск тестового вызова job_evening_alert()...")

        # Принудительно вызываем вечернее оповещение
        await scheduler.job_evening_alert()

        print("\n" + "=" * 75)
        print(f"✅ Вечерний дайджест успешно сформирован и отправлен в Telegram пользователю {settings.tg_user_id}!")
        print("Проверьте чат с ботом @kai5108_helper_bot в Telegram.")
        print("=" * 75)

    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
