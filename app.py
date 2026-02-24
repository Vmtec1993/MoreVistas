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
settings_sheet = None

if creds_json:
    try:
        info = json.loads(creds_json)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(info, scope)
        client = gspread.authorize(creds)
        
        SHEET_ID = "1wXlMNAUuW2Fr4L05ahxvUNn0yvMedcVosTRJzZf_1ao"
        main_spreadsheet = client.open_by_key(SHEET_ID)
        sheet = main_spreadsheet.sheet1
        
        # टैब्स को एक ही बार चेक करना (Fast Loading)
        all_ws = [ws.title for ws in main_spreadsheet.worksheets()]
        if "Places" in all_ws: places_sheet = main_spreadsheet.worksheet("Places")
        if "Enquiries" in all_ws: enquiry_sheet = main_spreadsheet.worksheet("Enquiries")
        if "Settings" in all_ws: settings_sheet = main_spreadsheet.worksheet("Settings")
        
    except Exception as e:
        print(f"Sheet Setup Error: {e}")

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
        # Timeout 2 seconds ताकि पोर्ट जल्दी ओपन हो सके
        api_key = "602d32574e40263f16952813df186b59"
        url = f"https://api.openweathermap.org/data/2.5/weather?q=Lonavala&units=metric&appid={api_key}"
        r = requests.get(url, timeout=2)
        if r.status_code == 200:
            d = r.json()
            return {'temp': round(d['main']['temp']), 'desc': d['weather'][0]['description'].title(), 'icon': d['weather'][0]['icon']}
    except: pass
    return None

# --- 🏠 Routes ---

@app.route('/')
def index():
    weather_info = get_weather()
    villas = get_safe_data(sheet)
    
    # Settings Logic
    runner_text = "Welcome to MoreVistas Lonavala | Call 8830024994"
    if settings_sheet:
        try:
            s_data = settings_sheet.get_all_records()
            runner_text = next((r['Value'] for r in s_data if str(r.get('Key')) == 'Offer_Text'), runner_text)
        except: pass

    for v in villas:
        v['Price'] = v.get('Price', '0')
        v['Villa_Name'] = v.get('Villa_Name', 'Luxury Villa')

    return render_template('index.html', 
                           villas=villas, 
                           weather=weather_info, 
                           runner_text=runner_text, 
                           tourist_places=get_safe_data(places_sheet))

@app.route('/explore')
def explore():
    return render_template('explore.html', tourist_places=get_safe_data(places_sheet))

@app.route('/villa/<villa_id>')
def villa_details(villa_id):
    villas = get_safe_data(sheet)
    villa = next((v for v in villas if str(v.get('Villa_ID')) == str(villa_id)), None)
    if villa:
        # Images logic
        villa_images = [villa.get(f'Image_URL_{i}') for i in range(1, 21) if villa.get(f'Image_URL_{i}') and str(villa.get(f'Image_URL_{i}')).lower() != 'nan']
        if not villa_images: villa_images = [villa.get('Image_URL')]
        return render_template('villa_details.html', villa=villa, villa_images=villa_images)
    return "Villa Not Found", 404

@app.route('/enquiry/<villa_id>', methods=['GET', 'POST'])
def enquiry(villa_id):
    villas = get_safe_data(sheet)
    villa = next((v for v in villas if str(v.get('Villa_ID')) == str(villa_id)), None)
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        # Telegram logic would go here if needed
        if enquiry_sheet:
            try:
                enquiry_sheet.append_row([datetime.now().strftime("%d-%m-%Y %H:%M"), name, phone, villa.get('Villa_Name')])
            except: pass
        return render_template('success.html', name=name)
    return render_template('enquiry.html', villa=villa)

# --- 🚀 PORT FIX FOR RENDER ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
    
