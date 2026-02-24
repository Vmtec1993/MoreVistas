import os
import json
import gspread
from flask import Flask, render_template, request, redirect, url_for, session
from oauth2client.service_account import ServiceAccountCredentials
import requests
from datetime import datetime

app = Flask(__name__)
app.secret_key = "morevistas_secure_2026" # Admin session ke liye zaroori hai

# --- Google Sheets Setup ---
creds_json = os.environ.get('GOOGLE_CREDS')
sheet = None
enquiry_sheet = None

if creds_json:
    try:
        info = json.loads(creds_json)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(info, scope)
        client = gspread.authorize(creds)
        
        SHEET_ID = "1wXlMNAUuW2Fr4L05ahxvUNn0yvMedcVosTRJzZf_1ao"
        main_spreadsheet = client.open_by_key(SHEET_ID)
        sheet = main_spreadsheet.sheet1  # Villas Data
        
        try:
            enquiry_sheet = main_spreadsheet.worksheet("Enquiries")
        except:
            enquiry_sheet = sheet
    except Exception as e:
        print(f"Critical Sheet Error: {e}")

# --- ✅ SAFE DATA LOADER (Images Load Karne ke liye) ---
def get_safe_data(target_sheet):
    """Sheet se data nikalne ka sabse safe tarika taki images gayab na hon"""
    try:
        if not target_sheet: return []
        data = target_sheet.get_all_values()
        if not data: return []
        headers = [h.strip() for h in data[0]] # Space saaf karne ke liye
        rows = data[1:]
        clean_data = []
        for row in rows:
            record = {}
            for i, h in enumerate(headers):
                record[h] = row[i] if i < len(row) else ""
            
            # Agar Image_URL khali hai to Image_URL_1 check kare
            if not record.get('Image_URL') or record.get('Image_URL') == '':
                record['Image_URL'] = record.get('Image_URL_1', '')
                
            clean_data.append(record)
        return clean_data
    except: return []

# --- Weather Alert ---
def get_weather():
    try:
        url = "https://api.openweathermap.org/data/2.5/weather?q=Lonavala&units=metric&appid=b8ee20104f767837862a93361e68787c"
        d = requests.get(url, timeout=5).json()
        return {'temp': round(d['main']['temp']), 'desc': d['weather'][0]['description'].title(), 'icon': d['weather'][0]['icon']}
    except: return None

# --- Telegram Setup ---
TELEGRAM_TOKEN = "7913354522:AAH1XxMP1EMWC59fpZezM8zunZrWQcAqH18"
TELEGRAM_CHAT_ID = "6746178673"

def send_telegram_alert(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        params = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        requests.get(url, params=params, timeout=10)
    except: pass

# --- Routes ---

@app.route('/')
def index():
    weather = get_weather()
    villas = get_safe_data(sheet)
    for v in villas:
        v['Status'] = v.get('Status', 'Available')
        v['Guests'] = v.get('Guests', '12')
        v['Offer'] = v.get('Offer', '')
    return render_template('index.html', villas=villas, weather=weather)

@app.route('/villa/<villa_id>')
def villa_details(villa_id):
    villas = get_safe_data(sheet)
    villa = next((v for v in villas if str(v.get('Villa_ID')) == str(villa_id)), None)
    if villa:
        # Gallery images logic (Image_URL_1 to Image_URL_20)
        villa_images = []
        for i in range(1, 21):
            key = f"Image_URL_{i}"
            img = villa.get(key)
            if not img and i == 1: img = villa.get('Image_URL')
            if img and str(img).strip() != "" and str(img).lower() != 'nan':
                if img not in villa_images: villa_images.append(img)
        
        return render_template('villa_details.html', villa=villa, villa_images=villa_images)
    return "Villa info not found", 404

@app.route('/enquiry/<villa_id>', methods=['GET', 'POST'])
def enquiry(villa_id):
    villas = get_safe_data(sheet)
    villa = next((v for v in villas if str(v.get('Villa_ID')) == str(villa_id)), None)
    
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        check_in, check_out = request.form.get('check_in'), request.form.get('check_out')
        guests, msg = request.form.get('guests'), request.form.get('message', 'No message')
        
        if enquiry_sheet:
            try:
                enquiry_sheet.append_row([datetime.now().strftime("%d-%m-%Y %H:%M"), name, phone, check_in, check_out, guests, msg])
            except: pass

        alert_text = f"🔔 *New Booking!*\n🏡 *Villa:* {villa.get('Villa_Name')}\n👤 *Name:* {name}\n📞 *Phone:* {phone}"
        send_telegram_alert(alert_text)
        return render_template('success.html', name=name)

    return render_template('enquiry.html', villa=villa)

# --- Admin Routes ---
@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('username') == "admin" and request.form.get('password') == "MoreVistas@2026":
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
    return render_template('admin_login.html')

@app.route('/admin-dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'): return redirect(url_for('admin_login'))
    villas = get_safe_data(sheet)
    enquiries = get_safe_data(enquiry_sheet)[::-1] # Newest first
    return render_template('admin_dashboard.html', villas=villas, enquiries=enquiries)

if __name__ == "__main__":
    # Render port configuration
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
    
