import math
from collections import defaultdict
from typing import Dict, List

from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.filters import AuthFilter
from database.connection import async_session
from database.crud import get_subject_by_id, get_tasks, update_task_status
from database.models import Subject, Task

tasks_router = Router(name="tasks_router")
tasks_router.message.filter(AuthFilter())
tasks_router.callback_query.filter(AuthFilter())

TASKS_PER_PAGE = 5


async def safe_edit_text(callback: CallbackQuery, text: str, reply_markup: InlineKeyboardMarkup | None = None):
    """Safely edit message text ignoring Telegram 'message is not modified' error."""
    if not callback.message:
        return
    try:
        await callback.message.edit_text(text, reply_markup=reply_markup, parse_mode="HTML")
    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
            pass
        else:
            raise


def format_short_task_title(title: str, max_len: int = 24) -> str:
    """Shorten task title for inline button label."""
    clean = title.strip()
    if len(clean) > max_len:
        return clean[:max_len - 2] + ".."
    return clean


async def build_subjects_menu() -> tuple[str, InlineKeyboardMarkup | None]:
    """Build root menu listing subjects with active todo tasks."""
    async with async_session() as session:
        tasks = await get_tasks(session, status="todo")

    if not tasks:
        text = (
            "📋 <b>Ваши текущие задачи и долги:</b>\n\n"
            "🎉 <b>У вас нет активных несданных задач!</b> Все чисто."
        )
        return text, None

    # Group tasks by subject
    subjects_map: Dict[int, Subject] = {}
    subject_counts: Dict[int, int] = defaultdict(int)

    for t in tasks:
        if t.subject:
            subjects_map[t.subject.id] = t.subject
            subject_counts[t.subject.id] += 1

    total_tasks = len(tasks)
    total_subjects = len(subject_counts)

    text = (
        f"📋 <b>Управление учебными задачами и долгами</b>\n\n"
        f"Всего несданных задач: <b>{total_tasks}</b> в <b>{total_subjects}</b> предметах.\n"
        f"Выберите предмет ниже, чтобы открыть список работ и отметить сданные:"
    )

    buttons = []
    # Sort subjects by task count descending, then by name
    sorted_subj_ids = sorted(subject_counts.keys(), key=lambda sid: (-subject_counts[sid], subjects_map[sid].name))

    for sid in sorted_subj_ids:
        subj = subjects_map[sid]
        count = subject_counts[sid]
        btn_text = f"📖 {subj.name} ({count})"
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"subj_tasks:{sid}:1")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return text, keyboard


async def build_subject_tasks_view(subject_id: int, page: int = 1) -> tuple[str, InlineKeyboardMarkup]:
    """Build tasks list with pagination and done buttons for a specific subject."""
    async with async_session() as session:
        subject = await get_subject_by_id(session, subject_id)
        tasks = await get_tasks(session, status="todo", subject_id=subject_id)

    subj_name = subject.name if subject else "Предмет"

    if not tasks:
        text = (
            f"📖 <b>{subj_name}</b>\n\n"
            f"🎉 <b>Все активные задачи по этому предмету сданы! Долгов нет.</b>"
        )
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📦 Показать сданные работы", callback_data=f"subj_done_tasks:{subject_id}:1")],
                [InlineKeyboardButton(text="🔙 К списку предметов", callback_data="tasks_subjects_list")]
            ]
        )
        return text, keyboard

    total_tasks = len(tasks)
    total_pages = max(1, math.ceil(total_tasks / TASKS_PER_PAGE))
    page = max(1, min(page, total_pages))

    start_idx = (page - 1) * TASKS_PER_PAGE
    end_idx = start_idx + TASKS_PER_PAGE
    page_tasks = tasks[start_idx:end_idx]

    lines = [
        f"📖 <b>{subj_name}</b>",
        f"<i>Страница {page} из {total_pages} (активных долгов: {total_tasks})</i>\n"
    ]

    action_buttons = []

    for i, t in enumerate(page_tasks, start=start_idx + 1):
        type_icon = "💻" if "лаб" in t.task_type.lower() else "📝" if "конспект" in t.task_type.lower() else "📊"
        type_label = t.task_type.upper() if t.task_type else "ЗАДАНИЕ"

        lines.append(f"<b>{i}. {type_icon} [{type_label}] {t.title}</b>")
        if t.details:
            details_first_line = t.details.split("\n")[0][:100]
            lines.append(f"   • <i>{details_first_line}</i>")
        lines.append("")

        # Add inline button to complete task
        btn_label = f"✅ Сдать: {format_short_task_title(t.title)}"
        action_buttons.append([
            InlineKeyboardButton(
                text=btn_label,
                callback_data=f"mark_done:{t.id}:{subject_id}:{page}"
            )
        ])

    # Navigation buttons row
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"subj_tasks:{subject_id}:{page - 1}"))
    nav_row.append(InlineKeyboardButton(text=f"📄 {page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton(text="Вперед ➡️", callback_data=f"subj_tasks:{subject_id}:{page + 1}"))

    action_buttons.append(nav_row)
    action_buttons.append([InlineKeyboardButton(text="📦 Показать сданные работы", callback_data=f"subj_done_tasks:{subject_id}:1")])
    action_buttons.append([InlineKeyboardButton(text="🔙 К списку предметов", callback_data="tasks_subjects_list")])

    text = "\n".join(lines).strip()
    keyboard = InlineKeyboardMarkup(inline_keyboard=action_buttons)
    return text, keyboard


async def build_subject_done_tasks_view(subject_id: int, page: int = 1) -> tuple[str, InlineKeyboardMarkup]:
    """Build completed tasks view with undo buttons and pagination."""
    async with async_session() as session:
        subject = await get_subject_by_id(session, subject_id)
        done_tasks = await get_tasks(session, status="done", subject_id=subject_id)

    subj_name = subject.name if subject else "Предмет"

    if not done_tasks:
        text = (
            f"📦 <b>Сданные работы: {subj_name}</b>\n\n"
            f"<i>В этом предмете пока нет отмеченных сданных работ.</i>"
        )
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад к несданным", callback_data=f"subj_tasks:{subject_id}:1")],
                [InlineKeyboardButton(text="🔙 К списку предметов", callback_data="tasks_subjects_list")]
            ]
        )
        return text, keyboard

    total_tasks = len(done_tasks)
    total_pages = max(1, math.ceil(total_tasks / TASKS_PER_PAGE))
    page = max(1, min(page, total_pages))

    start_idx = (page - 1) * TASKS_PER_PAGE
    end_idx = start_idx + TASKS_PER_PAGE
    page_tasks = done_tasks[start_idx:end_idx]

    lines = [
        f"📦 <b>Сданные работы: {subj_name}</b>",
        f"<i>Страница {page} из {total_pages} (сдано работ: {total_tasks})</i>\n"
    ]

    action_buttons = []

    for i, t in enumerate(page_tasks, start=start_idx + 1):
        lines.append(f"<b>{i}. ✅ [{t.task_type.upper()}] {t.title}</b>")
        lines.append("")

        btn_label = f"↩️ Вернуть в долги: {format_short_task_title(t.title)}"
        action_buttons.append([
            InlineKeyboardButton(
                text=btn_label,
                callback_data=f"mark_todo:{t.id}:{subject_id}:{page}"
            )
        ])

    # Navigation buttons row
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"subj_done_tasks:{subject_id}:{page - 1}"))
    nav_row.append(InlineKeyboardButton(text=f"📄 {page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton(text="Вперед ➡️", callback_data=f"subj_done_tasks:{subject_id}:{page + 1}"))

    action_buttons.append(nav_row)
    action_buttons.append([InlineKeyboardButton(text="🔙 Назад к несданным", callback_data=f"subj_tasks:{subject_id}:1")])
    action_buttons.append([InlineKeyboardButton(text="🔙 К списку предметов", callback_data="tasks_subjects_list")])

    text = "\n".join(lines).strip()
    keyboard = InlineKeyboardMarkup(inline_keyboard=action_buttons)
    return text, keyboard


@tasks_router.message(F.text == "📋 Мои задачи / Долги")
async def show_my_tasks_menu(message: Message):
    """Entry point for 'Мои задачи / Долги' reply keyboard button."""
    text, keyboard = await build_subjects_menu()
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@tasks_router.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery):
    """No-op callback for non-clickable indicator buttons."""
    await callback.answer()


@tasks_router.callback_query(F.data == "tasks_subjects_list")
async def cb_subjects_list(callback: CallbackQuery):
    """Handle return to subjects list button."""
    text, keyboard = await build_subjects_menu()
    await safe_edit_text(callback, text, reply_markup=keyboard)
    await callback.answer()


@tasks_router.callback_query(F.data.startswith("subj_tasks:"))
async def cb_subject_tasks(callback: CallbackQuery):
    """Handle pagination and view of tasks for a specific subject."""
    parts = callback.data.split(":")
    subject_id = int(parts[1])
    page = int(parts[2]) if len(parts) > 2 else 1

    text, keyboard = await build_subject_tasks_view(subject_id, page)
    await safe_edit_text(callback, text, reply_markup=keyboard)
    await callback.answer()


@tasks_router.callback_query(F.data.startswith("subj_done_tasks:"))
async def cb_subject_done_tasks(callback: CallbackQuery):
    """Handle pagination and view of completed tasks for a specific subject."""
    parts = callback.data.split(":")
    subject_id = int(parts[1])
    page = int(parts[2]) if len(parts) > 2 else 1

    text, keyboard = await build_subject_done_tasks_view(subject_id, page)
    await safe_edit_text(callback, text, reply_markup=keyboard)
    await callback.answer()


@tasks_router.callback_query(F.data.startswith("mark_done:"))
async def cb_mark_task_done(callback: CallbackQuery):
    """Handle clicking 'Сдать' on a specific task."""
    parts = callback.data.split(":")
    task_id = int(parts[1])
    subject_id = int(parts[2])
    page = int(parts[3])

    async with async_session() as session:
        updated = await update_task_status(session, task_id=task_id, status="done")

    task_title = updated.title if updated else f"№{task_id}"
    await callback.answer(f"🎉 Сдано: {format_short_task_title(task_title, max_len=20)}!", show_alert=False)

    # Re-render subject tasks
    text, keyboard = await build_subject_tasks_view(subject_id, page)
    await safe_edit_text(callback, text, reply_markup=keyboard)


@tasks_router.callback_query(F.data.startswith("mark_todo:"))
async def cb_mark_task_todo(callback: CallbackQuery):
    """Handle clicking '↩️ Вернуть в долги' on a completed task."""
    parts = callback.data.split(":")
    task_id = int(parts[1])
    subject_id = int(parts[2])
    page = int(parts[3])

    async with async_session() as session:
        await update_task_status(session, task_id=task_id, status="todo")

    await callback.answer("↩️ Задача возвращена в список долгов!", show_alert=False)

    # Re-render completed tasks view
    text, keyboard = await build_subject_done_tasks_view(subject_id, page)
    await safe_edit_text(callback, text, reply_markup=keyboard)
