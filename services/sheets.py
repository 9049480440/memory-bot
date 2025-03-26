import json
import gspread
import time
from oauth2client.service_account import ServiceAccountCredentials
from config import SPREADSHEET_ID, ACTIVITY_SHEET_NAME  # <-- теперь оттуда берём ID

# Авторизация
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
if not creds_json:
    raise ValueError("GOOGLE_CREDENTIALS_JSON is not set or is empty.")
creds_dict = json.loads(creds_json)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# Попытка открыть лист "Активность"
try:
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet(ACTIVITY_SHEET_NAME)
except Exception:
    sheet = None  # если нет — не критично

# ✅ Добавление пользователя
def add_or_update_user(user):
    if sheet is None:
        print("[WARNING] Лист 'Активность' не найден. Пропускаем сохранение пользователя.")
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
            print(f"[INFO] Новый пользователь добавлен: {user.full_name} ({user.id})")
    except Exception as e:
        print(f"[ERROR] Не удалось добавить пользователя {user.full_name} ({user.id}): {e}")

# ✅ Подать заявку
def submit_application(user, date_text, location, monument_name, link):
    try:
        sheet_app = client.open_by_key(SPREADSHEET_ID).worksheet("Заявки")
    except Exception:
        print("[ERROR] Лист 'Заявки' не найден.")
        return

    submission_id = f"{user.id}_{int(time.time())}"
    new_row = [
        str(user.id),
        user.username or "",
        user.full_name,
        submission_id,
        link,
        date_text,
        location,
        "=TODAY()",
        "",
        ""
    ]
    sheet_app.append_row(new_row)

# ✅ Подсчёт баллов
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
