# handlers/gpt_handler.py

import openai
from config import OPENAI_API_KEY

openai.api_key = OPENAI_API_KEY

async def ask_gpt(message_text):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ты — помощник по конкурсу 'Эстафета Победы'. Отвечай кратко и по делу."},
                {"role": "user", "content": message_text}
            ],
            max_tokens=300
        )
        return response['choices'][0]['message']['content']
    except Exception as e:
        return "Извините, я пока не могу ответить. Попробуйте позже."
