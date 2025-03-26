from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import asyncio
import datetime

from services.sheets import submit_application

class ApplicationState(StatesGroup):
    waiting_for_link = State()
    waiting_for_date = State()
    waiting_for_location = State()
    waiting_for_name = State()

async def start_application(message: types.Message):
    await message.answer("Пожалуйста, пришлите ссылку на пост с фотографией у памятника.")
    await ApplicationState.waiting_for_link.set()

async def process_link(message: types.Message, state: FSMContext):
    if "?" in message.text or len(message.text.split()) > 10:
        await message.answer("Похоже, вы хотите задать вопрос. Чтобы не запутаться, введите /cancel — и начнём заново.")
        return

    link = message.text.strip()
    if not (link.startswith("http://") or link.startswith("https://")):
        await message.answer("Пожалуйста, отправьте корректную ссылку, начинающуюся с http:// или https://")
        return
    await state.update_data(link=link)
    await message.answer("Спасибо! Теперь введите дату съёмки (ДД.ММ.ГГГГ):")
    await ApplicationState.waiting_for_date.set()

async def process_date(message: types.Message, state: FSMContext):
    try:
        datetime.datetime.strptime(message.text, "%d.%m.%Y")
    except ValueError:
        await message.answer("Неверный формат даты. Введите дату в формате ДД.ММ.ГГГГ:")
        return
    await state.update_data(date=message.text)
    await message.answer("Отлично! Теперь введите место съёмки (не более 100 символов):")
    await ApplicationState.waiting_for_location.set()

async def process_location(message: types.Message, state: FSMContext):
    if len(message.text) > 100:
        await message.answer("Слишком длинный текст. Введите место не более 100 символов:")
        return
    await state.update_data(location=message.text)
    await message.answer("Теперь введите название памятника или мероприятия (не более 100 символов):")
    await ApplicationState.waiting_for_name.set()

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

# Команда /cancel — отмена анкеты
async def cancel_application(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("Подача заявки отменена. Если захотите начать заново — нажмите «📨 Подать заявку».")

def register_application_handlers(dp: Dispatcher):
    dp.register_message_handler(start_application, text="📨 Подать заявку", state="*")
    dp.register_message_handler(process_link, state=ApplicationState.waiting_for_link)
    dp.register_message_handler(process_date, state=ApplicationState.waiting_for_date)
    dp.register_message_handler(process_location, state=ApplicationState.waiting_for_location)
    dp.register_message_handler(process_name, state=ApplicationState.waiting_for_name)
    dp.register_message_handler(cancel_application, commands=["cancel"], state="*")
