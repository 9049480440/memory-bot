from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from services.sheets import add_or_update_user, get_user_scores

# 📌 Узнать о конкурсе
async def info_about_competition(message: types.Message, state: FSMContext):
    await state.finish()  # если анкета была — сбросить
    await message.answer(
        "📍 Конкурс приурочен к 80-летию Победы и Году Защитника Отечества.\n\n"
        "Участвуйте, публикуйте посты у памятников, копите баллы и получайте призы!\n\n"
        "📄 Подробнее: https://docs.google.com/document/d/your-link-here"
    )

# ⭐️ Мои баллы
async def show_user_scores(message: types.Message, state: FSMContext):
    await state.finish()  # если анкета была — сбросить
    user_id = str(message.from_user.id)
    results, total = get_user_scores(user_id)
    if not results:
        await message.answer("У вас пока нет заявок. Подайте первую, нажав «📨 Подать заявку»!")
    else:
        await message.answer(f"Ваши заявки:\n\n" + "\n\n".join(results) + f"\n\n🌟 Всего баллов: {total}")

# /start
async def start(message: types.Message, state: FSMContext):
    await state.finish()  # сброс состояния, если что-то висело
    add_or_update_user(message.from_user)

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("📌 Узнать о конкурсе")
    keyboard.add("📨 Подать заявку")
    keyboard.add("⭐️ Мои баллы")

    await message.answer("Добро пожаловать! Выберите действие 👇", reply_markup=keyboard)

# Регистрация
def register_handlers(dp: Dispatcher):
    dp.register_message_handler(start, commands=["start"], state="*")
    dp.register_message_handler(info_about_competition, text="📌 Узнать о конкурсе", state="*")
    dp.register_message_handler(show_user_scores, text="⭐️ Мои баллы", state="*")
