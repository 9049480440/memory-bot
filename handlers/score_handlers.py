from aiogram import types, Dispatcher
from services.sheets import get_user_applications

async def my_scores(message: types.Message):
    user_id = str(message.from_user.id)
    apps = get_user_applications(user_id)
    if not apps:
        await message.answer("Вы ещё не подавали заявок.")
    else:
        text = "Ваши заявки и баллы:\n\n"
        total = 0
        for app in apps:
            # app: [user_id, username, full_name, дата, место, название, баллы]
            points = app[6] if len(app) >= 7 else "0"
            try:
                points_val = int(points)
            except:
                points_val = 0
            total += points_val
            text += f"Дата: {app[3]}, Место: {app[4]}, Название: {app[5]}, Баллы: {points}\n"
        text += f"\nОбщая сумма баллов: {total}"
        await message.answer(text)

def register_score_handlers(dp: Dispatcher):
    dp.register_message_handler(my_scores, lambda msg: msg.text == "⭐️ Мои баллы")
