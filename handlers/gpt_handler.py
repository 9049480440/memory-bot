# handlers/gpt_handler.py

from openai import OpenAI
from config import OPENAI_API_KEY, ADMIN_IDS
from handlers.admin_handlers import send_admin_panel
import logging
from aiogram import Dispatcher, types

client = OpenAI(api_key=OPENAI_API_KEY)

rules_summary = """
Ты — помощник по конкурсу «Эстафета Победы. От памятника к памяти». Конкурс проводится в городе Снежинске с 1 апреля по 30 ноября 2025 года. Участвуют только жители города Снежинска.

Участники публикуют фото или видео у памятников или знаковых мест, связанных с защитой Отечества, и подают заявку через Telegram-бот. В публикации обязательно указывают хештег #ОтПамятникаКПамяти, дату и место.

📌 Вот как начисляются баллы:
- Памятник, посвящённый военным событиям в истории России — 3 балла
- Памятник, посвящённый трудовому подвигу в годы войны — 3 балла
- Именные памятники Героям Советского Союза — 4 балла
- Памятники городам Воинской или Трудовой Славы — 4 балла
- Музейные экспозиции на тему войны или труда — 4 балла
- Памятные доски, посвящённые защитникам, труду или военным событиям — 1 балл

🔍 Если пользователь спрашивает, подходит ли конкретный памятник:
- Сравни описание с критериями выше
- Если объект отражает идеи героизма, памяти, труда, защиты Родины — скорее всего, подходит
- Если сомневаешься, дай вежный ответ и направь к организатору

🎓 Если не можешь точно оценить памятник:
- Напиши: "Это может зависеть от контекста. Рекомендую уточнить у организатора конкурса: @sibi_sibi"

Отвечай доброжелательно, кратко, по делу. Помогай участникам разобраться в правилах.
"""

async def ask_gpt(message_or_text):
    """
    Обрабатывает запрос к GPT. Может принимать как объект сообщения, так и строку текста.
    """
    try:
        if isinstance(message_or_text, str):
            text = message_or_text
            user_id = None
        else:
            text = message_or_text.text
            user_id = message_or_text.from_user.id
            
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": rules_summary},
                {"role": "user", "content": text}
            ],
            max_tokens=400
        )
        answer = response.choices[0].message.content
        
        # Если передан объект сообщения, отправляем ответ
        if not isinstance(message_or_text, str):
            await message_or_text.answer(answer)
            # Если это админ, показываем админ-панель
            if user_id in ADMIN_IDS:
                await send_admin_panel(message_or_text)
        
        return answer
    except Exception as e:
        logging.error(f"GPT ERROR: {e}")
        if not isinstance(message_or_text, str):
            await message_or_text.answer("Извините, я пока не могу ответить. Попробуйте позже.")
        return "Извините, я пока не могу ответить. Попробуйте позже."

def register_gpt_handler(dp: Dispatcher):
    @dp.message_handler(lambda message: "?" in message.text)
    async def handle_gpt_question(message: types.Message):
        await ask_gpt(message)
