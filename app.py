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
            places_sheet = main_spreadsheet.worksheet("Places")
        except:
            places_sheet = None

        try:
            enquiry_sheet = main_spreadsheet.worksheet("Enquiries")
        except:
            enquiry_sheet = sheet
            
    except Exception as e:
        print(f"Critical Sheet Error: {e}")

def get_safe_data(target_sheet):
    try:
        if not target_sheet: return []
        data = target_sheet.get_all_values()
        if not data or len(data) < 1: return []
        
        headers = [h.strip() for h in data[0]]
        rows = data[1:]
        clean_data = []
        
        for row in rows:
            record = {}
            for i, h in enumerate(headers):
                val = row[i] if i < len(row) else ""
                record[h] = val
            
            if not record.get('Image_URL') or record.get('Image_URL').strip() == "":
                record['Image_URL'] = record.get('Image_URL_1', '')
                
            clean_data.append(record)
        return clean_data
    except Exception as e:
        print(f"Data Fetch Error: {e}")
        return []

# --- 🌦️ Updated Weather Function ---
def get_weather():
    try:
        # API Key (Please wait 2 hours if new)
        api_key = "b8ee20104f767837862a93361e68787c"
        url = f"https://api.openweathermap.org/data/2.5/weather?q=Lonavala&units=metric&appid={api_key}"
        
        # Timeout helps to not slow down the site if API is slow
        response = requests.get(url, timeout=10) 
        
        if response.status_code == 200:
            d = response.json()
            weather_data = {
                'temp': round(d['main']['temp']), 
                'desc': d['weather'][0]['description'].title(), 
                'icon': d['weather'][0]['icon']
            }
            print(f"✅ Weather Data Fetched: {weather_data['temp']}°C")
            return weather_data
        else:
            print(f"❌ Weather API Error: {response.status_code}")
            return None
    except Exception as e:
        print(f"⚠️ Weather Fetch Error: {e}")
        return None

TELEGRAM_TOKEN = "7913354522:AAH1XxMP1EMWC59fpZezM8zunZrWQcAqH18"
TELEGRAM_CHAT_ID = "6746178673"

def send_telegram_alert(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        params = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        requests.get(url, params=params, timeout=10)
    except:
        pass

# --- 🏠 Routes ---

@app.route('/')
def index():
    weather_info = get_weather() # Store in variable
    villas = get_safe_data(sheet)
    tourist_places = get_safe_data(places_sheet) 
    
    for v in villas:
        v['Status'] = v.get('Status', 'Available')
        v['Guests'] = v.get('Guests', '12')
        v['Offer'] = v.get('Offer', '')
        v['BHK'] = v.get('BHK', '3')
        v['Rules'] = v.get('Rules', 'No specific rules mentioned.')
        
    return render_template('index.html', 
                           villas=villas, 
                           weather=weather_info, # Pass data
                           tourist_places=tourist_places)

@app.route('/explore')
def explore():
    tourist_places = get_safe_data(places_sheet)
    return render_template('explore.html', tourist_places=tourist_places)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/villa/<villa_id>')
def villa_details(villa_id):
    villas = get_safe_data(sheet)
    villa = next((v for v in villas if str(v.get('Villa_ID')) == str(villa_id)), None)
    
    if villa:
        villa['Rules'] = villa.get('Rules', 'Call for house rules.')
        
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
        name, phone, check_in, check_out, guests, msg = request.form.get('name'), request.form.get('phone'), request.form.get('check_in'), request.form.get('check_out'), request.form.get('guests'), request.form.get('message', 'No message')
        if enquiry_sheet:
            try:
                enquiry_sheet.append_row([datetime.now().strftime("%d-%m-%Y %H:%M"), name, phone, check_in, check_out, guests, msg, villa.get('Villa_Name')])
            except: pass
        alert_text = f"🔔 *New Booking Enquiry!*\n\n🏡 *Villa:* {villa.get('Villa_Name')}\n👤 *Name:* {name}\n📞 *Phone:* {phone}\n📅 *Stay:* {check_in} to {check_out}\n👥 *Guests:* {guests}"
        send_telegram_alert(alert_text)
        return render_template('success.html', name=name)
    return render_template('enquiry.html', villa=villa)

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
    villas, enquiries = get_safe_data(sheet), get_safe_data(enquiry_sheet)[::-1]
    return render_template('admin_dashboard.html', villas=villas, enquiries=enquiries)

if __name__ == "__main__":
    # Render handles the PORT
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
    
