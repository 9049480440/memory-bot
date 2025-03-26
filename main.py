import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from config import BOT_TOKEN
from handlers import user_handlers, application_handlers, fallback_handler

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

user_handlers.register_handlers(dp)
application_handlers.register_application_handlers(dp)
fallback_handler.register_fallback(dp)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
