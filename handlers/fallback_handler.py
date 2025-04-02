# handlers/fallback_handler.py

from aiogram import types, Dispatcher
from handlers.gpt_handler import ask_gpt
from config import ADMIN_IDS
from handlers.admin_handlers import admin_menu_markup
from services.common import main_menu_markup
import logging

logger = logging.getLogger(__name__)

async def handle_unknown(message: types.Message):
    """Обработчик для сообщений, которые не попали в другие обработчики"""
    user_id = message.from_user.id
    is_admin = user_id in ADMIN_IDS

    text = message.text.strip()
    answer = None  # <- добавлено

    try:
        # Если похоже на ссылку — предложим подать заявку
        if text.startswith("http"):
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("📨 Подать заявку", callback_data="apply"))
            markup.add(types.InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_menu"))
            
            await message.answer(
                "Похоже, вы прислали ссылку.\n\n"
                "Если это публикация для конкурса — нажмите кнопку ниже, чтобы подать заявку 👇",
                reply_markup=markup
            )
        
        # Если это похоже на вопрос — отправим в GPT
        elif "?" in text or len(text.split()) > 3:
            await message.answer("Сейчас постараюсь помочь... 🤖")
            answer = await ask_gpt(text)
            await message.answer(answer, reply_markup=main_menu_markup(user_id), parse_mode="Markdown")

        # Всё остальное — подскажем, что можно сделать
        else:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("📨 Подать заявку", callback_data="apply"))
            markup.add(types.InlineKeyboardButton("📌 О конкурсе", callback_data="info"))
            markup.add(types.InlineKeyboardButton("⭐️ Мои баллы", callback_data="scores"))

            await message.answer(
                "Я не совсем понял сообщение 🤔\n\n"
                "Вот что вы можете сделать прямо сейчас:",
                reply_markup=markup
            )

        # Если это админ, покажем панель
        if is_admin:
            await message.answer(
                "🛡 *Админ-панель:*",
                reply_markup=admin_menu_markup(),
                parse_mode="Markdown"
            )

    except Exception as e:
        logger.error(f"Error in fallback handler: {e}")
        await message.answer(
            "Произошла ошибка. Попробуйте снова или вернитесь в меню с помощью /menu.",
            reply_markup=main_menu_markup(user_id)
        )


def register_fallback(dp: Dispatcher):
    dp.register_message_handler(handle_unknown, content_types=types.ContentTypes.TEXT, state="*")
