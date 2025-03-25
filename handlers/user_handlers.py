from aiogram import types, Dispatcher
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from services.sheets import add_or_update_user
from config import RULES_LINK
import asyncio  # добавляем импорт asyncio

# Клавиатура
def get_main_menu():
    buttons = [
        [KeyboardButton("📌 Узнать о конкурсе")],
        [KeyboardButton("📨 Подать заявку")],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# Команда /start
async def start_command(message: types.Message):
    user = message.from_user
    # Запускаем синхронную функцию add_or_update_user в отдельном потоке, чтобы не блокировать event loop
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, add_or_update_user, user)
    
    await message.answer(
        f"Привет, {user.first_name}!\nТы в конкурсе «Эстафета Победы». Выбирай, что хочешь сделать:",
        reply_markup=get_main_menu()
    )

# Обработка кнопки "📌 Узнать о конкурсе"
async def info_about_contest(message: types.Message):
    text = (
        "Конкурс «Эстафета Победы. От памятника к памяти» проходит с 1 апреля по 30 ноября 2025 года.\n\n"
        "Участники публикуют фото или видео с памятниками и знаковыми местами, "
        "используют хештег #ОтПамятникаКПамяти и подают заявку через этот бот.\n\n"
        "Цель — сохранить память о защитниках Отечества и продвигать идеи патриотизма. "
        "Баллы начисляются за каждый объект, а активные участники получают призы.\n\n"
        f"📄 Скачать полное положение: {RULES_LINK}"
    )
    await message.answer(text)
