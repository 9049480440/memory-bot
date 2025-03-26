from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from services.sheets import add_or_update_user, get_user_scores
from handlers.application_handlers import start_application
from config import ADMIN_IDS
from handlers.admin_handlers import is_admin, admin_menu_markup

# Inline-меню (главное)
def main_menu_markup(user_id=None):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📌 Узнать о конкурсе", callback_data="info"),
        types.InlineKeyboardButton("📨 Подать заявку", callback_data="apply"),
        types.InlineKeyboardButton("⭐️ Мои баллы", callback_data="scores"),
    )

    # 👮‍♂️ Если админ — добавляем кнопку
    if user_id in ADMIN_IDS:
        markup.add(types.InlineKeyboardButton("🛡 Админ-панель", callback_data="admin_panel"))

    return markup

# /start
async def start(message: types.Message, state: FSMContext):
    await state.finish()
    add_or_update_user(message.from_user)
    await message.answer(
        "Добро пожаловать в конкурс «Эстафета Победы»! 👇",
        reply_markup=main_menu_markup(message.from_user.id)
    )

# Обработка нажатий на кнопки
async def handle_main_menu(callback: types.CallbackQuery, state: FSMContext):
    await state.finish()

    if callback.data == "info":
        await callback.message.edit_text(
            "📍 Конкурс приурочен к 80-летию Победы и Году Защитника Отечества.\n\n"
            "Участвуйте, публикуйте посты у памятников, копите баллы и получайте призы!\n\n"
            "📄 Подробнее: https://docs.google.com/document/d/your-link-here",
            reply_markup=main_menu_markup(callback.from_user.id)
        )

    elif callback.data == "apply":
        await callback.message.edit_text("🚀 Начинаем подачу заявки!")
        await start_application(callback.message)

    elif callback.data == "scores":
        user_id = str(callback.from_user.id)
        results, total = get_user_scores(user_id)
        if not results:
            text = "У вас пока нет заявок. Подайте первую — и получите баллы!"
        else:
            text = "Ваши заявки:\n\n" + "\n\n".join(results) + f"\n\n🌟 Всего баллов: {total}"

        await callback.message.edit_text(text, reply_markup=main_menu_markup(callback.from_user.id))

    elif callback.data == "admin_panel":
        if is_admin(callback.from_user.id):
            await callback.message.edit_text("🛡 Админ-панель:", reply_markup=admin_menu_markup())
        else:
            await callback.message.answer("❌ У вас нет прав доступа.")

# Регистрация
def register_handlers(dp: Dispatcher):
    dp.register_message_handler(start, commands=["start"], state="*")
    dp.register_callback_query_handler(handle_main_menu, text=["info", "apply", "scores", "admin_panel"], state="*")
