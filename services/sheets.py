import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config import SPREADSHEET_ID, ACTIVITY_SHEET_NAME

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Подключение через переменную среды
creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)

client = gspread.authorize(creds)
sheet = client.open_by_key(SPREADSHEET_ID).worksheet(ACTIVITY_SHEET_NAME)

def add_or_update_user(user):
    user_id = str(user.id)
    all_users = sheet.get_all_values()
    user_ids = [row[0] for row in all_users[1:]]

    if user_id in user_ids:
        idx = user_ids.index(user_id) + 2
        sheet.update_cell(idx, 4, '=TODAY()')
        sheet.update_cell(idx, 5, 'вход')
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
