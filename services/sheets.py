# sheets.py

import os
import json
import gspread
import time
import datetime
import logging
from oauth2client.service_account import ServiceAccountCredentials
from config import SPREADSHEET_ID, ACTIVITY_SHEET_NAME
from services.common import main_menu_markup

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🔐 Авторизация Google Sheets с повторными попытками
def get_gspread_client(max_retries=3):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    
    if not creds_json:
        raise ValueError("GOOGLE_CREDENTIALS_JSON is not set or is empty.")
    
    creds_dict = json.loads(creds_json)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    
    # Повторные попытки подключения
    for attempt in range(max_retries):
        try:
            client = gspread.authorize(creds)
            return client
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Attempt {attempt+1} to connect to Google Sheets failed: {e}. Retrying...")
                time.sleep(2 ** attempt)  # Экспоненциальная задержка
            else:
                logger.error(f"Failed to connect to Google Sheets after {max_retries} attempts")
                raise

client = get_gspread_client()

# 📄 Получение листа Активность
try:
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet(ACTIVITY_SHEET_NAME)
except Exception as e:
    logger.error(f"Error accessing Activity sheet: {e}")
    sheet = None

# 📄 Лист для хранения состояния пользователей
try:
    state_sheet = client.open_by_key(SPREADSHEET_ID).worksheet("UserState")
except Exception:
    # Если лист не существует, создаём его
    try:
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        state_sheet = spreadsheet.add_worksheet(title="UserState", rows="1000", cols="4")
        state_sheet.append_row(["user_id", "state", "data", "last_message_id"])
        logger.info("Created new UserState worksheet")
    except Exception as e:
        logger.error(f"Failed to create UserState worksheet: {e}")
        state_sheet = None

def add_or_update_user(user):
    """Добавляет или обновляет информацию о пользователе в таблице Активность"""
    if sheet is None:
        logger.warning("[WARNING] Лист 'Активность' не найден.")
        return
    try:
        user_id = str(user.id)
        all_users = sheet.get_all_values()
        user_ids = [row[0] for row in all_users[1:]]
        
        current_date = datetime.datetime.now().strftime("%d.%m.%Y")
        
        if user_id in user_ids:
            idx = user_ids.index(user_id) + 2
            sheet.update_cell(idx, 2, user.username or '')
            sheet.update_cell(idx, 3, user.full_name)
            sheet.update_cell(idx, 4, current_date)
            sheet.update_cell(idx, 5, 'вход')
            logger.info(f"Updated user {user_id} in Activity sheet")
        else:
            new_row = [
                str(user.id),
                user.username or '',
                user.full_name,
                current_date,
                'вход',
                '',
                '0'
            ]
            sheet.append_row(new_row)
            logger.info(f"Added new user {user_id} to Activity sheet")
    except Exception as e:
        logger.error(f"[ERROR] Пользователь не добавлен: {e}")

def update_user_score_in_activity(user_id):
    """Обновляет количество баллов пользователя в таблице Активность"""
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
            logger.info(f"Updated score for user {user_id}: {total}")
    except Exception as e:
        logger.error(f"[ERROR] update_user_score_in_activity: {e}")

def export_rating_to_sheet():
    """Экспортирует рейтинг в отдельный лист"""
    try:
        sheet_app = client.open_by_key(SPREADSHEET_ID).worksheet("Рейтинг")
        top_users = get_top_users(limit=100)

        sheet_app.clear()
        sheet_app.append_row(["user_id", "имя", "username", "telegram_link", "сколько_баллов"])

        for user in top_users:
            user_id = user.get("user_id", "")
            name = user.get("name", "")
            username = user.get("username", "").strip()
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
            logger.info(f"[INFO] Записан пользователь {user_id} с username {username} и ссылкой {link}")
        
        return True
    except Exception as e:
        logger.error(f"[ERROR] export_rating_to_sheet: {e}")
        return False

def submit_application(user, date_text, location, monument_name, link):
    """Сохраняет заявку пользователя в таблицу Заявки"""
    logger.info(f"[DEBUG] submit_application вызвана с параметрами: date_text={date_text}, location={location}, monument_name={monument_name}, link={link}")
    
    try:
        sheet_app = client.open_by_key(SPREADSHEET_ID).worksheet("Заявки")
    except Exception as e:
        logger.error(f"[ERROR] Лист 'Заявки' не найден: {e}")
        return None

    submission_id = f"{user.id}_{int(time.time())}"
    submitted_at = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")

    # Строим массив в точном соответствии с порядком колонок в таблице
    # A         B          C      D           E       F        G        H          I      J
    # user_id | username | имя | заявка_id | ссылка | ответ_1 | ответ_2 | дата_подачи | баллы | комментарий_админа
    new_row = [
        str(user.id),             # user_id (A)
        user.username or "",      # username (B)
        user.full_name,           # имя (C)
        submission_id,            # заявка_id (D)
        link,                     # ссылка (E)
        date_text,                # ответ_1 (F) - дата съемки
        location,                 # ответ_2 (G) - город/место
        submitted_at,             # дата_подачи (H)
        "",                       # баллы (I)
        monument_name             # комментарий_админа (J) - название памятника
    ]

    try:
        sheet_app.append_row(new_row)
        logger.info(f"Application submitted successfully: {submission_id}, date: {date_text}, location: {location}, monument: {monument_name}")
        return submission_id
    except Exception as e:
        logger.error(f"[ERROR] Не удалось добавить заявку: {e}")
        return None

def get_user_scores(user_id: str):
    """Получает список заявок пользователя и общий счет"""
    try:
        sheet_app = client.open_by_key(SPREADSHEET_ID).worksheet("Заявки")
    except Exception as e:
        logger.error(f"[ERROR] Cannot access Applications sheet: {e}")
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

def get_inactive_users(days=21):
    """Получает список неактивных пользователей"""
    try:
        sheet_app = client.open_by_key(SPREADSHEET_ID).worksheet("Заявки")
    except Exception as e:
        logger.error(f"[ERROR] Лист 'Заявки' не найден: {e}")
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

async def send_reminders_to_inactive(bot):
    """Отправляет напоминания неактивным пользователям каждые 21 день, до 24 ноября 2025"""
    # Проверка на конец конкурса - 24 ноября 2025
    now = datetime.datetime.now()
    end_date = datetime.datetime(2025, 11, 24)

    if now > end_date:
        logger.info("[INFO] Конкурс завершен (после 24.11.2025), напоминания больше не отправляются")
        return

    # Получаем неактивных пользователей
    inactive_users = get_inactive_users(days=21)

    # Отправляем напоминания только тем, у кого количество дней с момента последней заявки
    # кратно 21 (21, 42, 63, 84, ...)
    for user in inactive_users:
        user_id = user["user_id"]
        username = user["username"]
        days_since = user["days_since"]

        # Проверяем, что дни с последней активности кратны 21
        if days_since % 21 == 0:
            try:
                await bot.send_message(
                    user_id,
                    f"Привет, {username or 'участник'}! Ты не подавал заявки уже {days_since} дней. "
                    "Вернись в конкурс 'Эстафета Победы' и заработай баллы! Подай заявку через /start.",
                    reply_markup=main_menu_markup(user_id=user_id)
                )
                logger.info(f"[INFO] Напоминание отправлено {user_id} (неактивен {days_since} дней)")
            except Exception as e:
                logger.error(f"[ERROR] Не удалось отправить напоминание {user_id}: {e}")

def get_submission_stats():
    """Получает статистику по заявкам"""
    try:
        sheet_app = client.open_by_key(SPREADSHEET_ID).worksheet("Заявки")
        rows = sheet_app.get_all_values()[1:]
    except Exception as e:
        logger.error(f"[ERROR] Cannot get submission stats: {e}")
        return 0, 0

    user_ids = set()
    for row in rows:
        if len(row) >= 1:
            user_ids.add(row[0])
    return len(rows), len(user_ids)

def set_score_and_notify_user(submission_id: str, score: int):
    """Устанавливает баллы для заявки и готовит данные для уведомления"""
    try:
        sheet_app = client.open_by_key(SPREADSHEET_ID).worksheet("Заявки")
        rows = sheet_app.get_all_values()
        headers = rows[0]
        data = rows[1:]

        for idx, row in enumerate(data, start=2):
            if len(row) >= 4 and row[3] == submission_id:
                user_id = row[0]
                sheet_app.update_cell(idx, 9, str(score))
                logger.info(f"[INFO] Баллы {score} записаны для submission_id {submission_id}")
                return True
        
        logger.warning(f"[WARNING] Заявка с submission_id {submission_id} не найдена")
        return False
    except Exception as e:
        logger.error(f"[ERROR] Ошибка при выставлении баллов: {e}")
        return False

async def send_score_notification(user_id: int, score: int, bot):
    """Отправляет уведомление пользователю о начислении баллов"""
    try:
        await bot.send_message(
            user_id,
            f"🎉 Ваша заявка подтверждена!\n"
            f"Вам начислено {score} балл(ов).\n"
            f"Поздравляем и желаем удачи — вы на пути к победе! 💪",
            reply_markup=main_menu_markup(user_id=user_id)
        )
        logger.info(f"[INFO] Уведомление отправлено пользователю {user_id}")
    except Exception as e:
        logger.error(f"[ERROR] Не удалось отправить сообщение участнику {user_id}: {e}")

def get_all_user_ids():
    """Получает список всех user_id пользователей"""
    try:
        sheet_app = client.open_by_key(SPREADSHEET_ID).worksheet("Заявки")
        rows = sheet_app.get_all_values()[1:]
        user_ids = set()
        for row in rows:
            if len(row) >= 1 and row[0].isdigit():
                user_ids.add(int(row[0]))
        return list(user_ids)
    except Exception as e:
        logger.error(f"[ERROR] get_all_user_ids: {e}")
        return []

def get_top_users(limit=10):
    """Получает список топ пользователей по баллам"""
    try:
        sheet_app = client.open_by_key(SPREADSHEET_ID).worksheet("Заявки")
        rows = sheet_app.get_all_values()[1:]
    except Exception as e:
        logger.error(f"[ERROR] get_top_users: {e}")
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

        if not username:
            logger.warning(f"[WARNING] Username для user_id {user_id} пустой после проверки Заявки и Активности")

        logger.info(f"[INFO] Для user_id {user_id}: username из Заявки = {row[1]}, из Активности = {activity_usernames.get(user_id, 'нет')}")

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

def check_sheet_structure():
    """Выводит структуру листа 'Заявки' для отладки"""
    try:
        sheet_app = client.open_by_key(SPREADSHEET_ID).worksheet("Заявки")
        headers = sheet_app.row_values(1)
        logger.info("[DEBUG] Структура листа 'Заявки':")
        for i, header in enumerate(headers):
            logger.info(f"[DEBUG] Колонка {i+1} (буква {chr(65+i)}): '{header}'")
    except Exception as e:
        logger.error(f"[ERROR] Ошибка при проверке структуры: {e}")

# Функции для работы с состоянием пользователей
def save_user_state(user_id, state, data=None, last_message_id=None):
    """Сохраняет состояние пользователя в Google Таблицах."""
    if state_sheet is None:
        logger.error("[ERROR] UserState sheet is not available")
        return
        
    try:
        all_rows = state_sheet.get_all_values()
        user_ids = [row[0] for row in all_rows[1:]]
        user_id = str(user_id)

        # Если пользователь уже есть, обновляем его состояние
        if user_id in user_ids:
            idx = user_ids.index(user_id) + 2
            state_sheet.update_cell(idx, 2, state)
            state_sheet.update_cell(idx, 3, json.dumps(data) if data else "")
            if last_message_id:
                state_sheet.update_cell(idx, 4, str(last_message_id))
            logger.info(f"Updated state for user {user_id}: {state}")
        else:
            # Если пользователя нет, добавляем новую строку
            new_row = [
                user_id,
                state,
                json.dumps(data) if data else "",
                str(last_message_id) if last_message_id else ""
            ]
            state_sheet.append_row(new_row)
            logger.info(f"Added new state for user {user_id}: {state}")
    except Exception as e:
        logger.error(f"[ERROR] Не удалось сохранить состояние для user_id {user_id}: {e}")

def get_user_state(user_id):
    """Получает состояние пользователя из Google Таблиц."""
    if state_sheet is None:
        logger.error("[ERROR] UserState sheet is not available")
        return "main_menu", None, None
        
    try:
        all_rows = state_sheet.get_all_values()
        user_id = str(user_id)
        for row in all_rows[1:]:
            if row[0] == user_id:
                state = row[1] if len(row) > 1 else "main_menu"
                data = json.loads(row[2]) if len(row) > 2 and row[2] else None
                last_message_id = int(row[3]) if len(row) > 3 and row[3].isdigit() else None
                return state, data, last_message_id
        return "main_menu", None, None  # По умолчанию
    except Exception as e:
        logger.error(f"[ERROR] Не удалось получить состояние для user_id {user_id}: {e}")
        return "main_menu", None, None

def clear_user_state(user_id):
    """Очищает состояние пользователя в Google Таблицах."""
    if state_sheet is None:
        logger.error("[ERROR] UserState sheet is not available")
        return
        
    try:
        all_rows = state_sheet.get_all_values()
        user_ids = [row[0] for row in all_rows[1:]]
        user_id = str(user_id)

        if user_id in user_ids:
            idx = user_ids.index(user_id) + 2
            state_sheet.update_cell(idx, 2, "main_menu")
            state_sheet.update_cell(idx, 3, "")
            state_sheet.update_cell(idx, 4, "")
            logger.info(f"Cleared state for user {user_id}")
    except Exception as e:
        logger.error(f"[ERROR] Не удалось очистить состояние для user_id {user_id}: {e}")
