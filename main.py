import logging
import os
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from config import BOT_TOKEN
from handlers import user_handlers, application_handlers, fallback_handler
from handlers.application_handlers import incomplete_users
from handlers import admin_handlers  # 👈 это новый импорт


logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

user_handlers.register_handlers(dp)
application_handlers.register_application_handlers(dp)
fallback_handler.register_fallback(dp)
admin_handlers.register_admin_handlers(dp)  # 👈 регистрация админ-обработчиков


# 🔔 Фоновая задача
async def check_incomplete_users():
    while True:
        now = datetime.datetime.now()
        for user_id, started_at in list(incomplete_users.items()):
            delta = now - started_at

            if delta > datetime.timedelta(hours=1) and delta < datetime.timedelta(hours=2):
                try:
                    await bot.send_message(user_id, "👋 Вы начали подавать заявку, но не закончили. Продолжим?")
                except:
                    pass

            if delta > datetime.timedelta(days=1):
                incomplete_users.pop(user_id, None)
        await asyncio.sleep(3600)  # каждые 60 минут

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(check_incomplete_users())
    executor.start_polling(dp, skip_updates=True)
