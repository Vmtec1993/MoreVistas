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

def get_rows(target_sheet):
    if not target_sheet: return []
    try:
        data = target_sheet.get_all_values()
        if not data or len(data) < 1: return []
        headers = [h.strip() for h in data[0]]
        final_list = []
        for row in data[1:]:
            item = dict(zip(headers, row))
            # Price Clean-up: Empty strings या 0 को None करना ताकि HTML न फटे
            p = str(item.get('Price', '')).lower().strip()
            if p in ['', 'nan', '0', 'none']: 
                item['Price'] = None
            final_list.append(item)
        return final_list
    except:
        return []

# --- Routes ---

@app.route('/')
def index():
    villas = get_rows(sheet)
    places = get_rows(places_sheet)
    weather = None
    try:
        w_url = "https://api.openweathermap.org/data/2.5/weather?q=Lonavala&units=metric&appid=602d32574e40263f16952813df186b59"
        r = requests.get(w_url, timeout=3).json()
        weather = {'temp': round(r['main']['temp']), 'desc': r['weather'][0]['description'].title()}
    except:
        pass

    runner_text = "Welcome to MoreVistas Lonavala | Call 8830024994"
    if settings_sheet:
        try:
            s_data = settings_sheet.get_all_values()
            for r in s_data:
                if len(r) >= 2 and r[0] == 'Offer_Text':
                    runner_text = r[1]
                    break
        except:
            pass

    return render_template('index.html', villas=villas, weather=weather, runner_text=runner_text, tourist_places=places)

@app.route('/villa/<villa_id>')
def villa_details(villa_id):
    villas = get_rows(sheet)
    villa = next((v for v in villas if str(v.get('Villa_ID', '')).strip() == str(villa_id).strip()), None)
    if not villa: return "Villa Not Found", 404
    
    # इमेज हैंडलिंग (Image_URL_1 to 20)
    imgs = [villa.get(f'Image_URL_{i}') for i in range(1, 21) if villa.get(f'Image_URL_{i}') and str(villa.get(f'Image_URL_{i}')).lower() != 'nan']
    if not imgs: imgs = [villa.get('Image_URL')]
    
    return render_template('villa_details.html', villa=villa, villa_images=imgs)

@app.route('/enquiry/<villa_id>', methods=['GET', 'POST'])
def enquiry(villa_id):
    villas = get_rows(sheet)
    villa = next((v for v in villas if str(v.get('Villa_ID', '')).strip() == str(villa_id).strip()), None)
    
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        dates = request.form.get('stay_dates')
        guests = request.form.get('guests')
        v_name = villa.get('Villa_Name', 'Villa') if villa else "Villa"
        
        if enquiry_sheet:
            try:
                enquiry_sheet.append_row([datetime.now().strftime("%d-%m-%Y %H:%M"), name, phone, dates, guests, v_name])
            except:
                pass
            
        alert = f"🚀 *New Enquiry!*\n🏡 *Villa:* {v_name}\n👤 *Name:* {name}\n📞 *Phone:* {phone}\n📅 *Dates:* {dates}\n👥 *Guests:* {guests}"
        requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", params={"chat_id": TELEGRAM_CHAT_ID, "text": alert, "parse_mode": "Markdown"})
        return render_template('success.html', name=name)
    
    return render_template('enquiry.html', villa=villa)

@app.route('/explore')
def explore():
    return render_template('explore.html', tourist_places=get_rows(places_sheet))

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

if __name__ == "__main__":
    # Render के लिए 0.0.0.0 और पोर्ट सेट करना अनिवार्य है
    port = int(os.environ.get("PORT", 5000)) 
    app.run(host='0.0.0.0', port=port)

        
