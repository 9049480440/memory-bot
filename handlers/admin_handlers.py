from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from config import ADMIN_IDS

# Проверка, админ ли это
def is_admin(user_id):
    return user_id in ADMIN_IDS

# Inline-меню для админа
def admin_menu_markup():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📥 Просмотреть заявки", callback_data="admin_view_apps"),
        types.InlineKeyboardButton("🎯 Проставить баллы", callback_data="admin_set_scores"),
        types.InlineKeyboardButton("📤 Отправить новость", callback_data="admin_send_news"),
        types.InlineKeyboardButton("📊 Посмотреть рейтинг", callback_data="admin_view_rating"),
        types.InlineKeyboardButton("🔍 Поиск участника", callback_data="admin_search_user"),
        types.InlineKeyboardButton("🧾 Отчёт по участнику", callback_data="admin_user_report"),
        types.InlineKeyboardButton("📣 Сделать рассылку", callback_data="admin_broadcast"),
    )
    return markup

# Обработчик команды /admin
async def admin_start(message: types.Message, state: FSMContext):
    if is_admin(message.from_user.id):
        await state.finish()
        await message.answer("🛡 Админ-панель:", reply_markup=admin_menu_markup())
    else:
        await message.answer("❌ У вас нет доступа к этому разделу.")

# Регистрация обработчиков
def register_admin_handlers(dp: Dispatcher):
    dp.register_message_handler(admin_start, commands=["admin"], state="*")
