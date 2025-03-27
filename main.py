#main.py

import logging
import os
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import Update
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiohttp import web
import ssl

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

# Webhook путь
WEBHOOK_PATH = '/webhook'
WEBHOOK_URL = f"https://memory-bot.onrender.com{WEBHOOK_PATH}"  # Домен уже правильный!

# Настройки сервера
PORT = int(os.getenv('PORT', 8000))  # Render использует переменную PORT, по умолчанию 8000

# Обработчик Webhook
async def webhook_handler(request):
    try:
        update = Update(**await request.json())
        await dp.process_update(update)
        return web.Response(text="OK", status=200)
    except Exception as e:
        logger.error(f"Ошибка обработки Webhook: {e}")
        return web.Response(text="Error", status=500)

# Установка Webhook
async def set_webhook():
    webhook_info = await bot.get_webhook_info()
    if webhook_info.url != WEBHOOK_URL:
        await bot.delete_webhook()
        await bot.set_webhook(url=WEBHOOK_URL)
        logger.info(f"Webhook установлен на {WEBHOOK_URL}")
    else:
        logger.info("Webhook уже настроен корректно")

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
        if now.hour == 10 and now.minute == 0:  # Проверка в 10:00 каждый день
            try:
                await send_reminders_to_inactive(bot)
                logger.info("Напоминания неактивным участникам отправлены")
            except Exception as e:
                logger.error(f"Ошибка при отправке напоминаний: {e}")
        await asyncio.sleep(60)  # Проверка каждую минуту

# Запуск приложения
async def on_startup(_):
    logger.info("Бот запускается...")
    await set_webhook()
    asyncio.create_task(check_incomplete_users())
    asyncio.create_task(check_inactive_users())
    logger.info("Фоновые задачи запущены")

# Основная функция
def main():
    app = web.Application()
    app.router.add_post(WEBHOOK_PATH, webhook_handler)
    app.on_startup.append(on_startup)
    
    try:
        logger.info(f"Запуск сервера на порту {PORT}")
        web.run_app(app, host='0.0.0.0', port=PORT)
    except Exception as e:
        logger.error(f"Ошибка запуска сервера: {e}")

if __name__ == '__main__':
    main()
