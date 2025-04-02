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
- Участвовать может любой человек, выполнивший условия конкурса.
- Нужно сделать фото или видео у памятника (или знакового места), посвящённого защитникам Отечества.
- Опубликовать материал в соцсетях с хештегом `#ОтПамятникаКПамяти`
- Указать дату и место съёмки, и кратко описать объект.
- Подать заявку через Telegram-бот: @MemoryStone2025Bot

🎯 *Цель конкурса:*
Популяризация памяти о защитниках Отечества, развитие интереса к памятным местам, укрепление патриотического духа.

🏆 *Призы:*
- За каждую заявку начисляются баллы.
- Нужно набрать *80 баллов*, чтобы попасть в розыгрыш призов.
- Основной розыгрыш — *9 декабря 2025 года*, в День Героев Отечества.
- Также будут *дополнительные розыгрыши* за креативность и активность.

📊 *Система начисления баллов:*
- Памятники военным событиям — 8 баллов
- Памятники трудовому подвигу — 8 баллов
- Именные памятники Героям Советского Союза — 8 баллов
- Памятники городам Воинской или Трудовой Славы — 8 баллов
- Музейные экспозиции (война, труд) — 8 баллов
- Памятные доски защитникам, труду, войне — 4 балла

📌 *Какие объекты считаются подходящими:*
- Всё, что связано с защитой Отечества, героизмом, трудом, военной историей.
- Подходят памятники, доски, музеи, мемориальные комплексы, связанные с ВОВ и другими военными событиями.
- Если есть сомнения — предложи участнику свериться с критериями или уточнить у организаторов.

👥 *Организаторы конкурса:*
- Канов Михаил Александрович (@isilgan)
- ООО «Городской радиоузел»

📣 *Где читать новости о конкурсе:*
- VK: [Снежинск.СОБЫТИЯ](https://vk.com/snzsegodnya)
- Telegram-бот: @MemoryStone2025Bot

📌 *Важно:*
- Фото и видео должны быть сделаны *после 1 апреля 2025 года*.
- Участник соглашается на использование материалов организаторами.

💬 *Как отвечать:*
- Будь дружелюбным, говори по-человечески.
- Делай текст удобным: разделяй мысли на абзацы.
- Используй **жирный текст**, если это помогает выделить важное.
- Обязательно называй хештег `#ОтПамятникаКПамяти`, не заменяй его словами типа "определённый".
- Если не можешь точно ответить — скажи, что лучше уточнить у организаторов: @isilgan

Ты помогаешь участникам — объясняй, подсказывай, поддерживай!
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
            await message_or_text.answer(answer, parse_mode='Markdown')
            # Если это админ, показываем админ-панель
            if user_id in ADMIN_IDS:
                await send_admin_panel(message_or_text)

        return answer
    except Exception as e:
        logging.error(f"GPT ERROR: {e}")
        if not isinstance(message_or_text, str):
            await message_or_text.answer(
                "Извините, я пока не могу ответить. Попробуйте позже или обратитесь к организаторам: @isilgan", 
                parse_mode='Markdown'
            )
        return "Извините, я пока не могу ответить. Попробуйте позже."

# Обработчик для медиафайлов, отправленных в режиме вопроса
async def handle_media_question(message: types.Message):
    """Обрабатывает медиафайлы, отправленные в режиме вопроса к GPT"""
    media_type = "фото" if message.photo else "видео" if message.video else "аудио" if message.audio else "файл"
    
    await message.answer(
        f"К сожалению, я не могу анализировать {media_type} напрямую. Если у вас есть вопрос о конкурсе или правилах, "
        f"пожалуйста, напишите его текстом, и я с радостью отвечу!",
        parse_mode='Markdown'
    )

def register_gpt_handler(dp: Dispatcher):
    @dp.message_handler(lambda message: "?" in message.text, content_types=types.ContentTypes.TEXT)
    async def handle_gpt_question(message: types.Message):
        await ask_gpt(message)
        
    # Обработчик для медиафайлов в режиме вопроса
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
