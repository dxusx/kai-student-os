from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """
    Main reply keyboard for student assistant:
    [ 📅 Пары на сегодня ]  [ 📅 Пары на завтра ]
    [ 📋 Мои задачи / Долги ]  [ ℹ️ Помощь ]
    """
    keyboard = [
        [
            KeyboardButton(text="📅 Пары на сегодня"),
            KeyboardButton(text="📅 Пары на завтра"),
        ],
        [
            KeyboardButton(text="📋 Мои задачи / Долги"),
            KeyboardButton(text="ℹ️ Помощь"),
        ],
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder="Выберите действие в меню..."
    )
