from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMIN_IDS

def main_menu_markup(user_id=None):
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("📌 Узнать о конкурсе", callback_data="info"),
        InlineKeyboardButton("📨 Подать заявку", callback_data="apply"),
        InlineKeyboardButton("⭐️ Мои баллы", callback_data="scores"),
    )
    if user_id and int(user_id) in ADMIN_IDS:
        markup.add(InlineKeyboardButton("🛡 Админ-панель", callback_data="admin_panel"))
    return markup
