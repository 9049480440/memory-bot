# admin_handlers.py

from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from config import ADMIN_IDS
from services.sheets import get_submission_stats, set_score_and_notify_user

# Состояние для ввода баллов
class ScoreState(StatesGroup):
    waiting_for_score = State()

# Временное хранилище: заявка_id → user_id
pending_scores = {}

# Проверка: админ ли это
def is_admin(user_id):
    return user_id in ADMIN_IDS

# Меню для админа
def admin_menu_markup():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📥 Посмотреть заявки", callback_data="admin_view_apps"),
        types.InlineKeyboardButton("🎯 Проставить баллы", callback_data="admin_set_scores"),
        types.InlineKeyboardButton("📤 Отправить новость", callback_data="admin_send_news"),
        types.InlineKeyboardButton("📊 Посмотреть рейтинг", callback_data="admin_view_rating"),
    )
    return markup

# Команда /admin
async def admin_start(message: types.Message, state: FSMContext):
    if is_admin(message.from_user.id):
        await state.finish()
        await message.answer("🛡 Админ-панель:", reply_markup=admin_menu_markup())
    else:
        await message.answer("❌ У вас нет доступа к этому разделу.")

# Обработка кнопок админ-меню
async def handle_admin_panel(callback: types.CallbackQuery, state: FSMContext):
    await state.finish()
    if not is_admin(callback.from_user.id):
        await callback.message.answer("❌ У вас нет прав доступа.")
        return

    if callback.data == "admin_view_apps":
        count, unique_users = get_submission_stats()
        await callback.message.edit_text(
            f"📬 На данный момент подано {count} заявок.\n"
            f"👥 Участвуют {unique_users} человек.",
            reply_markup=admin_menu_markup()
        )

    elif callback.data == "admin_set_scores":
        await callback.message.edit_text("⚙️ Функция обработки заявок работает автоматически при поступлении.", reply_markup=admin_menu_markup())

    elif callback.data == "admin_send_news":
        await callback.message.edit_text("📰 Функция отправки новостей в разработке.", reply_markup=admin_menu_markup())

    elif callback.data == "admin_view_rating":
        await callback.message.edit_text("📊 Функция рейтинга в разработке.", reply_markup=admin_menu_markup())

# 👉 Обработка "✅ Подтвердить"
async def handle_approve(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    submission_id = callback.data.split("_", 1)[1]
    pending_scores[callback.from_user.id] = submission_id

    await callback.message.answer("Введите количество баллов, которые вы хотите назначить:")
    await ScoreState.waiting_for_score.set()

# 👉 Обработка "❌ Отклонить"
async def handle_reject(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup()
    await callback.message.answer("Заявка отклонена. Пользователь не будет уведомлён.")

# 👉 Обработка ввода баллов
async def receive_score(message: types.Message, state: FSMContext):
    admin_id = message.from_user.id
    score_text = message.text.strip()

    if not score_text.isdigit():
        await message.answer("Пожалуйста, введите число.")
        return

    score = int(score_text)
    submission_id = pending_scores.get(admin_id)

    if not submission_id:
        await message.answer("Что-то пошло не так. Повторите подтверждение заявки.")
        await state.finish()
        return

    # Обновляем таблицу + уведомляем участника
    result = set_score_and_notify_user(submission_id, score)

    if result:
        await message.answer("✅ Баллы записаны, участник уведомлён.")
    else:
        await message.answer("⚠️ Не удалось обновить баллы. Проверьте ID заявки.")

    await state.finish()
    pending_scores.pop(admin_id, None)

# Регистрация
def register_admin_handlers(dp: Dispatcher):
    dp.register_message_handler(admin_start, commands=["admin"], state="*")
    dp.register_callback_query_handler(handle_admin_panel, text=[
        "admin_view_apps", "admin_set_scores", "admin_send_news", "admin_view_rating"
    ], state="*")
    dp.register_callback_query_handler(handle_approve, text_startswith="approve_", state="*")
    dp.register_callback_query_handler(handle_reject, text_startswith="reject_", state="*")
    dp.register_message_handler(receive_score, state=ScoreState.waiting_for_score)
