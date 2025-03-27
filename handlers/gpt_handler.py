# handlers/gpt_handler.py

from openai import OpenAI
from config import OPENAI_API_KEY, ADMIN_IDS
from services.common import admin_menu_markup
import logging

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
- Если сомневаешься, дай вежливый ответ и направь к организатору

🎓 Если не можешь точно оценить памятник:
- Напиши: “Это может зависеть от контекста. Рекомендую уточнить у организатора конкурса: @sibi_sibi”

Отвечай доброжелательно, кратко, по делу. Помогай участникам разобраться в правилах.
"""

async def ask_gpt(user_id: int, text: str, bot):
    # Предварительная фильтрация
    if len(text.strip()) < 5 or len(text) > 300:
        await bot.send_message(user_id, "Пожалуйста, уточните вопрос — он слишком короткий или длинный.")
        return

    if all(char == text[0] for char in text.strip()):  # Пример: "ааааааа"
        await bot.send_message(user_id, "Вопрос выглядит непонятно. Попробуйте сформулировать иначе.")
        return

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": rules_summary},
                {"role": "user", "content": text}
            ],
            max_tokens=400
        )
        answer = response.choices[0].message.content
        await bot.send_message(user_id, answer)
        if user_id in ADMIN_IDS:
            await bot.send_message(user_id, "🛡 Админ-панель:", reply_markup=admin_menu_markup())
    except Exception as e:
        logging.error(f"[GPT ERROR] {e}")
        await bot.send_message(user_id, "Извините, я пока не могу ответить. Попробуйте позже.")

def register_gpt_handler(dp):
    pass  # GPT больше не перехватывает глобально, вызывается вручную

