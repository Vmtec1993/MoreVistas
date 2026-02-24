import sys
# रिकर्सन लिमिट को बढ़ाना केवल एक सुरक्षा कवच है, असली फिक्स नीचे लॉजिक में है
sys.setrecursionlimit(2000)

import os
import json
import gspread
from flask import Flask, render_template, request, redirect, url_for, session
from oauth2client.service_account import ServiceAccountCredentials
import requests
from datetime import datetime

app = Flask(__name__)
app.secret_key = "morevistas_secure_2026"

# --- CONFIG ---
TELEGRAM_TOKEN = "7913354522:AAH1XxMP1EMWC59fpZezM8zunZrWQcAqH18"
TELEGRAM_CHAT_ID = "6746178673"

# --- Google Sheets Setup ---
creds_json = os.environ.get('GOOGLE_CREDS')
sheet = None
main_spreadsheet = None
places_sheet = None
enquiry_sheet = None
settings_sheet = None

def init_sheets():
    global sheet, main_spreadsheet, places_sheet, enquiry_sheet, settings_sheet
    if creds_json:
        try:
            info = json.loads(creds_json)
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(info, scope)
            client = gspread.authorize(creds)
            
            SHEET_ID = "1wXlMNAUuW2Fr4L05ahxvUNn0yvMedcVosTRJzZf_1ao"
            main_spreadsheet = client.open_by_key(SHEET_ID)
            sheet = main_spreadsheet.sheet1
            
            all_ws = [ws.title for ws in main_spreadsheet.worksheets()]
            if "Places" in all_ws: places_sheet = main_spreadsheet.worksheet("Places")
            if "Enquiries" in all_ws: enquiry_sheet = main_spreadsheet.worksheet("Enquiries")
            if "Settings" in all_ws: settings_sheet = main_spreadsheet.worksheet("Settings")
        except Exception as e:
            print(f"Sheet Init Error: {e}")

init_sheets()

# --- 🛠️ Functions ---

def send_telegram_alert(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        params = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        requests.get(url, params=params, timeout=5)
    except Exception as e:
        print(f"Telegram Error: {e}")

def get_safe_data(target_sheet):
    """डेटा को सुरक्षित तरीके से निकालने के लिए फिक्स्ड फंक्शन"""
    try:
        if target_sheet is None: 
            return []
        
        data = target_sheet.get_all_values()
        if not data or len(data) < 1: 
            return []
            
        headers = [h.strip() for h in data[0]]
        clean_data = []
        
        for row in data[1:]:
            # डिक्शनरी कॉम्प्रिहेंशन का उपयोग करें ताकि रिकर्सन का खतरा न रहे
            record = {}
            for i, h in enumerate(headers):
                val = row[i] if i < len(row) else ""
                record[h] = val
            
            # इमेज यूआरएल फिक्स
            if not record.get('Image_URL'):
                record['Image_URL'] = record.get('Image_URL_1', '')
            
            # प्राइस क्लीनिंग लॉजिक (बिना लूप में फंसे)
            p_raw = str(record.get('Price', '')).lower().strip()
            if p_raw in ['', 'nan', '0', 'none', 'null']:
                record['Price'] = None
                
            op_raw = str(record.get('Original_Price', '')).lower().strip()
            if op_raw in ['', 'nan', '0', 'none', 'null']:
                record['Original_Price'] = None
                
            clean_data.append(record)
        return clean_data
    except Exception as e:
        print(f"Data Fetch Error: {e}")
        return []

def get_weather():
    try:
        api_key = "602d32574e40263f16952813df186b59"
        url = f"https://api.openweathermap.org/data/2.5/weather?q=Lonavala&units=metric&appid={api_key}"
        r = requests.get(url, timeout=2)
        if r.status_code == 200:
            d = r.json()
            return {'temp': round(d['main']['temp']), 'desc': d['weather'][0]['description'].title(), 'icon': d['weather'][0]['icon']}
    except:
        pass
    return None

# --- 🏠 Routes ---

@app.route('/')
def index():
    try:
        weather_info = get_weather()
        villas = get_safe_data(sheet)
        tourist_places = get_safe_data(places_sheet)
        
        runner_text = "Welcome to MoreVistas Lonavala | Call 8830024994"
        if settings_sheet:
            try:
                # get_all_records() के बजाय सुरक्षित तरीका
                s_data = settings_sheet.get_all_values()
                if len(s_data) > 1:
                    headers = s_data[0]
                    for row in s_data[1:]:
                        if len(row) >= 2 and str(row[0]).strip() == 'Offer_Text':
                            runner_text = row[1]
                            break
            except:
                pass

        return render_template('index.html', villas=villas, weather=weather_info, runner_text=runner_text, tourist_places=tourist_places)
    except Exception as e:
        print(f"Index Route Error: {e}")
        return f"Something went wrong: {e}", 500

@app.route('/villa/<villa_id>')
def villa_details(villa_id):
    try:
        villas = get_safe_data(sheet)
        # स्ट्रिंग तुलना सुनिश्चित करें
        villa = next((v for v in villas if str(v.get('Villa_ID', '')).strip() == str(villa_id).strip()), None)
        
        if villa:
            villa_images = []
            for i in range(1, 21):
                img = villa.get(f'Image_URL_{i}')
                if img and str(img).lower() != 'nan' and str(img).strip() != "":
                    villa_images.append(img)
            
            if not villa_images:
                villa_images = [villa.get('Image_URL')]
                
            return render_template('villa_details.html', villa=villa, villa_images=villa_images)
        return "Villa Not Found", 404
    except Exception as e:
        print(f"Villa Detail Error: {e}")
        return f"Error loading villa: {e}", 500

@app.route('/enquiry/<villa_id>', methods=['GET', 'POST'])
def enquiry(villa_id):
    villas = get_safe_data(sheet)
    villa = next((v for v in villas if str(v.get('Villa_ID', '')).strip() == str(villa_id).strip()), None)
    
    if request.method == 'POST':
        name = request.form.get('name', 'Guest')
        phone = request.form.get('phone', '')
        dates = request.form.get('stay_dates', 'Not selected')
        guests = request.form.get('guests', '1')
        villa_name = villa.get('Villa_Name', 'Unknown Villa') if villa else "Villa"
        
        if enquiry_sheet:
            try:
                enquiry_sheet.append_row([datetime.now().strftime("%d-%m-%Y %H:%M"), name, phone, dates, guests, villa_name])
            except:
                pass
        
        alert_msg = (
            f"🚀 *New Villa Enquiry!*\n\n"
            f"🏡 *Villa:* {villa_name}\n"
            f"👤 *Name:* {name}\n"
            f"📞 *Phone:* {phone}\n"
            f"📅 *Dates:* {dates}\n"
            f"👥 *Guests:* {guests}\n"
            f"⏰ *Received:* {datetime.now().strftime('%H:%M %p')}"
        )
        send_telegram_alert(alert_msg)
        return render_template('success.html', name=name)
    
    return render_template('enquiry.html', villa=villa)

@app.route('/explore')
def explore(): 
    return render_template('explore.html', tourist_places=get_safe_data(places_sheet))

@app.route('/about')
def about(): return render_template('about.html')

@app.route('/contact')
def contact(): return render_template('contact.html')

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
            
