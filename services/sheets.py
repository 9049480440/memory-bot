#sheets.py

import os
import json
import gspread
import time
import datetime
import logging
import asyncio
from oauth2client.service_account import ServiceAccountCredentials
from config import SPREADSHEET_ID, ACTIVITY_SHEET_NAME
from services.common import main_menu_markup

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
    logging.warning("[WARNING] Не удалось открыть лист 'Активность'")

# 📄 Лист состояния
try:
    state_sheet = client.open_by_key(SPREADSHEET_ID).worksheet("UserState")
except Exception:
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    state_sheet = spreadsheet.add_worksheet(title="UserState", rows="1000", cols="4")
    state_sheet.append_row(["user_id", "state", "data", "last_message_id"])

def add_or_update_user(user):
    if sheet is None:
        logging.warning("[WARNING] Лист 'Активность' не найден.")
        return
    try:
        user_id = str(user.id)
        all_users = sheet.get_all_values()
        user_ids = [row[0] for row in all_users[1:]]

        # Текущая дата в формате ДД.ММ.ГГГГ
        today_str = datetime.datetime.now().strftime("%d.%m.%Y")

        if user_id in user_ids:
            idx = user_ids.index(user_id) + 2
            sheet.update_cell(idx, 2, user.username or '')
            sheet.update_cell(idx, 3, user.full_name)
            sheet.update_cell(idx, 4, today_str)
        else:
            new_row = [
                str(user.id),
                user.username or '',
                user.full_name,
                today_str,
                'вход',
                '',
                '0'
            ]
            sheet.append_row(new_row)
    except Exception as e:
        logging.error(f"[ERROR] Пользователь не добавлен: {e}")


def is_duplicate_link(user_id, link):
    try:
        sheet_app = client.open_by_key(SPREADSHEET_ID).worksheet("Заявки")
        rows = sheet_app.get_all_values()[1:]
        for row in rows:
            if len(row) > 4 and row[0] == str(user_id) and row[4] == link:
                return True
        return False
    except Exception as e:
        logging.error(f"[ERROR] Проверка дубликата ссылки: {e}")
        return False

def update_user_score_in_activity(user_id):
    if sheet is None:
        return
    try:
        user_id = str(user_id)
        all_users = sheet.get_all_values()
        user_ids = [row[0] for row in all_users[1:]]
        if user_id in user_ids:
            idx = user_ids.index(user_id) + 2
            _, total = get_user_scores(user_id)
            sheet.update_cell(idx, 7, str(total))
    except Exception as e:
        logging.error(f"[ERROR] update_user_score_in_activity: {e}")

def export_rating_to_sheet():
    try:
        sheet_app = client.open_by_key(SPREADSHEET_ID).worksheet("Рейтинг")
        top_users = get_top_users(limit=100)

        sheet_app.clear()
        sheet_app.append_row(["user_id", "имя", "username", "telegram_link", "сколько_баллов"])

        for user in top_users:
            user_id = user.get("user_id", "")
            name = user.get("name", "")
            username = user.get("username", "").strip()
            link = f"https://t.me/{username.lstrip('@')}" if username else f"tg://user?id={user_id}"
            total = user.get("total", 0)
            sheet_app.append_row([user_id, name, username, link, total])
            logging.info(f"[INFO] Записан пользователь {user_id} — {link}")
    except Exception as e:
        logging.error(f"[ERROR] export_rating_to_sheet: {e}")

def submit_application(user, date_text, location, monument_name, link):
    try:
        sheet_app = client.open_by_key(SPREADSHEET_ID).worksheet("Заявки")
    except Exception:
        logging.error("[ERROR] Лист 'Заявки' не найден.")
        return None

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

    try:
        sheet_app.append_row(new_row)
        return submission_id
    except Exception as e:
        logging.error(f"[ERROR] Не удалось добавить заявку: {e}")
        return None

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

def set_score_and_notify_user(submission_id: str, score: int):
    try:
        sheet_app = client.open_by_key(SPREADSHEET_ID).worksheet("Заявки")
        rows = sheet_app.get_all_values()
        data = rows[1:]

        for idx, row in enumerate(data, start=2):
            if len(row) >= 4 and row[3] == submission_id:
                user_id = int(row[0])
                sheet_app.update_cell(idx, 9, str(score))
                logging.info(f"[INFO] Баллы {score} записаны для submission_id {submission_id}")
                asyncio.ensure_future(send_score_notification(user_id, score))
                return True

        logging.warning(f"[WARNING] Заявка с submission_id {submission_id} не найдена")
        return False
    except Exception as e:
        logging.error(f"[ERROR] set_score_and_notify_user: {e}")
        return False

async def send_score_notification(user_id: int, score: int):
    from main import bot
    try:
        await bot.send_message(
            user_id,
            f"🎉 Ваша заявка подтверждена!\n"
            f"Вам начислено {score} балл(ов).\n"
            f"Поздравляем и желаем удачи — вы на пути к победе! 💪",
            reply_markup=main_menu_markup(user_id=user_id)
        )
        logging.info(f"[INFO] Уведомление отправлено пользователю {user_id}")
    except Exception as e:
        logging.error(f"[ERROR] Не удалось отправить уведомление {user_id}: {e}")

def get_inactive_users(days=21):
    try:
        sheet_app = client.open_by_key(SPREADSHEET_ID).worksheet("Заявки")
    except Exception:
        logging.error("[ERROR] Лист 'Заявки' не найден.")
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
    inactive = []

    for user in user_data.values():
        days_since_submission = (now - user["last_submission"]).days
        if days_since_submission >= days:
            inactive.append({
                "user_id": user["user_id"],
                "username": user["username"],
                "days_since": days_since_submission
            })

    return inactive

def send_reminders_to_inactive(bot):
    inactive_users = get_inactive_users(days=21)
    for user in inactive_users:
        user_id = user["user_id"]
        username = user["username"]
        days_since = user["days_since"]
        try:
            bot.send_message(
                user_id,
                f"Привет, {username or 'участник'}! Ты не подавал заявки уже {days_since} дней. "
                "Вернись в конкурс 'Эстафета Победы' и заработай баллы! Подай заявку через /start.",
                reply_markup=main_menu_markup(user_id=user_id)
            )
            logging.info(f"[INFO] Напоминание отправлено {user_id}")
        except Exception as e:
            logging.error(f"[ERROR] Не удалось отправить напоминание {user_id}: {e}")

def get_submission_stats():
    try:
        sheet_app = client.open_by_key(SPREADSHEET_ID).worksheet("Заявки")
        rows = sheet_app.get_all_values()[1:]
    except Exception:
        return 0, 0

    user_ids = set()
    for row in rows:
        if len(row) >= 1:
            user_ids.add(row[0])
    return len(rows), len(user_ids)

def get_all_user_ids():
    try:
        sheet_app = client.open_by_key(SPREADSHEET_ID).worksheet("Заявки")
        rows = sheet_app.get_all_values()[1:]
        user_ids = set()
        for row in rows:
            if len(row) >= 1 and row[0].isdigit():
                user_ids.add(int(row[0]))
        return list(user_ids)
    except Exception as e:
        logging.error(f"[ERROR] get_all_user_ids: {e}")
        return []

def get_top_users(limit=10):
    try:
        sheet_app = client.open_by_key(SPREADSHEET_ID).worksheet("Заявки")
        rows = sheet_app.get_all_values()[1:]
    except Exception as e:
        logging.error(f"[ERROR] get_top_users: {e}")
        return []

    activity_usernames = {}
    if sheet:
        activity_rows = sheet.get_all_values()[1:]
        for row in activity_rows:
            if len(row) >= 2:
                user_id = row[0]
                username = row[1].strip()
                activity_usernames[user_id] = username

    stats = {}

    for row in rows:
        if len(row) < 9:
            continue

        user_id = row[0]
        username = row[1].strip()
        name = row[2]
        score_str = row[8]

        if not username and user_id in activity_usernames:
            username = activity_usernames[user_id]

        try:
            score = int(score_str) if score_str.strip().isdigit() else 0
        except:
            score = 0

        if user_id not in stats:
            stats[user_id] = {
                "user_id": user_id,
                "username": username,
                "name": name,
                "count": 0,
                "total": 0
            }

        stats[user_id]["count"] += 1
        stats[user_id]["total"] += score

    sorted_users = sorted(stats.values(), key=lambda u: u["total"], reverse=True)
    return sorted_users[:limit]

# === Состояние пользователя ===

def save_user_state(user_id, state, data=None, last_message_id=None):
    try:
        all_rows = state_sheet.get_all_values()
        user_ids = [row[0] for row in all_rows[1:]]
        user_id = str(user_id)

        if user_id in user_ids:
            idx = user_ids.index(user_id) + 2
            state_sheet.update_cell(idx, 2, state)
            state_sheet.update_cell(idx, 3, json.dumps(data) if data else "")
            if last_message_id:
                state_sheet.update_cell(idx, 4, str(last_message_id))
        else:
            new_row = [
                user_id,
                state,
                json.dumps(data) if data else "",
                str(last_message_id) if last_message_id else ""
            ]
            state_sheet.append_row(new_row)
    except Exception as e:
        logging.error(f"[ERROR] Не удалось сохранить состояние для user_id {user_id}: {e}")

def get_user_state(user_id):
    try:
        all_rows = state_sheet.get_all_values()
        user_id = str(user_id)
        for row in all_rows[1:]:
            if row[0] == user_id:
                state = row[1] if len(row) > 1 else "main_menu"
                data = json.loads(row[2]) if len(row) > 2 and row[2] else None
                last_message_id = int(row[3]) if len(row) > 3 and row[3].isdigit() else None
                return state, data, last_message_id
        return "main_menu", None, None
    except Exception as e:
        logging.error(f"[ERROR] Не удалось получить состояние для user_id {user_id}: {e}")
        return "main_menu", None, None

def clear_user_state(user_id):
    try:
        all_rows = state_sheet.get_all_values()
        user_ids = [row[0] for row in all_rows[1:]]
        user_id = str(user_id)

        if user_id in user_ids:
            idx = user_ids.index(user_id) + 2
            state_sheet.update_cell(idx, 2, "main_menu")
            state_sheet.update_cell(idx, 3, "")
            state_sheet.update_cell(idx, 4, "")
    except Exception as e:
        logging.error(f"[ERROR] Не удалось очистить состояние для user_id {user_id}: {e}")
