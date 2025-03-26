# services/sheets.py

import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config import SPREADSHEET_ID, ACTIVITY_SHEET_NAME

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

# Аутентификация с использованием переменной окружения
creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
if not creds_json:
    raise ValueError("GOOGLE_CREDENTIALS_JSON is not set or is empty.")

creds_dict = json.loads(creds_json)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)

client = gspread.authorize(creds)
sheet = client.open_by_key(SPREADSHEET_ID).worksheet(ACTIVITY_SHEET_NAME)

def add_or_update_user(user):
    user_id = str(user.id)
    all_users = sheet.get_all_values()
    user_ids = [row[0] for row in all_users[1:]]  # пропускаем заголовок

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

# Новая функция для сохранения заявки
def submit_application(user, date_text, location, monument_name):
    try:
        # Если существует отдельный лист для заявок
        sheet_app = client.open_by_key(SPREADSHEET_ID).worksheet("Заявки")
    except Exception:
        # Если лист "Заявки" не найден, используем лист "Активность"
        sheet_app = sheet

    new_row = [
        str(user.id),
        user.username or "",
        user.full_name,
        date_text,
        location,
        monument_name,
        "=TODAY()"
    ]
    sheet_app.append_row(new_row)

def get_user_scores(user_id: str):
    try:
        sheet_app = client.open_by_key(SPREADSHEET_ID).worksheet("Заявки")
    except Exception:
        return [], 0  # Если лист не найден

    all_rows = sheet_app.get_all_values()[1:]  # Пропускаем заголовок
    user_rows = [row for row in all_rows if row[0] == user_id]

    results = []
    total_score = 0

    for row in user_rows:
        date = row[3] if len(row) > 3 else ""
        location = row[4] if len(row) > 4 else ""
        name = row[5] if len(row) > 5 else ""
        try:
            score = int(row[6]) if len(row) > 6 and row[6].isdigit() else 0
        except:
            score = 0
        total_score += score
        results.append(f"📍 {name} ({location}, {date}) — {score} баллов")

    return results, total_score
