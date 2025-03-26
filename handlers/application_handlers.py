from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import asyncio
import datetime

from services.sheets import submit_application

# Состояния анкеты
class ApplicationState(StatesGroup):
    waiting_for_link = State()
    waiting_for_date = State()
    waiting_for_location = State()
    waiting_for_name = State()

# Временное хранилище для контроля незавершённых анкет
incomplete_users = {}

# Кнопка "Задать вопрос"
def ask_question_markup():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🤖 Задать вопрос", callback_data="ask_gpt"))
    return markup

# Старт анкеты
async def start_application(message: types.Message):
    user_id = message.from_user.id
    incomplete_users[user_id] = datetime.datetime.now()
    await message.answer("Пожалуйста, пришлите ссылку на пост с фотографией у памятника.")
    await ApplicationState.waiting_for_link.set()

# Обработка ссылки
async def process_link(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if "?" in text or len(text.split()) > 10:
        await message.answer(
            "Похоже, вы хотите задать вопрос или просто что-то пишете. "
            "Если вы действительно хотите спросить — нажмите кнопку ниже 👇",
            reply_markup=ask_question_markup()
        )
        return

    if not (text.startswith("http://") or text.startswith("https://")):
        await message.answer(
            "Пожалуйста, пришлите только ссылку, без текста.\n"
            "Если вы хотите задать вопрос — нажмите кнопку 👇",
            reply_markup=ask_question_markup()
        )
        return

    await state.update_data(link=text)
    await message.answer("Спасибо! Теперь введите дату съёмки (ДД.ММ.ГГГГ):")
    await ApplicationState.waiting_for_date.set()

# Обработка даты
async def process_date(message: types.Message, state: FSMContext):
    try:
        datetime.datetime.strptime(message.text, "%d.%m.%Y")
    except ValueError:
        await message.answer("Неверный формат даты. Введите дату в формате ДД.ММ.ГГГГ:")
        return
    await state.update_data(date=message.text)
    await message.answer("Отлично! Теперь введите место съёмки (не более 100 символов):")
    await ApplicationState.waiting_for_location.set()

# Обработка места
async def process_location(message: types.Message, state: FSMContext):
    if len(message.text) > 100:
        await message.answer("Слишком длинный текст. Введите место не более 100 символов:")
        return
    await state.update_data(location=message.text)
    await message.answer("Теперь введите название памятника или мероприятия (не более 100 символов):")
    await ApplicationState.waiting_for_name.set()

# Обработка названия и завершение
async def process_name(message: types.Message, state: FSMContext):
    if len(message.text) > 100:
        await message.answer("Слишком длинный текст. Введите название не более 100 символов:")
        return
    await state.update_data(name=message.text)
    data = await state.get_data()

    link = data.get("link")
    date_text = data.get("date")
    location = data.get("location")
    monument_name = data.get("name")

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, submit_application, message.from_user, date_text, location, monument_name, link)

    await message.answer("✅ Ваша заявка принята! Спасибо за участие.")
    await state.finish()
    incomplete_users.pop(message.from_user.id, None)

# Обработка /cancel
async def cancel_application(message: types.Message, state: FSMContext):
    await state.finish()
    incomplete_users.pop(message.from_user.id, None)
    await message.answer("Подача заявки отменена. Если захотите начать заново — нажмите «📨 Подать заявку».")

# 👉 Обработка нажатия на кнопку "Задать вопрос"
async def handle_callback_query(callback_query: types.CallbackQuery, state: FSMContext):
    await state.finish()
    incomplete_users.pop(callback_query.from_user.id, None)
    await callback_query.message.answer("Вы можете задать вопрос — я постараюсь помочь 🤖")
    # GPT-обработчик сам подхватит следующее сообщение

# Регистрация
def register_application_handlers(dp: Dispatcher):
    dp.register_message_handler(start_application, text="📨 Подать заявку", state="*")
    dp.register_message_handler(process_link, state=ApplicationState.waiting_for_link)
    dp.register_message_handler(process_date, state=ApplicationState.waiting_for_date)
    dp.register_message_handler(process_location, state=ApplicationState.waiting_for_location)
    dp.register_message_handler(process_name, state=ApplicationState.waiting_for_name)
    dp.register_message_handler(cancel_application, commands=["cancel"], state="*")
    dp.register_callback_query_handler(handle_callback_query, text="ask_gpt", state="*")
