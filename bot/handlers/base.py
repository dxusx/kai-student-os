from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

from bot.filters import AuthFilter
from bot.keyboards import get_main_keyboard
from core.config import settings

base_router = Router(name="base_router")
# Apply auth filter to the router
base_router.message.filter(AuthFilter())


@base_router.message(CommandStart())
async def cmd_start(message: Message):
    """Handle /start command."""
    user_id_note = ""
    if settings.tg_user_id is None and message.from_user:
        user_id_note = f"\n\n🔑 <i>Ваш Telegram ID:</i> <code>{message.from_user.id}</code> (добавьте в <code>.env</code> в <code>TG_USER_ID</code> для защиты бота)."

    text = (
        f"👋 <b>Привет! Я персональный ассистент студента КНИТУ-КАИ.</b>\n\n"
        f"🎯 <b>Профиль:</b>\n"
        f"• Институт: <b>ИРЭФ-ЦТ</b>\n"
        f"• Группа: <b>{settings.kai_group}</b>\n"
        f"• Подгруппа: <b>{settings.kai_subgroup}</b>\n\n"
        f"Используйте кнопки меню ниже для навигации по расписанию и учебным дедлайнам.{user_id_note}"
    )
    await message.answer(text, reply_markup=get_main_keyboard(), parse_mode="HTML")


@base_router.message(Command("app"))
@base_router.message(Command("pwa"))
async def cmd_app(message: Message):
    """Handle /app or /pwa command."""
    from services.tunnel import get_current_tunnel_url
    url = get_current_tunnel_url() or f"http://localhost:{settings.web_port}"
    text = (
        "🌐 <b>Мобильное веб-приложение (PWA) КАИ 5108:</b>\n\n"
        f"🔗 <b><a href='{url}'>{url}</a></b>\n\n"
        "📱 Откройте ссылку в браузере Chrome на смартфоне и выберите <i>«Добавить на главный экран»</i> для установки автономного приложения!"
    )
    await message.answer(text, parse_mode="HTML")


@base_router.message(F.text == "ℹ️ Помощь")
@base_router.message(Command("help"))
async def cmd_help(message: Message):
    """Handle help command or button."""
    text = (
        "📖 <b>Справка по возможностям ассистента:</b>\n\n"
        "📅 <b>Пары на сегодня</b> — актуальное расписание с учетом четности недели и 2-й подгруппы.\n"
        "📅 <b>Пары на завтра</b> — расписание на следующий день с аудиториями и корпусами.\n"
        "📋 <b>Мои задачи / Долги</b> — список ваших текущих лабораторных и заданий из Blackboard.\n"
        "🌐 <b>/app</b> — получить ссылку на мобильное веб-приложение (PWA) для смартфона.\n\n"
        "⚡ <i>Расписание автоматически синхронизируется с порталом КАИ и объединяет спаренные аудитории и лабораторные работы.</i>"
    )
    await message.answer(text, parse_mode="HTML")

