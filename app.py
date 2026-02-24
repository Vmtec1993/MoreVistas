import os
import json
import gspread
from flask import Flask, render_template, request
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
            
            sheet = main_spreadsheet.sheet1
            all_ws = [ws.title for ws in main_spreadsheet.worksheets()]
            if "Places" in all_ws: places_sheet = main_spreadsheet.worksheet("Places")
            if "Enquiries" in all_ws: enquiry_sheet = main_spreadsheet.worksheet("Enquiries")
            if "Settings" in all_ws: settings_sheet = main_spreadsheet.worksheet("Settings")
        except Exception as e:
            print(f"Sheet Init Error: {e}")

init_sheets()

# --- Functions ---
def send_telegram_alert(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.get(url, params={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}, timeout=5)
    except: pass

def get_safe_data(target_sheet):
    """Recursion Error को रोकने के लिए सादा और सीधा तरीका"""
    if target_sheet is None: return []
    try:
        # get_all_values() कभी भी Recursion Error नहीं देता
        rows = target_sheet.get_all_values()
        if not rows or len(rows) < 2: return []
        
        headers = [h.strip() for h in rows[0]]
        clean_list = []
        
        for row in rows[1:]:
            item = {}
            for i, h in enumerate(headers):
                item[h] = row[i] if i < len(row) else ""
            
            # सिर्फ जरूरी क्लीनिंग (बिना बदलाव के)
            p = str(item.get('Price', '')).lower().strip()
            if p in ['', 'nan', '0', 'none']: item['Price'] = None
            
            if not item.get('Image_URL'): item['Image_URL'] = item.get('Image_URL_1', '')
            clean_list.append(item)
        return clean_list
    except:
        return []

# --- Routes ---
@app.route('/')
def index():
    villas = get_safe_data(sheet)
    places = get_safe_data(places_sheet)
    
    # Weather
    weather = None
    try:
        w_url = "https://api.openweathermap.org/data/2.5/weather?q=Lonavala&units=metric&appid=602d32574e40263f16952813df186b59"
        r = requests.get(w_url, timeout=2).json()
        weather = {'temp': round(r['main']['temp']), 'desc': r['weather'][0]['description'].title()}
    except: pass

    # Settings / Offer Text
    runner_text = "Welcome to MoreVistas Lonavala | Call 8830024994"
    if settings_sheet:
        try:
            s_rows = settings_sheet.get_all_values()
            for r in s_rows:
                if len(r) >= 2 and r[0].strip() == 'Offer_Text':
                    runner_text = r[1]
                    break
        except: pass

    return render_template('index.html', villas=villas, weather=weather, runner_text=runner_text, tourist_places=places)

@app.route('/villa/<villa_id>')
def villa_details(villa_id):
    villas = get_safe_data(sheet)
    # ID मैच करने का वर्किंग तरीका
    villa = next((v for v in villas if str(v.get('Villa_ID', '')).strip() == str(villa_id).strip()), None)
    if not villa: return "Villa Not Found", 404
    
    imgs = [villa.get(f'Image_URL_{i}') for i in range(1, 21) if villa.get(f'Image_URL_{i}') and str(villa.get(f'Image_URL_{i}')).lower() != 'nan']
    if not imgs: imgs = [villa.get('Image_URL')]
    
    return render_template('villa_details.html', villa=villa, villa_images=imgs)

@app.route('/enquiry/<villa_id>', methods=['GET', 'POST'])
def enquiry(villa_id):
    villas = get_safe_data(sheet)
    villa = next((v for v in villas if str(v.get('Villa_ID', '')).strip() == str(villa_id).strip()), None)
    
    if request.method == 'POST':
        name, phone = request.form.get('name'), request.form.get('phone')
        dates, guests = request.form.get('stay_dates'), request.form.get('guests')
        v_name = villa.get('Villa_Name', 'Villa') if villa else "Villa"
        
        if enquiry_sheet:
            try:
                enquiry_sheet.append_row([datetime.now().strftime("%d-%m-%Y %H:%M"), name, phone, dates, guests, v_name])
            except: pass
            
        alert = f"🚀 *New Enquiry!*\n🏡 *Villa:* {v_name}\n👤 *Name:* {name}\n📞 *Phone:* {phone}\n📅 *Dates:* {dates}\n👥 *Guests:* {guests}"
        send_telegram_alert(alert)
        return render_template('success.html', name=name)
    
    return render_template('enquiry.html', villa=villa)

@app.route('/explore')
def explore(): return render_template('explore.html', tourist_places=get_safe_data(places_sheet))

@app.route('/about')
def about(): return render_template('about.html')

@app.route('/contact')
def contact(): return render_template('contact.html')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
    
