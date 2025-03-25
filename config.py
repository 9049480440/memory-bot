# config.py

import os
from oauth2client.service_account import ServiceAccountCredentials

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Пытаемся прочитать путь из переменной окружения.
# Если переменной нет — берём путь по умолчанию.
CREDENTIALS_FILE = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "google-credentials.json")

creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)

BOT_TOKEN = '7882594246:AAEkoqOtdJoA1hk7yBRKPiYchORNhvm4wNY'

# ID и название Google Таблицы
SPREADSHEET_ID = '1_G8dY5NMro0cari71Be9eT9htiVgRWJ3rcQXfZUI_F8'
ACTIVITY_SHEET_NAME = 'Активность'

# Ссылка на положение
RULES_LINK = 'https://disk.yandex.ru/i/RFyutWLZU5VCeg'
