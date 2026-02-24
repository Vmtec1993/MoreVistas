import os
import json
import gspread
from flask import Flask, render_template, request, redirect, url_for, session
from oauth2client.service_account import ServiceAccountCredentials
import requests
from datetime import datetime

app = Flask(__name__)
app.secret_key = "morevistas_secure_2026"

# --- Google Sheets Setup ---
creds_json = os.environ.get('GOOGLE_CREDS')
sheet = None
main_spreadsheet = None
places_sheet = None
enquiry_sheet = None

if creds_json:
    try:
        info = json.loads(creds_json)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(info, scope)
        client = gspread.authorize(creds)
        
        SHEET_ID = "1wXlMNAUuW2Fr4L05ahxvUNn0yvMedcVosTRJzZf_1ao"
        main_spreadsheet = client.open_by_key(SHEET_ID)
        sheet = main_spreadsheet.sheet1
        
        # सुरक्षित तरीके से टैब्स चेक करना
        all_ws = [ws.title for ws in main_spreadsheet.worksheets()]
        if "Places" in all_ws: places_sheet = main_spreadsheet.worksheet("Places")
        if "Enquiries" in all_ws: enquiry_sheet = main_spreadsheet.worksheet("Enquiries")
    except Exception as e:
        print(f"Sheet Error: {e}")

def get_safe_data(target_sheet):
    try:
        if not target_sheet: return []
        data = target_sheet.get_all_values()
        if len(data) < 2: return []
        headers = [h.strip() for h in data[0]]
        return [{headers[i]: row[i] if i < len(row) else "" for i, h in enumerate(headers)} for row in data[1:]]
    except: return []

def get_weather():
    try:
        api_key = "602d32574e40263f16952813df186b59"
        url = f"https://api.openweathermap.org/data/2.5/weather?q=Lonavala&units=metric&appid={api_key}"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            d = r.json()
            return {'temp': round(d['main']['temp']), 'desc': d['weather'][0]['description'].title(), 'icon': d['weather'][0]['icon']}
    except: pass
    return None

@app.route('/')
def index():
    weather_info = get_weather()
    villas = get_safe_data(sheet)
    
    # Settings Logic (Safe)
    runner_text = "Welcome to MoreVistas Lonavala | Call 8830024994"
    if main_spreadsheet:
        try:
            all_ws = [ws.title for ws in main_spreadsheet.worksheets()]
            if "Settings" in all_ws:
                s_data = main_spreadsheet.worksheet("Settings").get_all_records()
                runner_text = next((r['Value'] for r in s_data if str(r.get('Key')) == 'Offer_Text'), runner_text)
        except: pass

    for v in villas:
        v['Price'] = v.get('Price', '0')
        v['Villa_Name'] = v.get('Villa_Name', 'Luxury Villa')

    return render_template('index.html', villas=villas, weather=weather_info, runner_text=runner_text, tourist_places=get_safe_data(places_sheet))

# ... बाकी Routes (Explore, Villa, Enquiry) वैसे ही रहेंगे ...

# --- 🚀 PORT FIX FOR RENDER ---
if __name__ == "__main__":
    # Render की 'No open HTTP ports' एरर को ये लाइन ठीक करेगी
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
    
