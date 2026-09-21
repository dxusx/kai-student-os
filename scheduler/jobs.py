"""
Proactive notification scheduler based on APScheduler.
Automates:
1. Evening digest at 20:00 (tomorrow's lessons and lab warnings).
2. Morning routing brief at 07:30 (first pair, rooms, and schedule).
3. Periodic Blackboard synchronization every 4 hours.
"""

from __future__ import annotations

import logging
import re
from datetime import date, timedelta
from typing import List, Optional

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from core.config import settings
from database.connection import async_session
from database.crud import get_tasks
from database.models import Task
from services.bb_scraper import BlackboardScraper
from services.kai_api import KaiApiClient, Lesson
from services.para_api import KapiparaClient

logger = logging.getLogger("kai_assistant.scheduler")

RUSSIAN_WEEKDAYS = {
    1: "Понедельник",
    2: "Вторник",
    3: "Среда",
    4: "Четверг",
    5: "Пятница",
    6: "Суббота",
    7: "Воскресенье",
}


def match_subject(schedule_name: str, db_subject_name: str) -> bool:
    """Fuzzy matching between KAI schedule discipline name and Blackboard course title."""
    s1 = re.sub(r"[^\w\s]", " ", schedule_name.lower())
    s2 = re.sub(r"[^\w\s]", " ", db_subject_name.lower())
    if s1 in s2 or s2 in s1:
        return True

    words1 = {w for w in s1.split() if len(w) >= 4}
    words2 = {w for w in s2.split() if len(w) >= 4}

    for w1 in words1:
        for w2 in words2:
            if w1[:4] == w2[:4]:
                return True
    return False


class NotificationScheduler:
    """Manages scheduled background notification alerts for the student."""

    def __init__(self, bot: Bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler(timezone="Europe/Moscow")

    async def get_lessons_for_target_date(self, target_date: date) -> List[Lesson]:
        """Fetch schedule for a specific date (using Kapipara with fallback to KAI API)."""
        para_client = KapiparaClient(base_url=settings.kapipara_api_url)
        try:
            raw_schedule = para_client.get_schedule_grid(settings.kai_group, fallback_on_error=False)
            lessons = para_client.get_lessons_for_day(
                raw_schedule,
                target_date=target_date,
                subgroup=settings.kai_subgroup,
                strict_date=True,
                deduplicate=True,
            )
            return lessons
        except Exception as pe:
            logger.warning("Kapipara schedule fetch failed in scheduler (%s), falling back to KAI API.", pe)

        client = KaiApiClient(base_url=settings.kai_api_url)
        try:
            group_id = client.search_group_id(settings.kai_group)
            raw_schedule = client.get_schedule(group_id)
            lessons = client.get_lessons_for_day(
                raw_schedule,
                target_date=target_date,
                subgroup=settings.kai_subgroup,
                strict_date=True,
                deduplicate=True,
            )
            return lessons
        except Exception as e:
            logger.error("Failed to fetch KAI schedule for %s: %s", target_date, e)
            return []

    async def job_evening_alert(self) -> None:
        """
        Evening alert job (runs every day at 20:00).
        Analyzes tomorrow's schedule and highlights relevant lab assignments / deadlines.
        """
        logger.info("Executing evening alert job...")
        if not settings.tg_user_id:
            logger.warning("No TG_USER_ID configured. Skipping evening alert.")
            return

        tomorrow = date.today() + timedelta(days=1)
        day_num = tomorrow.weekday() + 1
        day_name = RUSSIAN_WEEKDAYS.get(day_num, "")

        lessons = await self.get_lessons_for_target_date(tomorrow)

        if not lessons:
            text = (
                f"🌙 <b>Вечерний дайджест на завтра ({tomorrow.strftime('%d.%m.%Y')}, {day_name}):</b>\n\n"
                f"🎉 <b>Завтра пар нет!</b> День самостоятельной работы или законный отдых.\n"
                f"Отличная возможность закрыть висящие долги в Blackboard."
            )
            await self.bot.send_message(chat_id=settings.tg_user_id, text=text, parse_mode="HTML")
            return

        # Fetch todo tasks from database
        async with async_session() as session:
            todo_tasks = await get_tasks(session, status="todo")

        # Match tasks by tomorrow's disciplines
        lesson_disc_names = [l.discipl_name for l in lessons]
        matched_tasks: List[Task] = []
        seen_task_ids = set()

        for disc in lesson_disc_names:
            for t in todo_tasks:
                if t.subject and t.id not in seen_task_ids:
                    if match_subject(disc, t.subject.name):
                        matched_tasks.append(t)
                        seen_task_ids.add(t.id)

        # Prioritize labs
        matched_tasks.sort(key=lambda x: (0 if "лаб" in x.task_type.lower() else 1, x.id))

        lines = [
            f"🌙 <b>Вечерний дайджест на завтра ({tomorrow.strftime('%d.%m.%Y')}, {day_name}):</b>\n",
            f"📚 <b>Расписание занятий:</b>"
        ]

        for idx, l in enumerate(lessons, 1):
            type_icon = "📖" if "лек" in l.discipl_type.lower() else "💻" if "лаб" in l.discipl_type.lower() else "✏️"
            lines.append(f"  {idx}. ⏰ <b>{l.day_time}</b> | {type_icon} <b>{l.discipl_name}</b> (к. {l.build_num or '—'}, ауд. {l.aud_num or '—'})")

        lines.append("")

        if matched_tasks:
            lines.append("⚠️ <b>Внимание к заданиям и лабораторным по этим предметам:</b>")
            for idx, t in enumerate(matched_tasks[:8], 1):
                s_name = t.subject.name if t.subject else "Общее"
                type_badge = t.task_type.upper() if t.task_type else "ЗАДАНИЕ"
                lines.append(f"  • <b>[{type_badge}]</b> {t.title} (<i>{s_name}</i>)")

            if len(matched_tasks) > 8:
                lines.append(f"  💡 <i>...и еще {len(matched_tasks) - 8} заданий по предметам дня.</i>")

            lines.append("\n📌 <i>Не забудьте распечатать титульные листы, отчеты и подготовить тетради!</i>")
        else:
            lines.append("✅ <i>По предметам на завтра несданных долгов в базе не найдено! Все чисто.</i>")

        text = "\n".join(lines).strip()
        await self.bot.send_message(chat_id=settings.tg_user_id, text=text, parse_mode="HTML")
        logger.info("Evening alert sent successfully to user %s.", settings.tg_user_id)

    async def job_morning_brief(self) -> None:
        """
        Morning brief job (runs every day at 07:30).
        Sends morning routing sheet with the first lesson location and building.
        """
        logger.info("Executing morning brief job...")
        if not settings.tg_user_id:
            logger.warning("No TG_USER_ID configured. Skipping morning brief.")
            return

        today = date.today()
        day_num = today.weekday() + 1
        day_name = RUSSIAN_WEEKDAYS.get(day_num, "")

        lessons = await self.get_lessons_for_target_date(today)

        if not lessons:
            text = (
                f"☀️ <b>Доброе утро! Маршрутный лист на сегодня ({today.strftime('%d.%m.%Y')}, {day_name}):</b>\n\n"
                f"🎉 <b>Сегодня занятий нет!</b> Хорошего и продуктивного дня."
            )
            await self.bot.send_message(chat_id=settings.tg_user_id, text=text, parse_mode="HTML")
            return

        first_lesson = lessons[0]

        lines = [
            f"☀️ <b>Доброе утро! Маршрутный лист на сегодня ({today.strftime('%d.%m.%Y')}, {day_name}):</b>\n",
            f"🚀 <b>Первая пара:</b>",
            f"⏰ Время: <b>{first_lesson.day_time}</b>",
            f"📖 Предмет: <b>{first_lesson.discipl_name}</b>",
            f"📍 Место: <b>Корпус {first_lesson.build_num or '—'}, ауд. {first_lesson.aud_num or '—'}</b>",
            f"👤 Преподаватель: <i>{first_lesson.prepod_name or '—'}</i>\n",
            f"📋 <b>Всего занятий сегодня: {len(lessons)}</b>"
        ]

        for idx, l in enumerate(lessons, 1):
            type_icon = "📖" if "лек" in l.discipl_type.lower() else "💻" if "лаб" in l.discipl_type.lower() else "✏️"
            lines.append(f"  {idx}. ⏰ {l.day_time} | {type_icon} {l.discipl_name} (к. {l.build_num or '—'}, ауд. {l.aud_num or '—'})")

        lines.append("\n⚡ <i>Удачного учебного дня!</i>")

        text = "\n".join(lines).strip()
        await self.bot.send_message(chat_id=settings.tg_user_id, text=text, parse_mode="HTML")
        logger.info("Morning brief sent successfully to user %s.", settings.tg_user_id)

    async def job_sync_blackboard(self) -> None:
        """
        Background synchronization with Blackboard Learn (every 4 hours).
        Alerts student if new tasks or materials appeared.
        """
        logger.info("Executing background Blackboard synchronization job...")
        try:
            scraper = BlackboardScraper(headless=True)
            result = await scraper.run_sync()

            if result.tasks_created > 0 and settings.tg_user_id:
                text = (
                    f"🔔 <b>В Blackboard появились новые материалы!</b>\n\n"
                    f"➕ Добавлено новых заданий/методичек: <b>{result.tasks_created} шт.</b>\n\n"
                    f"Используйте кнопку <b>«📋 Мои задачи / Долги»</b> в боте для просмотра."
                )
                await self.bot.send_message(chat_id=settings.tg_user_id, text=text, parse_mode="HTML")
                logger.info("Blackboard alert sent to user %s (new tasks: %d).", settings.tg_user_id, result.tasks_created)
        except Exception as e:
            logger.exception("Error in job_sync_blackboard: %s", e)

    def start(self) -> None:
        """Register jobs and start the AsyncIOScheduler."""
        logger.info("Starting NotificationScheduler...")

        # 1. Evening alert daily at 20:00 Europe/Moscow
        self.scheduler.add_job(
            self.job_evening_alert,
            trigger=CronTrigger(hour=20, minute=0, timezone="Europe/Moscow"),
            id="job_evening_alert",
            name="Evening Alert at 20:00",
            replace_existing=True
        )

        # 2. Morning brief daily at 07:30 Europe/Moscow
        self.scheduler.add_job(
            self.job_morning_brief,
            trigger=CronTrigger(hour=7, minute=30, timezone="Europe/Moscow"),
            id="job_morning_brief",
            name="Morning Brief at 07:30",
            replace_existing=True
        )

        # 3. Periodic Blackboard sync every 4 hours
        self.scheduler.add_job(
            self.job_sync_blackboard,
            trigger=IntervalTrigger(hours=4),
            id="job_sync_blackboard",
            name="Sync Blackboard every 4 hours",
            replace_existing=True
        )

        self.scheduler.start()
        logger.info("NotificationScheduler started with 3 registered jobs.")

    def stop(self) -> None:
        """Shutdown the scheduler gracefully."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("NotificationScheduler stopped.")
