# application_handlers.py

from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import asyncio
import datetime
import json
import logging


from services.sheets import submit_application, save_user_state, get_user_state, clear_user_state
from config import ADMIN_IDS
from services.common import main_menu_markup

# Состояния анкеты
class ApplicationState(StatesGroup):
    waiting_for_link = State()
    waiting_for_date = State()
    waiting_for_location = State()
    waiting_for_name = State()

# Кнопка "Задать вопрос"
def ask_question_markup():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🤖 Задать вопрос", callback_data="ask_gpt"))
    markup.add(InlineKeyboardButton("🔙 Вернуться в меню", callback_data="cancel_app"))
    return markup

# Расширенная кнопка отмены анкеты
def cancel_markup():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙 Вернуться в меню", callback_data="cancel_app"))
    return markup

# Старт анкеты
async def start_application(message: types.Message):
    user_id = message.from_user.id
    # Сохраняем состояние в Google Таблицах
    current_time = datetime.datetime.now().isoformat()
    save_user_state(user_id, "application_step_1", {"start_time": current_time})
    msg = await message.answer(
        "Пожалуйста, пришлите ссылку на пост с фотографией у памятника.\n\n"
        "Если хотите вернуться в меню, используйте кнопку ниже.",
        reply_markup=cancel_markup()
    )
    save_user_state(user_id, "application_step_1", {"start_time": current_time}, msg.message_id)
    await ApplicationState.waiting_for_link.set()

# Обработка ссылки
async def process_link(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text.strip()
    if "?" in text or len(text.split()) > 10 or not text.startswith("http"):
        await message.answer(
            "Похоже, вы хотите задать вопрос. Если да — нажмите кнопку 👇",
            reply_markup=ask_question_markup()
        )
        return

    await state.update_data(link=text)
    # Сохраняем состояние
    save_user_state(user_id, "application_step_2", {"link": text})
    msg = await message.answer(
        "Спасибо! Теперь введите дату съёмки (ДД.ММ.ГГГГ):", 
        reply_markup=cancel_markup()
    )
    save_user_state(user_id, "application_step_2", {"link": text}, msg.message_id)
    await ApplicationState.waiting_for_date.set()

# Обработка даты
async def process_date(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        date_obj = datetime.datetime.strptime(message.text, "%d.%m.%Y")
        date_text = message.text
    except ValueError:
        await message.answer(
            "Неверный формат даты. Введите дату в формате ДД.ММ.ГГГГ:", 
            reply_markup=cancel_markup()
        )
        return
    
    data = await state.get_data()
    data["date"] = date_text
    # Сохраняем состояние
    save_user_state(user_id, "application_step_3", data)
    msg = await message.answer(
        "Отлично! Теперь введите место съёмки (город или населенный пункт):", 
        reply_markup=cancel_markup()
    )
    save_user_state(user_id, "application_step_3", data, msg.message_id)
    await ApplicationState.waiting_for_location.set()

# Обработка места
async def process_location(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    data = await state.get_data()
    data["location"] = message.text
    # Сохраняем состояние
    save_user_state(user_id, "application_step_4", data)
    msg = await message.answer(
        "Теперь введите название памятника или мероприятия:", 
        reply_markup=cancel_markup()
    )
    save_user_state(user_id, "application_step_4", data, msg.message_id)
    await ApplicationState.waiting_for_name.set()

# Обработка названия и завершение
async def process_name(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    data = await state.get_data()
    data["name"] = message.text

    link = data.get("link", "")
    date_text = data.get("date", "")
    location = data.get("location", "")
    monument_name = data.get("name", "")

    # Добавляем отладочный вывод
    logging.info(f"[DEBUG] Отправка заявки: date_text={date_text}, location={location}, monument_name={monument_name}, link={link}")

    try:
        submission_id = submit_application(message.from_user, date_text, location, monument_name, link)
        
        
        if submission_id:
            await message.answer("✅ Ваша заявка принята! Спасибо за участие.")
            msg = await message.answer("👇 Главное меню:", reply_markup=main_menu_markup(message.from_user.id))
            
            # Очищаем состояние
            clear_user_state(user_id)
            save_user_state(user_id, "main_menu", None, msg.message_id)
            await state.finish()

            # Отправляем уведомление администраторам
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
                    logging.error(f"[Ошибка при отправке админу] {e}")
        else:
            await message.answer(
                "⚠️ Произошла ошибка при отправке заявки. Пожалуйста, попробуйте позже.", 
                reply_markup=main_menu_markup(message.from_user.id)
            )
            await state.finish()
            
    except Exception as e:
        logging.error(f"Ошибка при обработке заявки: {e}")
        await message.answer(
            "⚠️ Произошла ошибка при отправке заявки. Пожалуйста, попробуйте позже.", 
            reply_markup=main_menu_markup(message.from_user.id)
        )
        await state.finish()

# Отмена анкеты (по команде или по кнопке)
async def cancel_application(message_or_callback, state: FSMContext):
    user_id = message_or_callback.from_user.id if isinstance(message_or_callback, types.Message) else message_or_callback.from_user.id
    await state.finish()
    clear_user_state(user_id)
    
    if isinstance(message_or_callback, types.Message):
        await message_or_callback.answer("Подача заявки отменена.")
        msg = await message_or_callback.answer("👇 Главное меню:", reply_markup=main_menu_markup(user_id))
    elif isinstance(message_or_callback, types.CallbackQuery):
        await message_or_callback.message.edit_text("Подача заявки отменена.")
        msg = await message_or_callback.message.answer("👇 Главное меню:", reply_markup=main_menu_markup(user_id))
    
    save_user_state(user_id, "main_menu", None, msg.message_id)

# Кнопка GPT
async def handle_callback_query(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    await state.finish()
    clear_user_state(user_id)
    await callback_query.message.answer("Вы можете задать вопрос — я постараюсь помочь 🤖")
    msg = await callback_query.message.answer("👇 Главное меню:", reply_markup=main_menu_markup(user_id))
    save_user_state(user_id, "main_menu", None, msg.message_id)

# Регистрация
def register_application_handlers(dp: Dispatcher):
    dp.register_message_handler(start_application, text="📨 Подать заявку", state="*")
    dp.register_message_handler(process_link, state=ApplicationState.waiting_for_link)
    dp.register_message_handler(process_date, state=ApplicationState.waiting_for_date)
    dp.register_message_handler(process_location, state=ApplicationState.waiting_for_location)
    dp.register_message_handler(process_name, state=ApplicationState.waiting_for_name)
    dp.register_message_handler(cancel_application, commands=["cancel"], state="*")
    dp.register_callback_query_handler(cancel_application, text="cancel_app", state="*")
    dp.register_callback_query_handler(handle_callback_query, text="ask_gpt", state="*")
