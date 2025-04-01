# main.py

import logging
import os
import asyncio
import datetime
import json  # Добавляем импорт для работы с JSON
from aiogram import Bot, Dispatcher
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import Update
from aiogram.dispatcher.middlewares import BaseMiddleware

from config import BOT_TOKEN
from handlers import (
    user_handlers,
    application_handlers,
    fallback_handler,
    admin_handlers
)
from services.sheets import send_reminders_to_inactive, state_sheet  # Импортируем state_sheet

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

# Middleware для логирования всех обновлений
class LoggingMiddleware(BaseMiddleware):
    async def on_process_update(self, update: Update, data: dict):
        if update.message:
            logger.info(f"Получено сообщение от user_id {update.message.from_user.id}: {update.message.text}")
        elif update.callback_query:
            logger.info(f"Получен callback от user_id {update.callback_query.from_user.id}: {update.callback_query.data}")

dp.middleware.setup(LoggingMiddleware())

# Регистрируем обработчики
user_handlers.register_handlers(dp)
application_handlers.register_application_handlers(dp)
admin_handlers.register_admin_handlers(dp)
fallback_handler.register_fallback(dp)

# 🔔 Фоновая задача: напоминания о незавершённых заявках
async def check_incomplete_users():
    while True:
        now = datetime.datetime.now()
        current_time = now.time()
        night_start = datetime.time(22, 30)  # 22:30
        morning_end = datetime.time(8, 0)    # 08:00
        is_night = (current_time >= night_start or current_time < morning_end)

        # Проверяем пользователей в состоянии подачи заявки
        try:
            if state_sheet is None:
                logger.error("[ERROR] Лист 'UserState' не найден.")
                await asyncio.sleep(3600)
                continue

            all_rows = state_sheet.get_all_values()
            for row in all_rows[1:]:
                user_id = row[0]
                state = row[1] if len(row) > 1 else "main_menu"
                data_str = row[2] if len(row) > 2 else ""
                data = json.loads(data_str) if data_str else None

                if state.startswith("application_step") and data and "start_time" in data:
                    start_time = datetime.datetime.fromisoformat(data["start_time"])
                    delta = now - start_time
                    if delta > datetime.timedelta(hours=1) and delta < datetime.timedelta(hours=2):
                        if not is_night:
                            try:
                                await bot.send_message(user_id, "👋 Вы начали подавать заявку, но не закончили. Продолжим?")
                                logger.info(f"Напоминание отправлено пользователю {user_id} в {now}")
                            except Exception as e:
                                logger.error(f"Ошибка отправки напоминания пользователю {user_id}: {e}")
                        else:
                            logger.info(f"Напоминание для пользователя {user_id} отложено, так как сейчас ночь (время: {current_time})")
                    if delta > datetime.timedelta(days=1):
                        clear_user_state(user_id)
                        logger.info(f"Заявка пользователя {user_id} удалена, так как прошло больше 1 дня")
        except Exception as e:
            logger.error(f"[ERROR] Ошибка в check_incomplete_users: {e}")

        await asyncio.sleep(3600)  # Каждые 60 минут

# 🔔 Фоновая задача: напоминания неактивным участникам
async def check_inactive_users():
    while True:
        now = datetime.datetime.now()
        if now.hour == 10 and now.minute == 0:
            try:
                await send_reminders_to_inactive(bot)
                logger.info("Напоминания неактивным участникам отправлены")
            except Exception as e:
                logger.error(f"Ошибка при отправке напоминаний: {e}")
        next_check = now.replace(hour=10, minute=0, second=0, microsecond=0)
        if now.hour >= 10:
            next_check += datetime.timedelta(days=1)
        seconds_to_next_check = (next_check - now).total_seconds()
        await asyncio.sleep(seconds_to_next_check)

# Запуск бота
async def on_startup(_):
    logger.info("Бот запускается с polling...")
    asyncio.create_task(check_incomplete_users())
    asyncio.create_task(check_inactive_users())
    logger.info("Фоновые задачи запущены")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
