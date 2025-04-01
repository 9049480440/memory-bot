# user_handlers.py

from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from services.sheets import add_or_update_user, get_user_scores, save_user_state, get_user_state
from handlers.application_handlers import start_application
from services.common import main_menu_markup, is_admin, admin_menu_markup

# Команда /start
async def start(message: types.Message, state: FSMContext):
    await state.finish()
    user_id = message.from_user.id
    add_or_update_user(message.from_user)
    msg = await message.answer(
        "Добро пожаловать в конкурс «Эстафета Победы»! 👇",
        reply_markup=main_menu_markup(user_id)
    )
    save_user_state(user_id, "main_menu", None, msg.message_id)

# Обработка кнопок меню
async def handle_main_menu(callback: types.CallbackQuery, state: FSMContext):
    await state.finish()
    user_id = callback.from_user.id
    current_state, _, last_message_id = get_user_state(user_id)

    # Если пользователь был в процессе подачи заявки, восстанавливаем состояние
    if current_state.startswith("application_step"):
        step = int(current_state.split("_")[-1])
        data, _ = await state.get_data(), last_message_id
        if step == 1:
            await callback.message.edit_text("Пожалуйста, пришлите ссылку на пост с фотографией у памятника.", reply_markup=cancel_markup)
            await ApplicationState.waiting_for_link.set()
        elif step == 2:
            await callback.message.edit_text("Спасибо! Теперь введите дату съёмки (ДД.ММ.ГГГГ):", reply_markup=cancel_markup)
            await ApplicationState.waiting_for_date.set()
        elif step == 3:
            await callback.message.edit_text("Отлично! Теперь введите место съёмки:", reply_markup=cancel_markup)
            await ApplicationState.waiting_for_location.set()
        elif step == 4:
            await callback.message.edit_text("Теперь введите название памятника или мероприятия:", reply_markup=cancel_markup)
            await ApplicationState.waiting_for_name.set()
        return

    if callback.data == "info":
        text = (
            "📍 Конкурс приурочен к 80-летию Победы и Году Защитника Отечества.\n\n"
            "Участвуйте, публикуйте посты у памятников, копите баллы и получайте призы!\n\n"
            "📄 Подробнее: https://docs.google.com/document/d/your-link-here"
        )
        await callback.message.edit_text(
            text,
            reply_markup=main_menu_markup(user_id)
        )
        save_user_state(user_id, "main_menu", None, callback.message.message_id)

    elif callback.data == "apply":
        await callback.message.edit_text("🚀 Начинаем подачу заявки!")
        await start_application(callback.message)

    elif callback.data == "scores":
        user_id_str = str(user_id)
        results, total = get_user_scores(user_id_str)
        if not results:
            text = "У вас пока нет заявок. Подайте первую — и получите баллы!"
        else:
            text = "Ваши заявки:\n\n" + "\n\n".join(results) + f"\n\n🌟 Всего баллов: {total}"

        await callback.message.edit_text(
            text,
            reply_markup=main_menu_markup(user_id)
        )
        save_user_state(user_id, "main_menu", None, callback.message.message_id)

    elif callback.data == "admin_panel":
        if is_admin(user_id):
            await callback.message.edit_text("🛡 Админ-панель:", reply_markup=admin_menu_markup())
            save_user_state(user_id, "admin_panel", None, callback.message.message_id)
        else:
            await callback.message.answer("❌ У вас нет прав доступа.")

# Регистрация
def register_handlers(dp: Dispatcher):
    dp.register_message_handler(start, commands=["start"], state="*")
    dp.register_callback_query_handler(handle_main_menu, text=["info", "apply", "scores", "admin_panel"], state="*")
