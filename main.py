# main.py

import logging
import os
import asyncio
import datetime
import json
from aiogram import Bot, Dispatcher
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import Update, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.dispatcher.middlewares import BaseMiddleware
from services.sheets import check_sheet_structure, send_reminders_to_inactive
from config import BOT_TOKEN
from handlers import (
    user_handlers,
    application_handlers,
    fallback_handler,
    admin_handlers
)
from services.sheets import (
    send_reminders_to_inactive, 
    state_sheet, 
    clear_user_state, 
    get_all_user_ids, 
    save_user_state
)  # Добавлен import clear_user_state
from services.common import main_menu_markup

from services.sheets import (
    send_reminders_to_inactive, 
    state_sheet, 
    clear_user_state, 
    get_all_user_ids, 
    save_user_state,
    check_sheet_structure  # Добавьте эту строку
)

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

# Версия бота для отслеживания обновлений
BOT_VERSION = "1.0.1"
VERSION_FILE = "bot_version.txt"

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

# Проверка обновления версии
def check_version_update():
    """Проверяет, была ли обновлена версия бота"""
    try:
        # Пытаемся прочитать предыдущую версию
        with open(VERSION_FILE, "r") as f:
            previous_version = f.read().strip()
            
        # Если версии отличаются - было обновление
        if previous_version != BOT_VERSION:
            with open(VERSION_FILE, "w") as f:
                f.write(BOT_VERSION)
            return True
        return False
    except FileNotFoundError:
        # Если файла нет - это первый запуск
        with open(VERSION_FILE, "w") as f:
            f.write(BOT_VERSION)
        return False

# Уведомление о новой версии бота
async def notify_users_about_update():
    """Отправляет сообщение всем пользователям об обновлении бота"""
    users = get_all_user_ids()
    
    update_message = (
        "🔄 Бот был обновлен и готов к работе!\n"
        "Продолжайте участвовать в конкурсе и зарабатывать баллы!"
    )
    
    sent_count = 0
    for user_id in users:
        try:
            await bot.send_message(
                user_id, 
                update_message,
                reply_markup=main_menu_markup(user_id=user_id)
            )
            sent_count += 1
            await asyncio.sleep(0.1)  # Небольшая задержка чтобы не превысить лимиты API
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение об обновлении пользователю {user_id}: {e}")
    
    logger.info(f"Уведомление об обновлении отправлено {sent_count} пользователям")

# Команда /menu для возврата в главное меню
@dp.message_handler(commands=["menu"], state="*")
async def command_menu(message, state):
    """Обработчик команды /menu - всегда возвращает в главное меню"""
    await state.finish()
    user_id = message.from_user.id
    clear_user_state(user_id)
    
    msg = await message.answer(
        "👇 Главное меню:",
        reply_markup=main_menu_markup(user_id=user_id)
    )
    save_user_state(user_id, "main_menu", None, msg.message_id)
    logger.info(f"Пользователь {user_id} вернулся в главное меню через команду /menu")

# 🔔 Фоновая задача: напоминания о незавершённых заявках
async def check_incomplete_users():
    while True:
        try:
            now = datetime.datetime.now()
            current_time = now.time()
            night_start = datetime.time(22, 30)  # 22:30
            morning_end = datetime.time(8, 0)    # 08:00
            is_night = (current_time >= night_start or current_time < morning_end)

            # Проверяем пользователей в состоянии подачи заявки
            if state_sheet is None:
                logger.error("[ERROR] Лист 'UserState' не найден.")
                await asyncio.sleep(3600)
                continue

            all_rows = state_sheet.get_all_values()
            for row in all_rows[1:]:
                if len(row) < 3:
                    continue  # Пропускаем неполные строки
                    
                user_id = row[0]
                state = row[1]
                data_str = row[2]
                
                if not user_id or not user_id.isdigit():
                    continue  # Пропускаем строки с некорректным user_id
                
                user_id = int(user_id)
                data = json.loads(data_str) if data_str else None

                if state.startswith("application_step") and data and "start_time" in data:
                    try:
                        start_time = datetime.datetime.fromisoformat(data["start_time"])
                        delta = now - start_time
                        
                        if delta > datetime.timedelta(hours=1) and delta < datetime.timedelta(hours=2):
                            if not is_night:
                                try:
                                    markup = InlineKeyboardMarkup()
                                    markup.add(InlineKeyboardButton("📝 Продолжить заявку", callback_data="continue_app"))
                                    markup.add(InlineKeyboardButton("🔙 В главное меню", callback_data="cancel_app"))
                                    
                                    await bot.send_message(
                                        user_id, 
                                        "👋 Вы начали подавать заявку, но не закончили. Продолжим?",
                                        reply_markup=markup
                                    )
                                    logger.info(f"Напоминание отправлено пользователю {user_id} в {now}")
                                except Exception as e:
                                    logger.error(f"Ошибка отправки напоминания пользователю {user_id}: {e}")
                            else:
                                logger.info(f"Напоминание для пользователя {user_id} отложено, так как сейчас ночь (время: {current_time})")
                                
                        if delta > datetime.timedelta(days=1):
                            clear_user_state(user_id)
                            logger.info(f"Заявка пользователя {user_id} удалена, так как прошло больше 1 дня")
                    except Exception as e:
                        logger.error(f"Ошибка при обработке пользователя {user_id}: {e}")
        except Exception as e:
            logger.error(f"[ERROR] Ошибка в check_incomplete_users: {e}")

        await asyncio.sleep(3600)  # Каждые 60 минут

# 🔔 Фоновая задача: напоминания неактивным участникам
async def check_inactive_users():
    while True:
        try:
            now = datetime.datetime.now()
            if now.hour == 10 and now.minute < 5:  # Расширяем окно запуска до 5 минут
                try:
                    await send_reminders_to_inactive(bot)
                    logger.info("Напоминания неактивным участникам отправлены")
                except Exception as e:
                    logger.error(f"Ошибка при отправке напоминаний: {e}")
                
                # Ждем до завтра
                await asyncio.sleep(24 * 60 * 60 - 300)  # -5 минут чтобы не пропустить окно
            else:
                # Ждем до следующей проверки
                await asyncio.sleep(300)  # Проверяем каждые 5 минут
        except Exception as e:
            logger.error(f"Ошибка в check_inactive_users: {e}")
            await asyncio.sleep(3600)  # При ошибке повторяем через час

# Запуск бота
async def on_startup(_):
    logger.info("Бот запускается с polling...")
    
    # Добавьте эту строку для проверки структуры таблицы
    check_sheet_structure()
    
    # Проверка обновления и отправка уведомлений
    is_updated = check_version_update()
    if is_updated:
        await notify_users_about_update()
        logger.info(f"Бот обновлен до версии {BOT_VERSION}")
    
    # Запуск фоновых задач
    asyncio.create_task(check_incomplete_users())
    asyncio.create_task(check_inactive_users())
    logger.info("Фоновые задачи запущены")

# Обработчик для кнопки "продолжить заявку"
@dp.callback_query_handler(text="continue_app", state="*")
async def continue_application(callback_query, state):
    """Обработчик для продолжения незавершенной заявки"""
    user_id = callback_query.from_user.id
    await state.finish()
    
    # В будущем здесь можно добавить восстановление шага заявки
    # Пока просто перезапускаем процесс
    await callback_query.message.delete()
    await application_handlers.start_application(callback_query.message)

# Регистрируем обработчики
user_handlers.register_handlers(dp)
application_handlers.register_application_handlers(dp)
admin_handlers.register_admin_handlers(dp)
fallback_handler.register_fallback(dp)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
