"""Bot handlers package."""

from bot.handlers.base import base_router
from bot.handlers.schedule import schedule_router
from bot.handlers.tasks import tasks_router

__all__ = ["base_router", "schedule_router", "tasks_router"]
