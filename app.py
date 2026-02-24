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

def get_safe_data(target_sheet):
    try:
        if not target_sheet: return []
        data = target_sheet.get_all_values()
        if len(data) < 1: return []
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
        r = requests.get(url, timeout=2)
        if r.status_code == 200:
            d = r.json()
            return {'temp': round(d['main']['temp']), 'desc': d['weather'][0]['description'].title(), 'icon': d['weather'][0]['icon']}
    except: pass
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
                s_data = settings_sheet.get_all_records()
                for row in s_data:
                    if str(row.get('Key')).strip() == 'Offer_Text':
                        runner_text = row.get('Value', runner_text)
                        break
            except: pass

        for v in villas:
            v['Villa_Name'] = v.get('Villa_Name', 'Luxury Villa')
            v['BHK'] = v.get('BHK', '3')
            v['Guests'] = v.get('Guests', '12')
            v['Offer'] = v.get('Offer', '')

        return render_template('index.html', villas=villas, weather=weather_info, runner_text=runner_text, tourist_places=tourist_places)
    except Exception as e:
        return f"Error: {e}", 500

@app.route('/explore')
def explore():
    return render_template('explore.html', tourist_places=get_safe_data(places_sheet))

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
        villa_images = [villa.get(f'Image_URL_{i}') for i in range(1, 21) if villa.get(f'Image_URL_{i}') and str(villa.get(f'Image_URL_{i}')).lower() != 'nan']
        if not villa_images: villa_images = [villa.get('Image_URL')]
        return render_template('villa_details.html', villa=villa, villa_images=villa_images)
    return "Villa Not Found", 404

@app.route('/enquiry/<villa_id>', methods=['GET', 'POST'])
def enquiry(villa_id):
    villas = get_safe_data(sheet)
    villa = next((v for v in villas if str(v.get('Villa_ID')) == str(villa_id)), None)
    if request.method == 'POST':
        name = request.form.get('name', 'Guest')
        phone = request.form.get('phone', '')
        dates = request.form.get('stay_dates', 'Not selected')
        guests = request.form.get('guests', '1')
        
        if enquiry_sheet:
            try:
                enquiry_sheet.append_row([datetime.now().strftime("%d-%m-%Y %H:%M"), name, phone, dates, guests, villa.get('Villa_Name', 'Unknown')])
            except: pass
        return render_template('success.html', name=name)
    return render_template('enquiry.html', villa=villa)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
