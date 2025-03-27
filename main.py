# main.py

import logging
import os
import asyncio
import datetime
import json
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
from services.sheets import send_reminders_to_inactive, state_sheet, clear_user_state, save_user_state
from services.common import main_menu_markup

# Настройка логов
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot.log')
    ]
)
logger = logging.getLogger(__name__)

# Бот
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Middleware логов
class LoggingMiddleware(BaseMiddleware):
    async def on_process_update(self, update: Update, data: dict):
        if update.message:
            logger.info(f"Получено сообщение от user_id {update.message.from_user.id}: {update.message.text}")
        elif update.callback_query:
            logger.info(f"Получен callback от user_id {update.callback_query.from_user.id}: {update.callback_query.data}")

dp.middleware.setup(LoggingMiddleware())

# Регистрируем обработчики
# user_handlers.register_handlers(dp)  # Закомментируем
# application_handlers.register_application_handlers(dp)  # Закомментируем
admin_handlers.register_admin_handlers(dp)
fallback_handler.register_fallback(dp)

# 🔁 Сброс всех зависших состояний при старте
async def reset_all_user_states_on_startup():
    if state_sheet:
        all_rows = state_sheet.get_all_values()
        for row in all_rows[1:]:
            user_id = row[0]
            state = row[1] if len(row) > 1 else "main_menu"
            if state != "main_menu":
                try:
                    await bot.send_message(
                        user_id,
                        "🔄 Бот был обновлён. Вы можете продолжить участие с помощью меню ниже 👇",
                        reply_markup=main_menu_markup(user_id)
                    )
                    save_user_state(user_id, "main_menu", None, None)
                    logger.info(f"[INFO] Состояние пользователя {user_id} сброшено при запуске.")
                except Exception as e:
                    logger.warning(f"[WARNING] Не удалось отправить сообщение {user_id}: {e}")

# 🔔 Проверка незавершённых заявок
async def check_incomplete_users():
    while True:
        now = datetime.datetime.now()
        current_time = now.time()
        night_start = datetime.time(22, 30)
        morning_end = datetime.time(8, 0)
        is_night = (current_time >= night_start or current_time < morning_end)

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
                                logger.info(f"Напоминание отправлено пользователю {user_id}")
                            except Exception as e:
                                logger.error(f"Ошибка отправки напоминания пользователю {user_id}: {e}")
                        else:
                            logger.info(f"Напоминание отложено для {user_id}, сейчас ночь")

                    if delta > datetime.timedelta(days=1):
                        clear_user_state(user_id)
                        try:
                            await bot.send_message(
                                user_id,
                                "⏳ Ваша заявка была удалена, так как не была завершена в течение суток.\nВы можете начать заново с помощью меню ниже.",
                                reply_markup=main_menu_markup(user_id)
                            )
                            logger.info(f"Удалена незавершённая заявка у пользователя {user_id}")
                        except Exception as e:
                            logger.error(f"Ошибка при уведомлении об удалении заявки {user_id}: {e}")

        except Exception as e:
            logger.error(f"[ERROR] Ошибка в check_incomplete_users: {e}")

        await asyncio.sleep(3600)

# 🔔 Напоминания неактивным участникам
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

# Старт
async def on_startup(_):
    logger.info("Бот запускается с polling...")
    await reset_all_user_states_on_startup()
    asyncio.create_task(check_incomplete_users())
    asyncio.create_task(check_inactive_users())
    logger.info("Фоновые задачи запущены")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
