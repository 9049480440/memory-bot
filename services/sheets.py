#sheets.py

import os
import json
import gspread
import time
import datetime
from oauth2client.service_account import ServiceAccountCredentials
from config import SPREADSHEET_ID, ACTIVITY_SHEET_NAME
import logging

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
            # Обновляем username и имя, если они изменились
            sheet.update_cell(idx, 2, user.username or '')
            sheet.update_cell(idx, 3, user.full_name)
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
        print(f"[ERROR] update_user_score_in_activity: {e}")

# 📤 Экспорт рейтинга в Google Таблицу
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
            # Формируем ссылку: если есть username, используем его, иначе user_id
            if username:
                link = f"https://t.me/{username.lstrip('@')}"
            else:
                link = f"tg://user?id={user_id}"
            total = user.get("total", 0)

            sheet_app.append_row([
                user_id,
                name,
                username,
                link,
                total
            ])
    except Exception as e:
        print(f"[ERROR] export_rating_to_sheet: {e}")

# ✅ Подача заявки + возврат ID
def submit_application(user, date_text, location, monument_name, link):
    try:
        sheet_app = client.open_by_key(SPREADSHEET_ID).worksheet("Заявки")
    except Exception:
        print("[ERROR] Лист 'Заявки' не найден.")
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
        print(f"[ERROR] Не удалось добавить заявку: {e}")
        return None

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

# 📬 Отправка напоминаний неактивным участникам
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
                "Вернись в конкурс 'Эстафета Победы' и заработай баллы! Подай заявку через /start."
            )
            print(f"[INFO] Напоминание отправлено {user_id}")
        except Exception as e:
            print(f"[ERROR] Не удалось отправить напоминание {user_id}: {e}")

# 📊 Получение статистики по заявкам
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

# ✅ Проставить баллы и уведомить участника
def set_score_and_notify_user(submission_id: str, score: int):
    try:
        sheet_app = client.open_by_key(SPREADSHEET_ID).worksheet("Заявки")
        rows = sheet_app.get_all_values()
        headers = rows[0]
        data = rows[1:]

        for idx, row in enumerate(data, start=2):
            if len(row) >= 4 and row[3] == submission_id:
                user_id = int(row[0])
                sheet_app.update_cell(idx, 9, str(score))
                logging.info(f"[INFO] Баллы {score} записаны для submission_id {submission_id}")

                import asyncio
                loop = asyncio.get_event_loop()
                loop.create_task(send_score_notification(user_id, score))
                return True

        logging.warning(f"[WARNING] Заявка с submission_id {submission_id} не найдена")
        return False
    except Exception as e:
        logging.error(f"[ERROR] Ошибка при выставлении баллов: {e}")
        return False

# 📬 Уведомление участнику
async def send_score_notification(user_id: int, score: int):
    from main import bot
    try:
        await bot.send_message(
            user_id,
            f"🎉 Ваша заявка подтверждена!\n"
            f"Вам начислено {score} балл(ов).\n"
            f"Поздравляем и желаем удачи — вы на пути к победе! 💪"
        )
        logging.info(f"[INFO] Уведомление отправлено пользователю {user_id}")
    except Exception as e:
        logging.error(f"[ERROR] Не удалось отправить сообщение участнику {user_id}: {e}")

# 📬 Получить список всех user_id, кто подавал заявки
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
        print(f"[ERROR] get_all_user_ids: {e}")
        return []

# 📊 Получение рейтинга участников
def get_top_users(limit=10):
    try:
        sheet_app = client.open_by_key(SPREADSHEET_ID).worksheet("Заявки")
        rows = sheet_app.get_all_values()[1:]
    except Exception as e:
        print(f"[ERROR] get_top_users: {e}")
        return []

    # Получаем usernames из листа "Активность"
    activity_usernames = {}
    if sheet:
        activity_rows = sheet.get_all_values()[1:]
        for row in activity_rows:
            if len(row) >= 2:
                user_id = row[0]
                username = row[1].strip()
                if username:
                    activity_usernames[user_id] = username

    stats = {}

    for row in rows:
        if len(row) < 9:
            continue

        user_id = row[0]
        username = row[1].strip()
        name = row[2]
        score_str = row[8]

        # Если username пустой в "Заявках", берём из "Активности"
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
