import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config import SPREADSHEET_ID, ACTIVITY_SHEET_NAME

# Настройка доступа к таблице через переменную среды
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Загружаем JSON из переменной окружения (строкой)
creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)

# Подключаемся к Google Таблице
client = gspread.authorize(creds)
sheet = client.open_by_key(SPREADSHEET_ID).worksheet(ACTIVITY_SHEET_NAME)

# Добавляем или обновляем пользователя
def add_or_update_user(user):
    user_id = str(user.id)
    all_users = sheet.get_all_values()
    user_ids = [row[0] for row in all_users[1:]]  # пропускаем заголовок

    if user_id in user_ids:
        # обновим дату последнего входа
        idx = user_ids.index(user_id) + 2
        sheet.update_cell(idx, 4, '=TODAY()')
        sheet.update_cell(idx, 5, 'вход')
    else:
        # добавим нового пользователя
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
