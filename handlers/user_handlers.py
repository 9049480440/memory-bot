# user_handlers.py

from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
import logging
from services.sheets import add_or_update_user, get_user_scores, save_user_state, get_user_state, clear_user_state
from handlers.application_handlers import start_application, ApplicationState, cancel_markup
from services.common import main_menu_markup, is_admin, admin_menu_markup

logger = logging.getLogger(__name__)

# Команда /start
async def start(message: types.Message, state: FSMContext):
    """Обработчик команды /start"""
    await state.finish()
    user_id = message.from_user.id
    
    try:
        # Добавляем или обновляем информацию о пользователе
        add_or_update_user(message.from_user)
        
        # Отправляем приветствие и главное меню
        msg = await message.answer(
            "Добро пожаловать в конкурс «Эстафета Победы»! 👇",
            reply_markup=main_menu_markup(user_id)
        )
        save_user_state(user_id, "main_menu", None, msg.message_id)
        logger.info(f"User {user_id} started the bot")
    except Exception as e:
        logger.error(f"Error in start handler: {e}")
        await message.answer(
            "Произошла ошибка при запуске. Пожалуйста, попробуйте снова с помощью /start."
        )

# Обработка кнопок меню
async def handle_main_menu(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик нажатий на кнопки главного меню"""
    await state.finish()
    user_id = callback.from_user.id
    current_state, state_data, last_message_id = get_user_state(user_id)

    # Проверяем, был ли пользователь в процессе подачи заявки
    if current_state.startswith("application_step"):
        step = int(current_state.split("_")[-1])
        
        # В зависимости от шага, предлагаем продолжить заполнение
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📝 Продолжить заявку", callback_data="continue_app"))
        markup.add(types.InlineKeyboardButton("🔄 Начать новую заявку", callback_data="apply"))
        markup.add(types.InlineKeyboardButton("🔙 Вернуться в меню", callback_data="back_to_menu"))
        
        await callback.message.edit_text(
            "У вас есть незавершенная заявка. Хотите продолжить её заполнение или начать новую?",
            reply_markup=markup
        )
        return

    if callback.data == "info":
        text = (
            "📍 Конкурс приурочен к 80-летию Победы и Году Защитника Отечества.\n\n"
            "Участвуйте, публикуйте посты у памятников, копите баллы и получайте призы!\n\n"
            "📄 Подробнее: https://docs.google.com/document/d/your-link-here"
        )
        try:
            await callback.message.edit_text(
                text,
                reply_markup=main_menu_markup(user_id)
            )
            save_user_state(user_id, "main_menu", None, callback.message.message_id)
        except Exception as e:
            logger.error(f"Error updating message: {e}")
            await callback.message.answer(
                "Произошла ошибка. Попробуйте снова через /menu"
            )

    elif callback.data == "apply":
        await callback.message.edit_text("🚀 Начинаем подачу заявки!")
        await start_application(callback.message)

    elif callback.data == "continue_app":
        # Продолжаем заполнение с текущего шага
        if current_state == "application_step_1":
            await callback.message.edit_text(
                "Пожалуйста, пришлите ссылку на пост с фотографией у памятника:",
                reply_markup=cancel_markup()
            )
            await ApplicationState.waiting_for_link.set()
        elif current_state == "application_step_2":
            await callback.message.edit_text(
                "Спасибо! Теперь введите дату съёмки (ДД.ММ.ГГГГ):",
                reply_markup=cancel_markup()
            )
            await ApplicationState.waiting_for_date.set()
        elif current_state == "application_step_3":
            await callback.message.edit_text(
                "Отлично! Теперь введите место съёмки:",
                reply_markup=cancel_markup()
            )
            await ApplicationState.waiting_for_location.set()
        elif current_state == "application_step_4":
            await callback.message.edit_text(
                "Теперь введите название памятника или мероприятия:",
                reply_markup=cancel_markup()
            )
            await ApplicationState.waiting_for_name.set()

    elif callback.data == "back_to_menu":
        # Возвращаемся в главное меню
        clear_user_state(user_id)
        await callback.message.edit_text(
            "👇 Главное меню:",
            reply_markup=main_menu_markup(user_id)
        )
        save_user_state(user_id, "main_menu", None, callback.message.message_id)

    elif callback.data == "scores":
        try:
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
        except Exception as e:
            logger.error(f"Error getting user scores: {e}")
            await callback.message.answer(
                "Произошла ошибка при получении баллов. Попробуйте снова через /menu"
            )

    elif callback.data == "admin_panel":
        if is_admin(user_id):
            await callback.message.edit_text("🛡 Админ-панель:", reply_markup=admin_menu_markup())
            save_user_state(user_id, "admin_panel", None, callback.message.message_id)
        else:
            await callback.message.answer("❌ У вас нет прав доступа.")

# Регистрация
def register_handlers(dp: Dispatcher):
    dp.register_message_handler(start, commands=["start"], state="*")
    dp.register_callback_query_handler(handle_main_menu, text=[
        "info", "apply", "scores", "admin_panel", "continue_app", "back_to_menu"
    ], state="*")
