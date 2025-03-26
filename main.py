# main.py

import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
from handlers import user_handlers

from config import BOT_TOKEN

import os

print("Current working directory:", os.getcwd())
print("Files in current directory:", os.listdir("."))


logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# Регистрируем обработчики
user_handlers.register_handlers(dp)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
