# handlers/fallback_handler.py

from aiogram import types, Dispatcher
from handlers.gpt_handler import ask_gpt

# Если пользователь пишет странное сообщение
async def handle_unknown(message: types.Message):
    text = message.text.strip()

    if text.startswith("http"):
        await message.answer("Это заявка на конкурс? Если да — нажмите «📨 Подать заявку», чтобы мы её учли.")
        return

    if "?" in text or len(text.split()) > 3:
        await message.answer("Вы задали вопрос. Сейчас постараюсь ответить...")
        answer = await ask_gpt(text)
        await message.answer(answer)
        return

    await message.answer("Вы хотите подать заявку или задать вопрос?")
    
def register_fallback(dp: Dispatcher):
    dp.register_message_handler(handle_unknown, content_types=types.ContentTypes.TEXT, state="*")
