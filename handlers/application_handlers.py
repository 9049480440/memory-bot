# application_handlers.py

from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import asyncio
import datetime

from services.sheets import submit_application
from config import ADMIN_IDS
from services.common import main_menu_markup

# Состояния анкеты
class ApplicationState(StatesGroup):
    waiting_for_link = State()
    waiting_for_date = State()
    waiting_for_location = State()
    waiting_for_name = State()

# Временное хранилище
incomplete_users = {}

# Кнопка "Задать вопрос"
def ask_question_markup():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🤖 Задать вопрос", callback_data="ask_gpt"))
    markup.add(InlineKeyboardButton("🔙 Вернуться в меню", callback_data="cancel_app"))
    return markup

# Кнопка отмены анкеты
cancel_markup = InlineKeyboardMarkup().add(
    InlineKeyboardButton("🔙 Вернуться в меню", callback_data="cancel_app")
)

# Старт анкеты
async def start_application(message: types.Message):
    user_id = message.from_user.id
    incomplete_users[user_id] = datetime.datetime.now()
    await message.answer("Пожалуйста, пришлите ссылку на пост с фотографией у памятника.", reply_markup=cancel_markup)
    await ApplicationState.waiting_for_link.set()

# Обработка ссылки
async def process_link(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if "?" in text or len(text.split()) > 10 or not text.startswith("http"):
        await message.answer(
            "Похоже, вы хотите задать вопрос. Если да — нажмите кнопку 👇",
            reply_markup=ask_question_markup()
        )
        return

    await state.update_data(link=text)
    await message.answer("Спасибо! Теперь введите дату съёмки (ДД.ММ.ГГГГ):", reply_markup=cancel_markup)
    await ApplicationState.waiting_for_date.set()

# Обработка даты
async def process_date(message: types.Message, state: FSMContext):
    try:
        datetime.datetime.strptime(message.text, "%d.%m.%Y")
    except ValueError:
        await message.answer("Неверный формат даты. Введите дату в формате ДД.ММ.ГГГГ:", reply_markup=cancel_markup)
        return
    await state.update_data(date=message.text)
    await message.answer("Отлично! Теперь введите место съёмки:", reply_markup=cancel_markup)
    await ApplicationState.waiting_for_location.set()

# Обработка места
async def process_location(message: types.Message, state: FSMContext):
    await state.update_data(location=message.text)
    await message.answer("Теперь введите название памятника или мероприятия:", reply_markup=cancel_markup)
    await ApplicationState.waiting_for_name.set()

# Обработка названия и завершение
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    data = await state.get_data()

    link = data.get("link")
    date_text = data.get("date")
    location = data.get("location")
    monument_name = data.get("name")

    submission_id = submit_application(message.from_user, date_text, location, monument_name, link)

    await message.answer("✅ Ваша заявка принята! Спасибо за участие.")
    await message.answer("👇 Главное меню:", reply_markup=main_menu_markup(message.from_user.id))

    await state.finish()
    incomplete_users.pop(message.from_user.id, None)

    for admin_id in ADMIN_IDS:
        try:
            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton("✅ Подтвердить", callback_data=f"approve_{submission_id}"),
                InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{submission_id}")
            )
            text = (
                f"📥 Новая заявка:\n"
                f"👤 {message.from_user.full_name}\n"
                f"📍 {monument_name}\n"
                f"📅 {date_text}, {location}\n"
                f"🔗 {link}"
            )
            await message.bot.send_message(admin_id, text, reply_markup=markup)
        except Exception as e:
            print(f"[Ошибка при отправке админу] {e}")

# Отмена анкеты (по команде или по кнопке)
async def cancel_application(message_or_callback, state: FSMContext):
    await state.finish()
    user_id = message_or_callback.from_user.id
    incomplete_users.pop(user_id, None)
    if isinstance(message_or_callback, types.Message):
        await message_or_callback.answer("Подача заявки отменена.")
        await message_or_callback.answer("👇 Главное меню:", reply_markup=main_menu_markup(user_id))
    elif isinstance(message_or_callback, types.CallbackQuery):
        await message_or_callback.message.edit_text("Подача заявки отменена.")
        await message_or_callback.message.answer("👇 Главное меню:", reply_markup=main_menu_markup(user_id))

# Кнопка GPT
async def handle_callback_query(callback_query: types.CallbackQuery, state: FSMContext):
    await state.finish()
    incomplete_users.pop(callback_query.from_user.id, None)
    await callback_query.message.answer("Вы можете задать вопрос — я постараюсь помочь 🤖")
    await callback_query.message.answer("👇 Главное меню:", reply_markup=main_menu_markup(callback_query.from_user.id))

# Регистрация
def register_application_handlers(dp: Dispatcher):
    dp.register_message_handler(start_application, text="📨 Подать заявку", state="*")
    dp.register_message_handler(process_link, state=ApplicationState.waiting_for_link)
    dp.register_message_handler(process_date, state=ApplicationState.waiting_for_date)
    dp.register_message_handler(process_location, state=ApplicationState.waiting_for_location)
    dp.register_message_handler(process_name, state=ApplicationState.waiting_for_name)
    dp.register_message_handler(cancel_application, commands=["cancel"], state="*")
    dp.register_callback_query_handler(cancel_application, text="cancel_app", state="*")  # 👈 Обработка кнопки отмены
    dp.register_callback_query_handler(handle_callback_query, text="ask_gpt", state="*")
