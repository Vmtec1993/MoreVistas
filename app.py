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

# Initialization
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
    res = {
        'Banner_Status': 'OFF',
        'Offer_Text': 'Luxury Living',
        'Offer_Tag': 'SPECIAL',
        'Banner_URL': '',
        'Contact': '8830024994',
        'Logo_URL': '',
        'Logo_Height': '50'
    }
    if settings_sheet:
        try:
            data = settings_sheet.get_all_values()
            for r in data:
                if len(r) >= 2:
                    key = r[0].strip()
                    val = r[1].strip()
                    # Auto-fix: Adding https if missing from sheet
                    if ('URL' in key) and val and not val.startswith('http'):
                        val = 'https://' + val
                    res[key] = val
        except: pass
    return res

@app.route('/')
def index():
    settings_data = get_settings()
    return render_template('index.html', 
                           villas=get_rows(sheet), 
                           settings=settings_data, 
                           tourist_places=get_rows(places_sheet))

@app.route('/villa/<villa_id>')
def villa_details(villa_id):
    villas = get_rows(sheet)
    villa = next((v for v in villas if str(v.get('Villa_ID', '')).strip() == str(villa_id).strip()), None)
    if not villa: return "Villa Not Found", 404
    imgs = [villa.get(f'Image_URL_{i}') for i in range(1, 21) if villa.get(f'Image_URL_{i}')]
    if not imgs or not any(imgs): imgs = [villa.get('Image_URL')]
    return render_template('villa_details.html', villa=villa, villa_images=imgs, settings=get_settings())

# Main Entry
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
    
