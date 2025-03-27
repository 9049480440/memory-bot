# admin_handlers.py

from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from services.sheets import (
    get_all_user_ids,
    set_score_and_notify_user,
    get_user_scores,
    export_rating_to_sheet
)
from services.common import admin_menu_markup, main_menu_markup
from config import ADMIN_IDS
import logging

# Состояния админа
class AdminStates(StatesGroup):
    waiting_for_news = State()

# Команда /admin
async def admin_start(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ У вас нет доступа.")
        return
    await message.answer("🛡 Админ-панель:", reply_markup=admin_menu_markup())

# Панель админа (кнопки)
async def handle_admin_panel(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if user_id not in ADMIN_IDS:
        await callback.message.answer("❌ У вас нет доступа.")
        return

    if callback.data == "admin_view_apps":
        await callback.message.answer("📥 Заявки пока просматриваются вручную.")
    elif callback.data == "admin_set_scores":
        await callback.message.answer("🎯 Для начисления баллов нажмите на заявку и подтвердите.")
    elif callback.data == "admin_send_news":
        await callback.message.answer("📢 Пришлите сообщение, которое хотите разослать участникам:", reply_markup=cancel_news_markup())
        await AdminStates.waiting_for_news.set()
    elif callback.data == "admin_view_rating":
        await callback.message.answer("📊 Рейтинг можно посмотреть в таблице: https://docs.google.com/spreadsheets/d/your-link")
    elif callback.data == "admin_export_rating":
        export_rating_to_sheet()
        await callback.message.answer("✅ Рейтинг выгружен в Google Таблицы.")
    else:
        await callback.message.answer("🤷 Неизвестная команда.")

# Отмена рассылки
def cancel_news_markup():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("❌ Отменить рассылку", callback_data="cancel_news"))
    return markup

async def cancel_news(callback: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await callback.message.edit_text("✉️ Рассылка отменена.")
    await callback.message.answer("🛡 Админ-панель:", reply_markup=admin_menu_markup())

# Обработка текста рассылки
async def handle_news_input(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ У вас нет доступа.")
        return

    if not message.text:
        await message.answer("Пожалуйста, отправьте текстовое сообщение.")
        return

    text = message.text
    user_ids = get_all_user_ids()

    sent = 0
    for uid in user_ids:
        try:
            await message.bot.send_message(uid, text, reply_markup=main_menu_markup(uid))
            sent += 1
        except Exception as e:
            logging.warning(f"[WARNING] Не удалось отправить сообщение {uid}: {e}")

    await message.answer(f"✅ Рассылка завершена. Сообщение отправлено {sent} участникам.")
    await message.answer("🛡 Админ-панель:", reply_markup=admin_menu_markup())
    await state.finish()

# Подтверждение баллов
async def handle_approve(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.message.answer("❌ Нет доступа.")
        return

    if callback.data.startswith("approve_"):
        submission_id = callback.data.split("approve_")[1]
        score = 3  # Можно сделать динамическим
        success = set_score_and_notify_user(submission_id, score)
        if success:
            await callback.message.edit_text("✅ Заявка подтверждена и баллы начислены.")
        else:
            await callback.message.answer("⚠️ Не удалось подтвердить заявку.")
    elif callback.data.startswith("reject_"):
        await callback.message.edit_text("❌ Заявка отклонена.")
    else:
        await callback.message.answer("❓ Неизвестное действие.")

# Регистрация
def register_admin_handlers(dp: Dispatcher):
    dp.register_message_handler(admin_start, commands=["admin"], state="*")
    dp.register_callback_query_handler(handle_admin_panel, text_startswith="admin_", state="*")
    dp.register_callback_query_handler(cancel_news, text="cancel_news", state=AdminStates.waiting_for_news)
    dp.register_message_handler(handle_news_input, state=AdminStates.waiting_for_news, content_types=types.ContentTypes.TEXT)

