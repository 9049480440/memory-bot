import logging
from aiogram import Bot, Dispatcher
from aiogram.utils import executor
from handlers import user_handlers, application_handlers, score_handlers
from config import BOT_TOKEN
import os

print("Current working directory:", os.getcwd())
print("Files in current directory:", os.listdir("."))

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

user_handlers.register_handlers(dp)
application_handlers.register_application_handlers(dp)
score_handlers.register_score_handlers(dp)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
