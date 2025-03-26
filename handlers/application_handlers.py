from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import asyncio
import datetime

from services.sheets import submit_application

# Определяем состояния подачи заявки
class ApplicationState(StatesGroup):
    waiting_for_link = State()        # Ссылка на пост
    waiting_for_date = State()        # Дата съемки
    waiting_for_location = State()    # Место
    waiting_for_name = State()        # Название памятника

# Старт подачи заявки
async def start_application(message: types.Message):
    await message.answer("Пожалуйста, пришлите ссылку на пост с фотографией у памятника.")
    await ApplicationState.waiting_for_link.set()

# Обработка ссылки
async def process_link(message: types.Message, state: FSMContext):
    link = message.text.strip()
    if not (link.startswith("http://") or link.startswith("https://")):
        await message.answer("Пожалуйста, отправьте корректную ссылку, начинающуюся с http:// или https://")
        return
    await state.update_data(link=link)
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
    await message.answer("Отлично! Теперь введите место расположения (не более 100 символов):")
    await ApplicationState.waiting_for_location.set()

# Обработка места
async def process_location(message: types.Message, state: FSMContext):
    if len(message.text) > 100:
        await message.answer("Слишком длинный текст. Введите место расположения не более 100 символов:")
        return
    await state.update_data(location=message.text)
    await message.answer("Хорошо! Теперь введите название мероприятия или памятника (не более 100 символов):")
    await ApplicationState.waiting_for_name.set()

# Обработка названия и сохранение заявки
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

    await message.answer("Ваша заявка принята! Спасибо за участие.")
    await state.finish()

# Регистрация хендлеров
def register_application_handlers(dp: Dispatcher):
    dp.register_message_handler(start_application, text="📨 Подать заявку", state="*")
    dp.register_message_handler(process_link, state=ApplicationState.waiting_for_link)
    dp.register_message_handler(process_date, state=ApplicationState.waiting_for_date)
    dp.register_message_handler(process_location, state=ApplicationState.waiting_for_location)
    dp.register_message_handler(process_name, state=ApplicationState.waiting_for_name)
