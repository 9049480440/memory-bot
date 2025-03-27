# handlers/fallback_handler.py

from aiogram import types, Dispatcher
from aiogram.dispatcher.filters.state import any_state
from handlers.gpt_handler import ask_gpt
from config import ADMIN_IDS
from services.common import admin_menu_markup, main_menu_markup
from handlers.admin_handlers import AdminStates  # Импортируем AdminStates для исключения состояния
import logging

async def handle_unknown(message: types.Message):
    user_id = message.from_user.id
    is_admin = user_id in ADMIN_IDS

    if not message.text:
        await message.answer("Извините, я понимаю только текстовые сообщения. Вы можете задать вопрос или использовать кнопки меню.")
        return

    text = message.text.strip()

    if text.startswith("http"):
        await message.answer("Это заявка на конкурс? Если да — нажмите «📨 Подать заявку», чтобы мы её учли.")
    elif "?" in text or len(text.split()) > 3:
        await message.answer("Вы задали вопрос. Сейчас постараюсь ответить...")
        await ask_gpt(user_id=user_id, text=text, bot=message.bot)
    else:
        await message.answer("Вы хотите подать заявку или задать вопрос?")

    if is_admin:
        await message.answer("🛡 Админ-панель:", reply_markup=admin_menu_markup())

def register_fallback(dp: Dispatcher):
    # Регистрируем обработчик, исключая состояние AdminStates.waiting_for_news
    dp.register_message_handler(
        handle_unknown,
        content_types=types.ContentTypes.ANY,
        state=any_state,  # Для всех состояний
        state_not=AdminStates.waiting_for_news  # Кроме AdminStates.waiting_for_news
    )
