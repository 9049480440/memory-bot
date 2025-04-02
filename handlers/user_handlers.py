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
    await state.finish()
    user_id = message.from_user.id

    try:
        add_or_update_user(message.from_user)

        msg = await message.answer(
            "👋 *Добро пожаловать в конкурс «Эстафета Победы. От памятника к памяти»!* 🇷🇺\n\n"
            "Конкурс проходит с 1 апреля по 30 ноября 2025 года и посвящён 80-летию Победы и Году Защитника Отечества.\n\n"
            "Здесь вы можете подать заявку, узнать свои баллы и прочитать правила участия.\n"
            "Нажмите на одну из кнопок ниже, чтобы начать 👇",
            reply_markup=main_menu_markup(user_id),
            parse_mode="Markdown"
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
    await state.finish()
    user_id = callback.from_user.id
    current_state, state_data, last_message_id = get_user_state(user_id)

    if current_state.startswith("application_step"):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📝 Продолжить заявку", callback_data="continue_app"))
        markup.add(types.InlineKeyboardButton("🔄 Начать новую заявку", callback_data="apply"))
        markup.add(types.InlineKeyboardButton("🔙 Вернуться в меню", callback_data="back_to_menu"))

        try:
            await callback.message.edit_text(
                "У вас есть незавершенная заявка. Хотите продолжить её заполнение или начать новую?",
                reply_markup=markup
            )
        except Exception as e:
            logger.error(f"Error editing message: {e}")
            await callback.message.answer(
                "У вас есть незавершенная заявка. Хотите продолжить её заполнение или начать новую?",
                reply_markup=markup
            )
        return

    if callback.data == "info":
        text = (
            "📍 *Конкурс «Эстафета Победы. От памятника к памяти»*\n"
            "Посвящён 80-летию Победы и Году Защитника Отечества.\n\n"
            "🎯 *Что нужно сделать?*\n"
            "Сфотографируйтесь у памятника, мемориальной таблички или музейной экспозиции, связанной с защитой Отечества.\n"
            "Опубликуйте пост с хештегом `#ОтПамятникаКПамяти` в открытом доступе в соцсетях.\n"
            "После этого — подайте заявку через бот!\n\n"
            "📊 *Сколько баллов?*\n"
            "За один пост можно получить до *8 баллов* (в зависимости от объекта).\n"
            "Например, памятные доски — 4 балла, музеи и мемориалы — 8 баллов.\n\n"
            "🏆 *Наберите 80 баллов — и участвуйте в розыгрыше призов!*\n"
            "Главный розыгрыш состоится *9 декабря 2025 года — в День Героев Отечества*.\n"
            "Дополнительные призы — за креативность и активность!\n\n"
            "📎 *Правила конкурса:* [Смотреть документ](https://disk.yandex.ru/i/PZfquUnQau8XGA)\n\n"
            "❓ *Если остались вопросы — смело задавайте! Я здесь, чтобы помочь 🙂*"
        )
        try:
            await callback.message.edit_text(
                text,
                reply_markup=main_menu_markup(user_id),
                parse_mode='Markdown'
            )
            save_user_state(user_id, "main_menu", None, callback.message.message_id)
        except Exception as e:
            logger.error(f"Error updating message: {e}")
            await callback.message.answer(
                text,
                reply_markup=main_menu_markup(user_id),
                parse_mode='Markdown'
            )
            await callback.message.delete()

    elif callback.data == "apply":
        text = (
            "🚀 *Начинаем подачу заявки!*\n\n"
            "Сейчас я задам вам несколько простых вопросов. Пожалуйста, отвечайте на них по очереди.\n\n"
            "Вот что понадобится:\n"
            "1️⃣ Ссылка на вашу публикацию с хештегом `#ОтПамятникаКПамяти`\n"
            "2️⃣ Дата съёмки\n"
            "3️⃣ Населённый пункт, где сделано фото или видео\n"
            "4️⃣ Краткое описание (например: *памятник героям ВОВ в парке Победы*)\n\n"
            "Если всё готово — начинаем! ✨"
        )
        try:
            await callback.message.edit_text(text, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Error editing message: {e}")
            await callback.message.answer(text, parse_mode="Markdown")
            await callback.message.delete()
            
        await start_application(callback.message)

    elif callback.data == "continue_app":
        if current_state == "application_step_1":
            text = (
                "📎 Пожалуйста, пришлите ссылку на публикацию с фотографией у памятника.\n\n"
                "⚠️ *Обратите внимание:*\n"
                "- Одна заявка = одна ссылка = один пост.\n"
                "- Если у вас несколько постов с разными памятниками, нужно подать отдельную заявку для каждого.\n"
                "- Не присылайте ссылку, которая уже участвовала в конкурсе ранее.\n\n"
                "Спасибо за понимание!"
            )
            try:
                await callback.message.edit_text(
                    text,
                    reply_markup=cancel_markup(),
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.error(f"Error editing message: {e}")
                await callback.message.answer(
                    text,
                    reply_markup=cancel_markup(),
                    parse_mode="Markdown"
                )
                await callback.message.delete()
                
            await ApplicationState.waiting_for_link.set()

        elif current_state == "application_step_2":
            try:
                await callback.message.edit_text(
                    "Спасибо! Теперь введите дату съёмки (ДД.ММ.ГГГГ):",
                    reply_markup=cancel_markup()
                )
            except Exception as e:
                logger.error(f"Error editing message: {e}")
                await callback.message.answer(
                    "Спасибо! Теперь введите дату съёмки (ДД.ММ.ГГГГ):",
                    reply_markup=cancel_markup()
                )
                await callback.message.delete()
                
            await ApplicationState.waiting_for_date.set()
            
        elif current_state == "application_step_3":
            try:
                await callback.message.edit_text(
                    "Отлично! Теперь укажите, где была сделана съёмка — достаточно написать название населённого пункта, например: *Снежинск*.",
                    reply_markup=cancel_markup(),
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.error(f"Error editing message: {e}")
                await callback.message.answer(
                    "Отлично! Теперь укажите, где была сделана съёмка — достаточно написать название населённого пункта, например: *Снежинск*.",
                    reply_markup=cancel_markup(),
                    parse_mode="Markdown"
                )
                await callback.message.delete()
                
            await ApplicationState.waiting_for_location.set()
            
        elif current_state == "application_step_4":
            try:
                await callback.message.edit_text(
                    "Пожалуйста, напишите краткое название объекта — например: *мемориал Славы*, *памятник героям ВОВ*, *доска на здании школы №125*.\n\n"
                    "Если объект не имеет официального названия, просто опишите его коротко.",
                    reply_markup=cancel_markup(),
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.error(f"Error editing message: {e}")
                await callback.message.answer(
                    "Пожалуйста, напишите краткое название объекта — например: *мемориал Славы*, *памятник героям ВОВ*, *доска на здании школы №125*.\n\n"
                    "Если объект не имеет официального названия, просто опишите его коротко.",
                    reply_markup=cancel_markup(),
                    parse_mode="Markdown"
                )
                await callback.message.delete()
                
            await ApplicationState.waiting_for_name.set()

    elif callback.data == "back_to_menu":
        clear_user_state(user_id)
        try:
            await callback.message.edit_text(
                "👇 Главное меню:",
                reply_markup=main_menu_markup(user_id)
            )
            save_user_state(user_id, "main_menu", None, callback.message.message_id)
        except Exception as e:
            logger.error(f"Error editing message: {e}")
            msg = await callback.message.answer(
                "👇 Главное меню:",
                reply_markup=main_menu_markup(user_id)
            )
            save_user_state(user_id, "main_menu", None, msg.message_id)
            await callback.message.delete()

    elif callback.data == "scores":
        try:
            user_id_str = str(user_id)
            results, total = get_user_scores(user_id_str)

            if not results:
                text = (
                    "У вас пока нет заявок 😌\n"
                    "Подайте первую заявку — и начните зарабатывать баллы за участие в конкурсе!"
                )
            else:
                formatted_results = "\n\n".join(
                    [f"{i + 1}. {entry}" for i, entry in enumerate(results)]
                )
                text = (
                    "📋 *Ваши заявки:*\n\n"
                    f"{formatted_results}\n\n"
                    f"🌟 *Ваши баллы:* *{total}*\n\n"
                    "Наберите *80 баллов*, чтобы участвовать в розыгрыше призов! 🎁"
                )

            try:
                await callback.message.edit_text(
                    text,
                    reply_markup=main_menu_markup(user_id),
                    parse_mode="Markdown"
                )
                save_user_state(user_id, "main_menu", None, callback.message.message_id)
            except Exception as e:
                logger.error(f"Error editing message: {e}")
                msg = await callback.message.answer(
                    text,
                    reply_markup=main_menu_markup(user_id),
                    parse_mode="Markdown"
                )
                save_user_state(user_id, "main_menu", None, msg.message_id)
                await callback.message.delete()
        except Exception as e:
            logger.error(f"Error getting user scores: {e}")
            await callback.message.answer(
                "Произошла ошибка при получении баллов. Попробуйте снова через /menu"
            )

    elif callback.data == "admin_panel":
        if is_admin(user_id):
            try:
                await callback.message.edit_text("🛡 Админ-панель:", reply_markup=admin_menu_markup())
                save_user_state(user_id, "admin_panel", None, callback.message.message_id)
            except Exception as e:
                logger.error(f"Error editing message: {e}")
                msg = await callback.message.answer("🛡 Админ-панель:", reply_markup=admin_menu_markup())
                save_user_state(user_id, "admin_panel", None, msg.message_id)
                await callback.message.delete()
        else:
            await callback.message.answer("❌ У вас нет прав доступа.")

# Обработчики для медиафайлов
async def handle_media_in_main(message: types.Message):
    """Обрабатывает медиафайлы, когда пользователь в главном меню"""
    user_id = message.from_user.id
    
    media_type = "фото" if message.photo else "видео" if message.video else "аудио" if message.audio else "файл"
    
    await message.answer(
        f"Я получил ваш {media_type}, но не могу его обработать напрямую.\n\n"
        f"Если вы хотите подать заявку, пожалуйста, опубликуйте этот {media_type} в соцсетях "
        f"с хештегом #ОтПамятникаКПамяти, затем пришлите мне ссылку на публикацию через кнопку 'Подать заявку'.",
        reply_markup=main_menu_markup(user_id=user_id)
    )

# Регистрация
def register_handlers(dp: Dispatcher):
    dp.register_message_handler(start, commands=["start"], state="*")
    dp.register_callback_query_handler(handle_main_menu, text=[
        "info", "apply", "scores", "admin_panel", "continue_app", "back_to_menu"
    ], state="*")
    
    # Обработчик для медиафайлов
    dp.register_message_handler(
        handle_media_in_main,
        content_types=[
            types.ContentType.PHOTO, 
            types.ContentType.VIDEO, 
            types.ContentType.AUDIO, 
            types.ContentType.DOCUMENT,
            types.ContentType.VOICE,
            types.ContentType.STICKER
        ],
        state=None
    )
