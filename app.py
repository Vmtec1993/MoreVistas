import os
import json
import gspread
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

app = Flask(__name__)
app.secret_key = "morevistas_secure_2026"

# --- CONFIG ---
TELEGRAM_TOKEN = "7913354522:AAH1XxMP1EMWC59fpZezM8zunZrWQcAqH18"
TELEGRAM_CHAT_ID = "6746178673"
ADMIN_PASSWORD = "MoreVistas@2026"

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
            worksheets = main_spreadsheet.worksheets()
            sheet = worksheets[0]
            if len(worksheets) > 1: places_sheet = worksheets[1]
            if len(worksheets) > 2: enquiry_sheet = worksheets[2]
            if len(worksheets) > 3: settings_sheet = worksheets[3]
            print("✅ All Sheets Linked Successfully")
        except Exception as e:
            print(f"❌ Sheet Init Error: {e}")

init_sheets()

# --- HELPER FUNCTIONS ---
def get_rows(target_sheet):
    if not target_sheet: return []
    try:
        data = target_sheet.get_all_values()
        if not data or len(data) <= 1: return []
        headers = [h.strip() for h in data[0]]
        final_list = []
        for row in data[1:]:
            if not any(row): continue
            padded_row = row + [''] * (len(headers) - len(row))
            final_list.append(dict(zip(headers, padded_row)))
        return final_list
    except: return []

def get_settings():
    res = {'Banner_Status': 'OFF', 'Offer_Text': '', 'Offer_Tag': 'OFFER', 'Banner_URL': '', 'Contact': '8830024994', 'Logo_URL': '', 'Logo_Height': '50'}
    if settings_sheet:
        try:
            data = settings_sheet.get_all_values()
            for r in data:
                if len(r) >= 2:
                    key = r[0].strip()
                    val = r[1].strip()
                    if 'URL' in key and val and not val.startswith('http'): val = 'https://' + val
                    res[key] = val
        except: pass
    return res

# --- ROUTES ---
@app.route('/')
def index():
    return render_template('index.html', villas=get_rows(sheet), settings=get_settings(), tourist_places=get_rows(places_sheet))

@app.route('/villa/<villa_id>')
def villa_details(villa_id):
    villas = get_rows(sheet)
    villa = next((v for v in villas if str(v.get('Villa_ID', '')).strip() == str(villa_id).strip()), None)
    if not villa: return "Villa Not Found", 404
    
    # Image logic for gallery
    imgs = [villa.get(f'Image_URL_{i}') for i in range(1, 21) if villa.get(f'Image_URL_{i}')]
    if not any(imgs): imgs = [villa.get('Image_URL')]
    
    # Rules logic - Clean list
    rules = [villa.get(f'Rule_{i}') for i in range(1, 11) if villa.get(f'Rule_{i}')]
    
    return render_template('villa_details.html', villa=villa, villa_images=imgs, villa_rules=rules, settings=get_settings())

@app.route('/enquiry/<villa_id>', methods=['GET', 'POST'])
def enquiry(villa_id):
    v_data = get_rows(sheet)
    villa = next((v for v in v_data if str(v.get('Villa_ID', '')).strip() == str(villa_id).strip()), None)
    if not villa: return "Villa Not Found", 404

    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        dates = request.form.get('stay_dates')
        guests = request.form.get('guests')
        
        if enquiry_sheet:
            enquiry_sheet.append_row([datetime.now().strftime("%d-%m-%Y"), name, phone, dates, guests, villa.get('Villa_Name')])
        
        # Telegram Alert
        msg = f"🆕 NEW ENQUIRY!\n\nVilla: {villa.get('Villa_Name')}\nName: {name}\nPhone: {phone}\nDates: {dates}\nGuests: {guests}"
        requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text={msg}")
        
        return render_template('success.html', name=name, settings=get_settings())
    
    return render_template('enquiry.html', villa=villa, settings=get_settings())

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'): return redirect(url_for('admin_login'))
    return render_template('admin_dashboard.html', enquiries=get_rows(enquiry_sheet))

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('index'))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
    
