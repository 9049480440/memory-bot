# admin_handlers.py

from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from config import ADMIN_IDS
from services.sheets import get_submission_stats

# Проверка: является ли пользователь админом
def is_admin(user_id):
    return user_id in ADMIN_IDS

# Кнопки меню для админа
def admin_menu_markup():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📥 Посмотреть заявки", callback_data="admin_view_apps"),
        types.InlineKeyboardButton("🎯 Проставить баллы", callback_data="admin_set_scores"),
        types.InlineKeyboardButton("📤 Отправить новость", callback_data="admin_send_news"),
        types.InlineKeyboardButton("📊 Посмотреть рейтинг", callback_data="admin_view_rating"),
    )
    return markup

# Команда /admin (на всякий случай)
async def admin_start(message: types.Message, state: FSMContext):
    if is_admin(message.from_user.id):
        await state.finish()
        await message.answer("🛡 Админ-панель:", reply_markup=admin_menu_markup())
    else:
        await message.answer("❌ У вас нет доступа к этому разделу.")

# 👉 Обработка кнопок из админ-панели
async def handle_admin_panel(callback: types.CallbackQuery, state: FSMContext):
    await state.finish()

    if not is_admin(callback.from_user.id):
        await callback.message.answer("❌ У вас нет доступа к админ-панели.")
        return

    if callback.data == "admin_view_apps":
        count, unique_users = get_submission_stats()
        await callback.message.edit_text(
            f"📬 На данный момент подано {count} заявок.\n"
            f"👥 Участвуют {unique_users} человек.",
            reply_markup=admin_menu_markup()
        )

    elif callback.data == "admin_set_scores":
        await callback.message.edit_text("⚙️ Функция проставления баллов в разработке.", reply_markup=admin_menu_markup())

    elif callback.data == "admin_send_news":
        await callback.message.edit_text("📰 Функция отправки новостей в разработке.", reply_markup=admin_menu_markup())

    elif callback.data == "admin_view_rating":
        await callback.message.edit_text("📊 Функция рейтинга участников в разработке.", reply_markup=admin_menu_markup())

# Регистрация
def register_admin_handlers(dp: Dispatcher):
    dp.register_message_handler(admin_start, commands=["admin"], state="*")
    dp.register_callback_query_handler(handle_admin_panel, text=[
        "admin_view_apps", "admin_set_scores", "admin_send_news", "admin_view_rating"
    ], state="*")
