# main.py

import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor

from config import BOT_TOKEN
from handlers import user_handlers, application_handlers, fallback_handler  # ✅ добавили fallback

import os

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# ✅ Регистрируем обработчики
user_handlers.register_handlers(dp)
application_handlers.register_application_handlers(dp)
fallback_handler.register_fallback(dp)  # ✅ GPT + свободный текст

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
