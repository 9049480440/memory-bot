# services/sheets.py

import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config import SPREADSHEET_ID, ACTIVITY_SHEET_NAME

# Эти scope нужны для работы с Google Sheets и Google Drive
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

# Считываем содержимое JSON из переменной окружения
creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")  # То, что вы добавили на Render.com

if not creds_json:
    # Если по какой-то причине переменная окружения пустая, выводим ошибку
    raise ValueError("GOOGLE_CREDENTIALS_JSON is not set or is empty.")

# Парсим строку как JSON
creds_dict = json.loads(creds_json)

# Создаём учетные данные сервисного аккаунта из словаря
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)

# Авторизация через gspread
client = gspread.authorize(creds)

# Открываем нужную таблицу по ID
sheet = client.open_by_key(SPREADSHEET_ID).worksheet(ACTIVITY_SHEET_NAME)

def add_or_update_user(user):
    user_id = str(user.id)
    all_users = sheet.get_all_values()
    user_ids = [row[0] for row in all_users[1:]]  # пропускаем заголовок

    if user_id in user_ids:
        # обновим только дату последнего входа
        idx = user_ids.index(user_id) + 2
        sheet.update_cell(idx, 4, '=TODAY()')
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
