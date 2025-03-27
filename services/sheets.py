# sheets.py

import os
import json
import gspread
import time
import datetime
from oauth2client.service_account import ServiceAccountCredentials
from config import SPREADSHEET_ID, ACTIVITY_SHEET_NAME

# 🔐 Авторизация Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
if not creds_json:
    raise ValueError("GOOGLE_CREDENTIALS_JSON is not set or is empty.")
creds_dict = json.loads(creds_json)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# 📄 Активность
try:
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet(ACTIVITY_SHEET_NAME)
except Exception:
    sheet = None

def add_or_update_user(user):
    if sheet is None:
        print("[WARNING] Лист 'Активность' не найден.")
        return
    try:
        user_id = str(user.id)
        all_users = sheet.get_all_values()
        user_ids = [row[0] for row in all_users[1:]]
        if user_id in user_ids:
            idx = user_ids.index(user_id) + 2
            sheet.update_cell(idx, 4, '=TODAY()')
        else:
            new_row = [
                str(user.id),
                user.username or '',
                user.full_name,
                '=TODAY()',
                'вход',
                '',
                '0'
            ]
            sheet.append_row(new_row)
    except Exception as e:
        print(f"[ERROR] Пользователь не добавлен: {e}")

# 🔄 Обновление баллов в Активности
def update_user_score_in_activity(user_id, score):
    if sheet is None:
        return
    try:
        user_id = str(user_id)
        all_users = sheet.get_all_values()
        user_ids = [row[0] for row in all_users[1:]]
        if user_id in user_ids:
            idx = user_ids.index(user_id) + 2
            sheet.update_cell(idx, 7, str(score))
    except Exception as e:
        print(f"[ERROR] update_user_score_in_activity: {e}")

# 📤 Экспорт рейтинга
def export_rating_to_sheet():
    try:
        sheet_app = client.open_by_key(SPREADSHEET_ID).worksheet("Рейтинг")
        top_users = get_top_users(limit=100)

        sheet_app.clear()
        sheet_app.append_row(["user_id", "имя", "сколько_баллов"])

        for user in top_users:
            sheet_app.append_row([
                user.get("user_id", ""),
                user.get("name", ""),
                user.get("total", 0)
            ])
    except Exception as e:
        print(f"[ERROR] export_rating_to_sheet: {e}")

# остальные функции остаются без изменений
