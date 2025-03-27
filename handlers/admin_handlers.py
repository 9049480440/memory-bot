# admin_handlers.py

from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils.exceptions import MessageNotModified  # Добавляем импорт
from services.sheets import (
    get_submission_stats,
    set_score_and_notify_user,
    get_all_user_ids,
    get_top_users,
    update_user_score_in_activity,
    export_rating_to_sheet,
    save_user_state,
    get_user_state,
    clear_user_state
)
from services.common import main_menu_markup, is_admin, admin_menu_markup
import logging

# Состояния админа
class ScoreState(StatesGroup):
    waiting_for_score = State()

class AdminStates(StatesGroup):
    waiting_for_news = State()

pending_scores = {}

async def send_admin_panel(message: types.Message):
    if is_admin(message.from_user.id):
        msg = await message.answer("🛡 Админ-панель:", reply_markup=admin_menu_markup())
        save_user_state(message.from_user.id, "admin_panel", None, msg.message_id)

async def admin_start(message: types.Message, state: FSMContext):
    if is_admin(message.from_user.id):
        await state.finish()
        msg = await message.answer("🛡 Админ-панель:", reply_markup=admin_menu_markup())
        save_user_state(message.from_user.id, "admin_panel", None, msg.message_id)
    else:
        await message.answer("❌ У вас нет доступа к админ-панели.")

async def handle_admin_panel(callback: types.CallbackQuery, state: FSMContext):
    await state.finish()
    user_id = callback.from_user.id
    logging.info(f"handle_admin_panel вызван для user_id {user_id} с callback.data: {callback.data}")
    
    if not is_admin(user_id):
        await callback.message.answer("❌ У вас нет доступа.")
        return

    if callback.data == "admin_view_apps":
        count, unique_users = get_submission_stats()
        text = f"📬 Подано {count} заявок от {unique_users} участников."
        try:
            await callback.message.edit_text(
                text,
                reply_markup=admin_menu_markup()
            )
        except MessageNotModified:
            pass  # Игнорируем ошибку, если текст не изменился
        save_user_state(user_id, "admin_panel", None, callback.message.message_id)

    elif callback.data == "admin_set_scores":
        text = "⚙️ Оценка заявок происходит автоматически при поступлении."
        try:
            await callback.message.edit_text(
                text,
                reply_markup=admin_menu_markup()
            )
        except MessageNotModified:
            pass
        save_user_state(user_id, "admin_panel", None, callback.message.message_id)

    elif callback.data == "admin_send_news":
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 Отменить рассылку", callback_data="cancel_admin_news"))
        await callback.message.edit_text(
            "📢 Пришлите сообщение, которое хотите разослать участникам:",
            reply_markup=markup
        )
        save_user_state(user_id, "admin_news", None, callback.message.message_id)
        await AdminStates.waiting_for_news.set()
        logging.info(f"Состояние установлено для user_id {user_id}: AdminStates.waiting_for_news")
        current_state = await state.get_state()  # Проверяем, какое состояние установлено
        logging.info(f"Текущее состояние для user_id {user_id}: {current_state}")

    elif callback.data == "admin_view_rating":
        top_users = get_top_users()

        if not top_users:
            text = "⚠️ Пока нет данных для рейтинга."
        else:
            text = "🏆 <b>Топ-10 участников:</b>\n\n"
            for i, user in enumerate(top_users, start=1):
                name = user.get("name", "Без имени")
                username = user.get("username", "").strip()
                user_id_str = user.get("user_id", "")
                if username:
                    clean_username = username.lstrip("@")
                    link = f"https://t.me/{clean_username}"
                else:
                    link = f"tg://user?id={user_id_str}"
                text += f"{i}. <a href='{link}'>{name}</a> — {user['count']} заявок, {user['total']} баллов\n"

        try:
            await callback.message.edit_text(
                text,
                reply_markup=admin_menu_markup(),
                parse_mode="HTML"
            )
        except MessageNotModified:
            pass
        save_user_state(user_id, "admin_panel", None, callback.message.message_id)

    elif callback.data == "admin_export_rating":
        export_rating_to_sheet()
        try:
            await callback.message.edit_text(
                "✅ Рейтинг выгружен в таблицу!",
                reply_markup=admin_menu_markup()
            )
        except MessageNotModified:
            pass
        save_user_state(user_id, "admin_panel", None, callback.message.message_id)

    elif callback.data == "cancel_admin_news":
        await state.finish()
        clear_user_state(user_id)
        try:
            await callback.message.edit_text(
                "❌ Рассылка отменена.",
                reply_markup=admin_menu_markup()
            )
        except MessageNotModified:
            pass
        save_user_state(user_id, "admin_panel", None, callback.message.message_id)

async def handle_approve(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if not is_admin(user_id):
        return

    submission_id = callback.data.split("_", 1)[1]
    pending_scores[user_id] = submission_id

    await callback.message.edit_reply_markup()
    msg = await callback.message.answer("Введите количество баллов, которые вы хотите назначить:")
    save_user_state(user_id, "waiting_for_score", {"submission_id": submission_id}, msg.message_id)
    await ScoreState.waiting_for_score.set()

async def handle_reject(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    await callback.message.edit_reply_markup()
    await callback.message.answer("Заявка отклонена. Пользователь не будет уведомлён.")
    msg = await callback.message.answer("🛡 Админ-панель:", reply_markup=admin_menu_markup())
    save_user_state(user_id, "admin_panel", None, msg.message_id)

async def receive_score(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    score_text = message.text.strip()

    if not score_text.isdigit():
        await message.answer("Пожалуйста, введите число.")
        return

    score = int(score_text)
    submission_id = pending_scores.get(user_id)

    if not submission_id:
        await message.answer("Что-то пошло не так. Повторите подтверждение заявки.")
        await state.finish()
        await send_admin_panel(message)
        return

    result = set_score_and_notify_user(submission_id, score)

    if result:
        user_id_str = submission_id.split("_")[0]
        update_user_score_in_activity(user_id_str)
        await message.answer("✅ Баллы записаны, участник уведомлён.")
    else:
        await message.answer("⚠️ Не удалось обновить баллы. Возможно, заявка не найдена.")

    await send_admin_panel(message)
    await state.finish()
    pending_scores.pop(user_id, None)

async def send_news_to_users(message: types.Message, state: FSMContext):
    logging.info(f"send_news_to_users вызван для user_id {message.from_user.id} с текстом: {message.text}")
    user_id = message.from_user.id
    await state.finish()
    clear_user_state(user_id)
    users = get_all_user_ids()
    sent = 0
    for user_id in users:
        try:
            if message.photo:
                await message.bot.send_photo(user_id, message.photo[-1].file_id, caption=message.caption or "", reply_markup=main_menu_markup(user_id=user_id))
            elif message.video:
                await message.bot.send_video(user_id, message.video.file_id, caption=message.caption or "", reply_markup=main_menu_markup(user_id=user_id))
            elif message.text:
                await message.bot.send_message(user_id, message.text, reply_markup=main_menu_markup(user_id=user_id))
            sent += 1
        except Exception as e:
            logging.warning(f"[ERROR] Не удалось отправить {user_id}: {e}")

    await message.answer(f"✅ Рассылка завершена. Отправлено {sent} пользователей.")
    msg = await message.answer("🛡 Админ-панель:", reply_markup=admin_menu_markup())
    save_user_state(user_id, "admin_panel", None, msg.message_id)

def register_admin_handlers(dp: Dispatcher):
    dp.register_message_handler(admin_start, commands=["admin"], state="*")
    dp.register_callback_query_handler(handle_admin_panel, text=[
        "admin_view_apps", "admin_set_scores", "admin_send_news", "admin_view_rating", "admin_export_rating", "cancel_admin_news"
    ], state="*")
    dp.register_callback_query_handler(handle_approve, text_startswith="approve_", state="*")
    dp.register_callback_query_handler(handle_reject, text_startswith="reject_", state="*")
    dp.register_message_handler(receive_score, state=ScoreState.waiting_for_score)
    dp.register_message_handler(send_news_to_users, content_types=types.ContentTypes.ANY, state=AdminStates.waiting_for_news)
