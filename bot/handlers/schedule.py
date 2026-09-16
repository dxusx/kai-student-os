from datetime import date, timedelta
from typing import List

from aiogram import Router, F
from aiogram.types import Message

from bot.filters import AuthFilter
from core.config import settings
from services.kai_api import KaiApiClient, Lesson, get_week_parity, KaiApiError

schedule_router = Router(name="schedule_router")
schedule_router.message.filter(AuthFilter())

RUSSIAN_WEEKDAYS = {
    1: "Понедельник",
    2: "Вторник",
    3: "Среда",
    4: "Четверг",
    5: "Пятница",
    6: "Суббота",
    7: "Воскресенье",
}


def format_day_schedule(target_date: date, lessons: List[Lesson], title_prefix: str) -> str:
    """Format single day schedule into a clean, readable Telegram message."""
    day_num = target_date.weekday() + 1
    day_name = RUSSIAN_WEEKDAYS.get(day_num, "")
    parity = get_week_parity(target_date)
    parity_str = "ЧЕТНАЯ" if parity == "чет" else "НЕЧЕТНАЯ"
    iso_week = target_date.isocalendar()[1]

    header = (
        f"📅 <b>{title_prefix}: {target_date.strftime('%d.%m.%Y')} ({day_name})</b>\n"
        f"ℹ️ Группа: <b>{settings.kai_group}</b> | Подгруппа: <b>{settings.kai_subgroup}</b>\n"
        f"🔄 Неделя: <b>{parity_str}</b> (№{iso_week})\n"
        f"{'—' * 28}\n\n"
    )

    if not lessons:
        return (
            f"{header}"
            f"🎉 <b>Занятий нет!</b>\n"
            f"Свободный день или день самостоятельной работы."
        )

    lines = [header]
    for idx, l in enumerate(lessons, 1):
        type_icon = "📖" if "лек" in l.discipl_type.lower() else "💻" if "лаб" in l.discipl_type.lower() or "л.р." in l.discipl_type.lower() else "✏️"
        type_label = l.discipl_type.upper() if l.discipl_type else "ЗАНЯТИЕ"

        lines.append(f"<b>{idx}. ⏰ {l.day_time}</b> | {type_icon} <b>{l.discipl_name}</b>")
        lines.append(f"   • Тип: <i>{type_label}</i>")
        lines.append(f"   • Корпус/ауд: <b>к. {l.build_num or '—'}, ауд. {l.aud_num or '—'}</b>")
        lines.append(f"   • Преподаватель: <i>{l.prepod_name or '—'}</i>")
        if l.day_date:
            lines.append(f"   • Даты: <code>{l.day_date}</code>")
        lines.append("")

    return "\n".join(lines).strip()


@schedule_router.message(F.text == "📅 Пары на сегодня")
async def show_schedule_today(message: Message):
    """Handle 'Пары на сегодня' button."""
    today = date.today()
    client = KaiApiClient(base_url=settings.kai_api_url)

    wait_msg = await message.answer("🔄 <i>Загружаю расписание с портала КАИ...</i>", parse_mode="HTML")

    try:
        group_id = client.search_group_id(settings.kai_group)
        raw_schedule = client.get_schedule(group_id)
        lessons = client.get_lessons_for_day(
            raw_schedule,
            target_date=today,
            subgroup=settings.kai_subgroup,
            strict_date=True,
            deduplicate=True
        )
        text = format_day_schedule(today, lessons, "Пары на сегодня")
        await wait_msg.edit_text(text, parse_mode="HTML")
    except KaiApiError as e:
        await wait_msg.edit_text(f"⚠️ <b>Ошибка при получении расписания:</b>\n{e}", parse_mode="HTML")
    except Exception as e:
        await wait_msg.edit_text(f"❌ <b>Непредвиденная ошибка:</b> {e}", parse_mode="HTML")


@schedule_router.message(F.text == "📅 Пары на завтра")
async def show_schedule_tomorrow(message: Message):
    """Handle 'Пары на завтра' button."""
    tomorrow = date.today() + timedelta(days=1)
    client = KaiApiClient(base_url=settings.kai_api_url)

    wait_msg = await message.answer("🔄 <i>Загружаю расписание с портала КАИ...</i>", parse_mode="HTML")

    try:
        group_id = client.search_group_id(settings.kai_group)
        raw_schedule = client.get_schedule(group_id)
        lessons = client.get_lessons_for_day(
            raw_schedule,
            target_date=tomorrow,
            subgroup=settings.kai_subgroup,
            strict_date=True,
            deduplicate=True
        )
        text = format_day_schedule(tomorrow, lessons, "Пары на завтра")
        await wait_msg.edit_text(text, parse_mode="HTML")
    except KaiApiError as e:
        await wait_msg.edit_text(f"⚠️ <b>Ошибка при получении расписания:</b>\n{e}", parse_mode="HTML")
    except Exception as e:
        await wait_msg.edit_text(f"❌ <b>Непредвиденная ошибка:</b> {e}", parse_mode="HTML")


