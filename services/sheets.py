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

# ➕ Добавление пользователя или обновление даты входа
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

# ✅ Подача заявки
def submit_application(user, date_text, location, monument_name, link):
    try:
        sheet_app = client.open_by_key(SPREADSHEET_ID).worksheet("Заявки")
    except Exception:
        print("[ERROR] Лист 'Заявки' не найден.")
        return

    submission_id = f"{user.id}_{int(time.time())}"
    submitted_at = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")

    new_row = [
        str(user.id),
        user.username or "",
        user.full_name,
        submission_id,
        link,
        date_text,
        location,
        submitted_at,
        "",
        ""
    ]
    sheet_app.append_row(new_row)

# ⭐️ Получение баллов пользователя
def get_user_scores(user_id: str):
    try:
        sheet_app = client.open_by_key(SPREADSHEET_ID).worksheet("Заявки")
    except Exception:
        return [], 0

    all_rows = sheet_app.get_all_values()[1:]
    user_rows = [row for row in all_rows if row[0] == user_id]

    results = []
    total_score = 0

    for row in user_rows:
        link = row[4] if len(row) > 4 else ""
        date = row[5] if len(row) > 5 else ""
        location = row[6] if len(row) > 6 else ""
        name = row[3] if len(row) > 3 else ""
        try:
            score = int(row[8]) if len(row) > 8 and row[8].isdigit() else 0
        except:
            score = 0
        total_score += score
        results.append(f"📍 {name} ({location}, {date}) — {score} баллов\n🔗 {link}")

    return results, total_score

# 📬 Поиск неактивных участников
def get_inactive_users(days=21):
    try:
        sheet_app = client.open_by_key(SPREADSHEET_ID).worksheet("Заявки")
    except Exception:
        print("[ERROR] Лист 'Заявки' не найден.")
        return []

    all_rows = sheet_app.get_all_values()[1:]
    user_data = {}

    for row in all_rows:
        if len(row) < 8:
            continue

        user_id = row[0]
        username = row[1]
        full_name = row[2]
        submitted_at_str = row[7]

        try:
            submitted_at = datetime.datetime.strptime(submitted_at_str.split(" ")[0], "%d.%m.%Y")
        except:
            continue

        if user_id not in user_data or submitted_at > user_data[user_id]["last_submission"]:
            user_data[user_id] = {
                "user_id": int(user_id),
                "username": username,
                "full_name": full_name,
                "last_submission": submitted_at
            }

    now = datetime.datetime.now()
    deadline = datetime.datetime(2025, 11, 30)
    inactive = []

    for user in user_data.values():
        days_since_submission = (now - user["last_submission"]).days
        if days_since_submission >= days:
            days_left = (deadline - now).days
            inactive.append({
                "user_id": user["user_id"],
                "username": user["username"],
                "days_left": days_left if days_left > 0 else 0
            })

    return inactive
