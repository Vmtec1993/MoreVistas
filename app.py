import os
import json
import gspread
from flask import Flask, render_template, request, redirect, url_for, session
from oauth2client.service_account import ServiceAccountCredentials
import requests
from datetime import datetime

app = Flask(__name__)
app.secret_key = "morevistas_admin_secure_key_2026" 

# --- Google Sheets Setup ---
creds_json = os.environ.get('GOOGLE_CREDS')
sheet = None
enquiry_sheet = None
places_sheet = None 

if creds_json:
    try:
        info = json.loads(creds_json)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(info, scope)
        client = gspread.authorize(creds)
        
        SHEET_ID = "1wXlMNAUuW2Fr4L05ahxvUNn0yvMedcVosTRJzZf_1ao"
        main_spreadsheet = client.open_by_key(SHEET_ID)
        sheet = main_spreadsheet.sheet1
        
        try:
            enquiry_sheet = main_spreadsheet.worksheet("Enquiries")
        except:
            enquiry_sheet = sheet
        try:
            places_sheet = main_spreadsheet.worksheet("Places")
        except:
            places_sheet = None
    except Exception as e:
        print(f"Critical Sheet Error: {e}")

# --- Telegram Setup ---
TELEGRAM_TOKEN = "7913354522:AAH1XxMP1EMWC59fpZezM8zunZrWQcAqH18"
TELEGRAM_CHAT_ID = "6746178673"

def send_telegram_alert(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        params = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        requests.get(url, params=params, timeout=10)
    except: pass

# --- Weather ---
def get_lonavala_weather():
    try:
        api_key = "b8ee20104f767837862a93361e68787c" 
        url = f"https://api.openweathermap.org/data/2.5/weather?q=Lonavala&units=metric&appid={api_key}"
        data = requests.get(url, timeout=5).json()
        return {'temp': round(data['main']['temp']), 'desc': data['weather'][0]['description'].title(), 'icon': data['weather'][0]['icon']}
    except: return None

# --- ✅ SAFE DATA FETCH FUNCTION ---
def get_safe_data(target_sheet):
    """दुरुस्त तरीके से डेटा पढ़ने के लिए ताकि Duplicate Headers एरर न आए"""
    try:
        if not target_sheet: return []
        data = target_sheet.get_all_values()
        if not data: return []
        headers = data[0]
        rows = data[1:]
        # हेडर के डुप्लीकेट्स को संभालने के लिए डिक्शनरी बनाना
        clean_data = []
        for row in rows:
            record = {}
            for i, header in enumerate(headers):
                if header: # अगर हेडर खाली नहीं है
                    record[header] = row[i] if i < len(row) else ""
            clean_data.append(record)
        return clean_data
    except Exception as e:
        print(f"Data conversion error: {e}")
        return []

# --- Routes ---

@app.route('/')
def index():
    weather_data = get_lonavala_weather()
    villas = get_safe_data(sheet)
    for v in villas:
        v['Status'] = v.get('Status', 'Available')
    return render_template('index.html', villas=villas, weather=weather_data)

@app.route('/explore-lonavala')
def explore_lonavala():
    places = get_safe_data(places_sheet)
    return render_template('explore.html', places=places)

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        user, pwd = request.form.get('username'), request.form.get('password')
        if user == "admin" and pwd == "MoreVistas@2026":
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        error = "Invalid Username or Password!"
    return render_template('admin_login.html', error=error)

@app.route('/admin-dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'): return redirect(url_for('admin_login'))
    villas = get_safe_data(sheet)
    enquiries = get_safe_data(enquiry_sheet)
    enquiries.reverse()
    return render_template('admin_dashboard.html', enquiries=enquiries, villas=villas)

@app.route('/update-status/<villa_id>/<new_status>')
def update_villa_status(villa_id, new_status):
    if not session.get('admin_logged_in'): return redirect(url_for('admin_login'))
    if sheet:
        try:
            headers = sheet.row_values(1)
            if "Status" in headers:
                col = headers.index("Status") + 1
                all_villas = get_safe_data(sheet)
                row_idx = 2
                for v in all_villas:
                    if str(v.get('Villa_ID')) == str(villa_id):
                        sheet.update_cell(row_idx, col, new_status)
                        break
                    row_idx += 1
        except: pass
    return redirect(url_for('admin_dashboard', t=datetime.now().timestamp()))

@app.route('/villa/<villa_id>')
def villa_details(villa_id):
    villas = get_safe_data(sheet)
    villa = next((v for v in villas if str(v.get('Villa_ID')) == str(villa_id)), None)
    if villa:
        villa['Status'] = villa.get('Status', 'Available')
        villa_images = []
        # Image_URL_1 to 20 को चेक करना
        for i in range(1, 21):
            key = f"Image_URL_{i}"
            img = villa.get(key)
            if not img and i==1: img = villa.get('Image_URL') # Backup for main col
            if img and str(img).strip() != "" and str(img).lower() != 'nan':
                if img not in villa_images: villa_images.append(img)
        return render_template('villa_details.html', villa=villa, villa_images=villa_images)
    return "Villa info not found", 404

@app.route('/enquiry/<villa_id>', methods=['GET', 'POST'])
def enquiry(villa_id):
    villas = get_safe_data(sheet)
    villa = next((v for v in villas if str(v.get('Villa_ID')) == str(villa_id)), None)
    if request.method == 'POST':
        name, phone = request.form.get('name'), request.form.get('phone')
        check_in, check_out = request.form.get('check_in'), request.form.get('check_out')
        guests, msg = request.form.get('guests'), request.form.get('message', 'No message')
        if enquiry_sheet:
            try:
                enquiry_sheet.append_row([datetime.now().strftime("%d-%m-%Y %H:%M"), name, phone, check_in, check_out, guests, msg])
            except: pass
        send_telegram_alert(f"🔔 *New Booking!*\n🏡 *Villa:* {villa.get('Villa_Name')}\n👤 *Name:* {name}\n📞 *Phone:* {phone}")
        return render_template('success.html', name=name)
    return render_template('enquiry.html', villa=villa)

@app.route('/admin-logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000)) 
    app.run(host='0.0.0.0', port=port)
    
