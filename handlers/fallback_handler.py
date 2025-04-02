# handlers/fallback_handler.py

from aiogram import types, Dispatcher
from handlers.gpt_handler import ask_gpt
from config import ADMIN_IDS
from handlers.admin_handlers import admin_menu_markup
from services.common import main_menu_markup
import logging
import re

logger = logging.getLogger(__name__)

# Функция для проверки URL
def is_url(text):
    # Простая проверка на URL
    url_pattern = re.compile(
        r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+(?:/[-\w%!./?=&]*)?'
    )
    return bool(url_pattern.match(text))

async def handle_unknown_text(message: types.Message):
    """Обработчик для текстовых сообщений, которые не попали в другие обработчики"""
    user_id = message.from_user.id
    is_admin = user_id in ADMIN_IDS

    text = message.text.strip()
    answer = None

    try:
        # Если похоже на ссылку — предложим подать заявку
        if is_url(text):
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

async def handle_media(message: types.Message):
    """Обработчик для медиафайлов"""
    user_id = message.from_user.id
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📨 Подать заявку", callback_data="apply"))
    markup.add(types.InlineKeyboardButton("📌 О конкурсе", callback_data="info"))
    markup.add(types.InlineKeyboardButton("⭐️ Мои баллы", callback_data="scores"))
    
    media_type = "фото" if message.photo else "видео" if message.video else "аудио" if message.audio else "файл"
    
    await message.answer(
        f"Я получил ваш {media_type}, но не могу его обработать напрямую.\n\n"
        f"Если вы хотите подать заявку, пожалуйста, опубликуйте этот {media_type} в соцсетях "
        f"с хештегом #ОтПамятникаКПамяти, затем пришлите мне ссылку на публикацию через кнопку 'Подать заявку'.",
        reply_markup=markup
    )
    
    # Если это админ, покажем панель
    if user_id in ADMIN_IDS:
        await message.answer(
            "🛡 *Админ-панель:*",
            reply_markup=admin_menu_markup(),
            parse_mode="Markdown"
        )

def register_fallback(dp: Dispatcher):
    # Обработчик для текстовых сообщений
    dp.register_message_handler(handle_unknown_text, content_types=types.ContentTypes.TEXT, state="*", is_forwarded=False)
    
    # Обработчик для медиафайлов
    dp.register_message_handler(
        handle_media, 
        content_types=[
            types.ContentType.PHOTO, 
            types.ContentType.VIDEO, 
            types.ContentType.AUDIO, 
            types.ContentType.DOCUMENT,
            types.ContentType.VOICE,
            types.ContentType.STICKER
        ], 
        state="*",
        is_forwarded=False
    )
