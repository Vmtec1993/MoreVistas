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
enquiry_sheet = None
places_sheet = None 
main_spreadsheet = None 

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
        all_sheets = [s.title for s in main_spreadsheet.worksheets()]
        
        if "Places" in all_sheets:
            places_sheet = main_spreadsheet.worksheet("Places")
        if "Enquiries" in all_sheets:
            enquiry_sheet = main_spreadsheet.worksheet("Enquiries")
            
    except Exception as e:
        print(f"Critical Sheet Error: {e}")

def get_safe_data(target_sheet):
    try:
        if not target_sheet: return []
        data = target_sheet.get_all_values()
        if not data or len(data) < 1: return []
        headers = [h.strip() for h in data[0]]
        clean_data = []
        for row in data[1:]:
            record = {headers[i]: row[i] if i < len(row) else "" for i, h in enumerate(headers)}
            if not record.get('Image_URL'): record['Image_URL'] = record.get('Image_URL_1', '')
            clean_data.append(record)
        return clean_data
    except: return []

def get_weather():
    try:
        api_key = "602d32574e40263f16952813df186b59"
        url = f"https://api.openweathermap.org/data/2.5/weather?q=Lonavala&units=metric&appid={api_key}"
        response = requests.get(url, timeout=10) 
        if response.status_code == 200:
            d = response.json()
            return {'temp': round(d['main']['temp']), 'desc': d['weather'][0]['description'].title(), 'icon': d['weather'][0]['icon']}
        return None
    except: return None

TELEGRAM_TOKEN = "7913354522:AAH1XxMP1EMWC59fpZezM8zunZrWQcAqH18"
TELEGRAM_CHAT_ID = "6746178673"

def send_telegram_alert(message):
    try:
        requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", params={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}, timeout=10)
    except: pass

# --- 🏠 Routes ---

@app.route('/')
def index():
    weather_info = get_weather()
    villas = get_safe_data(sheet)
    tourist_places = get_safe_data(places_sheet) 
    
    # --- 🛠️ Robust Settings Logic ---
    runner_text = "Welcome to MoreVistas Lonavala | Luxury Villas"
    try:
        # चेक करें कि Settings टैब मौजूद है या नहीं
        all_ws = [ws.title for ws in main_spreadsheet.worksheets()]
        if "Settings" in all_ws:
            settings_data = main_spreadsheet.worksheet("Settings").get_all_records()
            for row in settings_data:
                if str(row.get('Key')).strip() == 'Offer_Text':
                    runner_text = row.get('Value', runner_text)
                    break
    except Exception as e:
        print(f"Settings Fetch Error: {e}")

    for v in villas:
        v['Status'] = v.get('Status', 'Available')
        v['Guests'] = v.get('Guests', '12')
        v['Offer'] = v.get('Offer', '')
        v['BHK'] = v.get('BHK', '3')
        
    return render_template('index.html', villas=villas, weather=weather_info, tourist_places=tourist_places, runner_text=runner_text)

# ... (बाकी के routes explore, contact, villa_details, enquiry वैसे ही रहेंगे)

@app.route('/explore')
def explore():
    return render_template('explore.html', tourist_places=get_safe_data(places_sheet))

@app.route('/about')
def about(): return render_template('about.html')

@app.route('/contact')
def contact(): return render_template('contact.html')

@app.route('/villa/<villa_id>')
def villa_details(villa_id):
    villas = get_safe_data(sheet)
    villa = next((v for v in villas if str(v.get('Villa_ID')) == str(villa_id)), None)
    if villa:
        villa_images = [villa.get(f'Image_URL_{i}') for i in range(1, 21) if villa.get(f'Image_URL_{i}') and str(villa.get(f'Image_URL_{i}')).lower() != 'nan']
        if not villa_images: villa_images = [villa.get('Image_URL')]
        return render_template('villa_details.html', villa=villa, villa_images=villa_images)
    return "Not Found", 404

@app.route('/enquiry/<villa_id>', methods=['GET', 'POST'])
def enquiry(villa_id):
    villas = get_safe_data(sheet)
    villa = next((v for v in villas if str(v.get('Villa_ID')) == str(villa_id)), None)
    if request.method == 'POST':
        d = request.form
        if enquiry_sheet:
            try: enquiry_sheet.append_row([datetime.now().strftime("%d-%m-%Y %H:%M"), d['name'], d['phone'], d['check_in'], d['check_out'], d['guests'], d.get('message', ''), villa.get('Villa_Name')])
            except: pass
        send_telegram_alert(f"🔔 *Enquiry!*\n🏡 {villa.get('Villa_Name')}\n👤 {d['name']}\n📞 {d['phone']}")
        return render_template('success.html', name=d['name'])
    return render_template('enquiry.html', villa=villa)

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST' and request.form.get('password') == "MoreVistas@2026":
        session['admin_logged_in'] = True
        return redirect(url_for('admin_dashboard'))
    return render_template('admin_login.html')

@app.route('/admin-dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'): return redirect(url_for('admin_login'))
    return render_template('admin_dashboard.html', villas=get_safe_data(sheet), enquiries=get_safe_data(enquiry_sheet)[::-1])

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
    
