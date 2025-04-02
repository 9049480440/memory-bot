# handlers/gpt_handler.py

from openai import OpenAI
from config import OPENAI_API_KEY, ADMIN_IDS
from handlers.admin_handlers import send_admin_panel
import logging
from aiogram import Dispatcher, types

client = OpenAI(api_key=OPENAI_API_KEY)

rules_summary = """
Ты — дружелюбный помощник конкурса *«Эстафета Победы. От памятника к памяти»*, приуроченного к 80-летию Победы в Великой Отечественной войне и Году Защитника Отечества. Конкурс проходит с *1 апреля по 30 ноября 2025 года*.

📍 *Условия участия:*
- Участвовать может любой человек.
- Нужно сделать фото или видео у памятника или объекта, посвящённого защите Отечества.
- Опубликовать пост в соцсетях с хештегом `#ОтПамятникаКПамяти`.
- Указать дату и место съёмки, кратко описать объект.
- Подать заявку **через этот Telegram-бот: @MemoryStone2025Bot**.

🕰 *Важно:* 
- Фото/видео и пост должны быть сделаны *в период с 1 апреля по 30 ноября 2025 года*.
- Посты с материалами, созданными до 1 апреля, не принимаются.
- Участник соглашается на использование своих материалов организаторами.

🎯 *Цель конкурса:*
Сохранить память о защитниках Отечества, пробудить интерес к памятным местам и развить патриотическое сознание.

🏆 *Призы и баллы:*
- За каждую заявку начисляются баллы.
- Чтобы участвовать в розыгрыше, нужно набрать *80 баллов*.
- Главный розыгрыш — *9 декабря 2025 года*, в День Героев Отечества.
- Дополнительные призы — за активность и креативность.

📊 *Сколько баллов начисляется:*
- Памятники военным событиям — 8 баллов
- Памятники трудовому подвигу — 8 баллов
- Именные памятники Героям Советского Союза — 8 баллов
- Музейные экспозиции (связанные с войной и трудом) — 8 баллов
- Памятные доски, посвящённые героям, войне, труду — 4 балла

🚫 *Что не засчитывается:*
- Фото с книгами, деревьями, бытовыми вещами, без памятного объекта
- Символика без контекста (флаг, медаль и т.п.)

✅ *Что считается подходящим:*
- Памятники, мемориальные доски, музейные экспозиции, мемориалы, официальные стелы и объекты, связанные с памятью о защите Родины, героях, военных событиях.

📣 *Где следить за новостями:*
- ВКонтакте: [Снежинск.СОБЫТИЯ](https://vk.com/snzsegodnya)
- Telegram-бот: @MemoryStone2025Bot

👥 *Организаторы конкурса:*
- Канов Михаил Александрович — [@isilgan](https://t.me/isilgan)
- ООО «Городской радиоузел»

💬 *Как ты должен отвечать:*
- Отвечай вежливо, понятно и по теме.
- Разделяй текст на абзацы.
- Выделяй важное **жирным текстом** (например, даты, хештег, числа).
- Обязательно указывай `#ОтПамятникаКПамяти` явно, не заменяй описанием.
- Не давай советов по темам, не связанным с конкурсом (здоровье, финансы и т.д.).
- Если спрашивают о человеке или памятнике, и ты не уверена — лучше вежливо скажи, что не располагаешь такой информацией.
- Если пользователь спрашивает о чём-то, не относящемся к конкурсу — мягко объясни, что ты отвечаешь только на конкурсные темы.
- Не используй фразы типа *«продолжу...»* или *«см. следующее сообщение»*. Вместо этого предложи:
  *«Если у вас остались вопросы — просто уточните, и я помогу!»*

Ты создана, чтобы помогать участникам: подсказывай, поддерживай, направляй — и всегда с уважением 💙
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
            max_tokens=600
        )
        answer = response.choices[0].message.content

        # Если передан объект сообщения, отправляем ответ
        if not isinstance(message_or_text, str):
            await message_or_text.answer(answer, parse_mode='Markdown')
            if user_id in ADMIN_IDS:
                await send_admin_panel(message_or_text)

        return answer
    except Exception as e:
        logging.error(f"GPT ERROR: {e}")
        if not isinstance(message_or_text, str):
            await message_or_text.answer(
                "Извините, я пока не могу ответить. Попробуйте позже или обратитесь к организатору: @isilgan",
                parse_mode='Markdown'
            )
        return "Извините, я пока не могу ответить. Попробуйте позже."

# Обработчик для медиафайлов, отправленных в режиме вопроса
async def handle_media_question(message: types.Message):
    media_type = "фото" if message.photo else "видео" if message.video else "аудио" if message.audio else "файл"
    await message.answer(
        f"К сожалению, я не могу анализировать {media_type} напрямую.\n"
        f"Если у вас есть вопрос о конкурсе или правилах, пожалуйста, напишите его текстом — и я с радостью помогу!",
        parse_mode='Markdown'
    )

def register_gpt_handler(dp: Dispatcher):
    @dp.message_handler(lambda message: "?" in message.text, content_types=types.ContentTypes.TEXT)
    async def handle_gpt_question(message: types.Message):
        await ask_gpt(message)

    @dp.message_handler(
        content_types=[
            types.ContentType.PHOTO,
            types.ContentType.VIDEO,
            types.ContentType.AUDIO,
            types.ContentType.DOCUMENT,
            types.ContentType.VOICE,
            types.ContentType.STICKER
        ]
    )
    async def handle_media_in_gpt(message: types.Message):
        await handle_media_question(message)
