from typing import Union
from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from core.config import settings


class AuthFilter(BaseFilter):
    """
    Security filter: allows messages only from the user specified by TG_USER_ID in .env.
    If TG_USER_ID is not configured, allows requests (development mode).
    """

    async def __call__(self, event: Union[Message, CallbackQuery]) -> bool:
        if settings.tg_user_id is None:
            return True

        user = event.from_user
        if user is None:
            return False

        return user.id == settings.tg_user_id
