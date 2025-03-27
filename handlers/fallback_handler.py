# handlers/fallback_handler.py

from aiogram import types, Dispatcher
from handlers.gpt_handler import ask_gpt
from config import ADMIN_IDS
from handlers.admin_handlers import admin_menu_markup

async def handle_unknown(message: types.Message):
    user_id = message.from_user.id
    is_admin = user_id in ADMIN_IDS

    text = message.text.strip()

    if text.startswith("http"):
        await message.answer("Это заявка на конкурс? Если да — нажмите «📨 Подать заявку», чтобы мы её учли.")
    elif "?" in text or len(text.split()) > 3:
        await message.answer("Вы задали вопрос. Сейчас постараюсь ответить...")
        answer = await ask_gpt(text)
        await message.answer(answer)
    else:
        await message.answer("Вы хотите подать заявку или задать вопрос?")

    if is_admin:
        await message.answer("🛡 Админ-панель:", reply_markup=admin_menu_markup())

def register_fallback(dp: Dispatcher):
    dp.register_message_handler(handle_unknown, content_types=types.ContentTypes.TEXT, state="*")
