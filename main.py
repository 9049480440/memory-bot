#main.py

import logging
import os
import asyncio
import datetime
from aiogram import Bot, Dispatcher
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import Update  # Добавляем для логирования

from config import BOT_TOKEN
from handlers import (
    user_handlers,
    application_handlers,
    fallback_handler,
    admin_handlers
)
from handlers.application_handlers import incomplete_users
from services.sheets import send_reminders_to_inactive

# Настройка логов с большей детализацией
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Вывод в консоль
        logging.FileHandler('bot.log')  # Сохранение в файл
    ]
)
logger = logging.getLogger(__name__)

# Инициализация бота и хранилища
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Регистрируем обработчики
user_handlers.register_handlers(dp)
application_handlers.register_application_handlers(dp)
admin_handlers.register_admin_handlers(dp)
fallback_handler.register_fallback(dp)

# Добавляем middleware для логирования всех обновлений
async def on_update(update: Update):
    if update.message:
        logger.info(f"Получено сообщение от user_id {update.message.from_user.id}: {update.message.text}")
    elif update.callback_query:
        logger.info(f"Получен callback от user_id {update.callback_query.from_user.id}: {update.callback_query.data}")

dp.middleware.setup(lambda update, data: on_update(update))

# 🔔 Фоновая задача: напоминания о незавершённых заявках
async def check_incomplete_users():
    while True:
        now = datetime.datetime.now()
        for user_id, started_at in list(incomplete_users.items()):
            delta = now - started_at
            if delta > datetime.timedelta(hours=1) and delta < datetime.timedelta(hours=2):
                try:
                    await bot.send_message(user_id, "👋 Вы начали подавать заявку, но не закончили. Продолжим?")
                except Exception as e:
                    logger.error(f"Ошибка отправки напоминания пользователю {user_id}: {e}")
            if delta > datetime.timedelta(days=1):
                incomplete_users.pop(user_id, None)
        await asyncio.sleep(3600)  # Каждые 60 минут

# 🔔 Фоновая задача: напоминания неактивным участникам
async def check_inactive_users():
    while True:
        now = datetime.datetime.now()
        # Проверяем только в 10:00
        if now.hour == 10 and now.minute == 0:
            try:
                await send_reminders_to_inactive(bot)
                logger.info("Напоминания неактивным участникам отправлены")
            except Exception as e:
                logger.error(f"Ошибка при отправке напоминаний: {e}")
        # Спим до следующей минуты, но вычисляем, сколько осталось до 10:00
        next_check = now.replace(hour=10, minute=0, second=0, microsecond=0)
        if now.hour >= 10:
            next_check += datetime.timedelta(days=1)  # Следующий день в 10:00
        seconds_to_next_check = (next_check - now).total_seconds()
        await asyncio.sleep(seconds_to_next_check)  # Спим до 10:00

# Запуск бота
async def on_startup(_):
    logger.info("Бот запускается с polling...")
    asyncio.create_task(check_incomplete_users())
    asyncio.create_task(check_inactive_users())
    logger.info("Фоновые задачи запущены")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
