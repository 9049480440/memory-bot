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

    try:
        # Если похоже на ссылку, предлагаем подать заявку
        if text.startswith("http"):
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("📨 Подать заявку", callback_data="apply"))
            markup.add(types.InlineKeyboardButton("🔙 Главное меню", callback_data="cancel_app"))
            
            await message.answer(
                "Это заявка на конкурс? Если да — нажмите «📨 Подать заявку», чтобы мы её учли.",
                reply_markup=markup
            )
        
        # Если похоже на вопрос, отправляем в GPT
        elif "?" in text or len(text.split()) > 3:
            await message.answer("Вы задали вопрос. Сейчас постараюсь ответить...")
            answer = await ask_gpt(text)
            await message.answer(answer, reply_markup=main_menu_markup(user_id))
        
        # Иначе показываем основные опции
        else:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("📨 Подать заявку", callback_data="apply"))
            markup.add(types.InlineKeyboardButton("📌 О конкурсе", callback_data="info"))
            markup.add(types.InlineKeyboardButton("⭐️ Мои баллы", callback_data="scores"))
        await message.answer(answer, reply_markup=main_menu_markup(user_id), parse_mode='Markdown')    


        # Если это админ, показываем админ-панель
        if is_admin:
            await message.answer("🛡 Админ-панель:", reply_markup=admin_menu_markup())
            
    except Exception as e:
        logger.error(f"Error in fallback handler: {e}")
        # В случае ошибки, всегда даем пользователю возможность вернуться в меню
        await message.answer(
            "Произошла ошибка. Пожалуйста, вернитесь в меню или используйте команду /menu.",
            reply_markup=main_menu_markup(user_id)
        )

def register_fallback(dp: Dispatcher):
    dp.register_message_handler(handle_unknown, content_types=types.ContentTypes.TEXT, state="*")
