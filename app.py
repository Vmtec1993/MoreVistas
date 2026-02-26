import os
import json
import gspread
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from oauth2client.service_account import ServiceAccountCredentials
import requests
from datetime import datetime

app = Flask(__name__)
app.secret_key = "morevistas_secure_2026"

# --- CONFIG ---
TELEGRAM_TOKEN = "7913354522:AAH1XxMP1EMWC59fpZezM8zunZrWQcAqH18"
TELEGRAM_CHAT_ID = "6746178673"
ADMIN_PASSWORD = "MoreVistas@2026"

# --- Google Sheets Setup ---
creds_json = os.environ.get('GOOGLE_CREDS')
sheet = None
places_sheet = None
enquiry_sheet = None
settings_sheet = None

def init_sheets():
    global sheet, places_sheet, enquiry_sheet, settings_sheet
    if creds_json:
        try:
            info = json.loads(creds_json)
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(info, scope)
            client = gspread.authorize(creds)
            SHEET_ID = "1wXlMNAUuW2Fr4L05ahxvUNn0yvMedcVosTRJzZf_1ao"
            main_spreadsheet = client.open_by_key(SHEET_ID)
            
            worksheets = main_spreadsheet.worksheets()
            sheet = worksheets[0]
            if len(worksheets) > 1: places_sheet = worksheets[1]
            if len(worksheets) > 2: enquiry_sheet = worksheets[2]
            if len(worksheets) > 3: settings_sheet = worksheets[3]
            print("✅ Sheets Linked Successfully")
        except Exception as e:
            print(f"❌ Sheet Init Error: {e}")

init_sheets()

def get_rows(target_sheet):
    if not target_sheet: return []
    try:
        data = target_sheet.get_all_values()
        if not data or len(data) <= 1: return []
        headers = [h.strip() for h in data[0]]
        final_list = []
        for row in data[1:]:
            if not any(row): continue
            padded_row = row + [''] * (len(headers) - len(row))
            item = dict(zip(headers, padded_row))
            final_list.append(item)
        return final_list
    except: return []

def get_settings():
    # Default values logic improved
    res = {
        'Banner_Status': 'OFF',
        'Offer_Text': 'Welcome to MoreVistas',
        'Offer_Tag': 'OFFER LIVE',
        'Banner_URL': '',
        'Contact': '8830024994',
        'Logo_URL': '',
        'Logo_Height': '40'
    }
    if settings_sheet:
        try:
            data = settings_sheet.get_all_values()
            for r in data:
                if len(r) >= 2:
                    res[r[0].strip()] = r[1].strip()
        except Exception as e:
            print(f"Settings Load Error: {e}")
    return res

@app.route('/')
def index():
    settings_data = get_settings()
    villas_data = get_rows(sheet)
    places_data = get_rows(places_sheet)
    return render_template('index.html', villas=villas_data, settings=settings_data, tourist_places=places_data)

# ... (Add other routes: admin, enquiry, explore, contact etc. exactly as you had them)

if __name__ == '__main__':
    import os
    # Render automatically sets a PORT environment variable
    port = int(os.environ.get("PORT", 10000))
    # '0.0.0.0' is required for Render to find the app
    app.run(host='0.0.0.0', port=port)
