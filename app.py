import os, json, gspread, requests
from flask import Flask, render_template, request, session, redirect, url_for
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

app = Flask(__name__)
app.secret_key = "morevistas_2026_secure"

# --- CONFIG ---
ADMIN_PASSWORD = "MoreVistas@2026"
TELEGRAM_TOKEN = "7913354522:AAH1XxMP1EMWC59fpZezM8zunZrWQcAqH18"
TELEGRAM_CHAT_ID = "6746178673"

# --- SHEETS SETUP ---
creds_json = os.environ.get('GOOGLE_CREDS')
client = None
SHEET_ID = "1wXlMNAUuW2Fr4L05ahxvUNn0yvMedcVosTRJzZf_1ao"

def get_sheet_data(tab_name):
    try:
        global client
        if not client:
            info = json.loads(creds_json)
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(info, scope)
            client = gspread.authorize(creds)
        
        spreadsheet = client.open_by_key(SHEET_ID)
        # Tab name se data uthayega taaki koi galti na ho
        worksheet = spreadsheet.worksheet(tab_name)
        data = worksheet.get_all_values()
        if not data: return []
        headers = [h.strip() for h in data[0]]
        return [dict(zip(headers, row)) for row in data[1:] if any(row)]
    except: return []

def get_settings():
    res = {'Banner_Status': 'OFF', 'Contact': '8830024994', 'Logo_Height': '50'}
    try:
        data = get_sheet_data("Settings") # Tab ka naam "Settings" hona chahiye
        for item in data:
            key = list(item.values())[0].strip()
            val = list(item.values())[1].strip()
            if 'URL' in key and val and not val.startswith('http'): val = 'https://' + val
            res[key] = val
    except: pass
    return res

# --- ROUTES ---

@app.route('/')
def index():
    villas = get_sheet_data("Villas") # Tab ka naam "Villas"
    places = get_sheet_data("Places") # Tab ka naam "Places"
    return render_template('index.html', villas=villas, settings=get_settings(), tourist_places=places)

@app.route('/villa/<villa_id>')
def villa_details(villa_id):
    villas = get_sheet_data("Villas")
    villa = next((v for v in villas if str(v.get('Villa_ID')).strip() == str(villa_id).strip()), None)
    if not villa: return "Villa Not Found", 404
    
    # Rules list fix
    rules = [v for k, v in villa.items() if 'rule' in k.lower() and v.strip()]
    villa['Rules_List'] = rules
    
    # Image gallery fix
    imgs = [villa.get(f'Image_URL_{i}') for i in range(1, 21) if villa.get(f'Image_URL_{i}')]
    if not any(imgs): imgs = [villa.get('Image_URL')]
    
    return render_template('villa_details.html', villa=villa, villa_images=imgs, settings=get_settings())

@app.route('/enquiry/<villa_id>', methods=['GET', 'POST'])
def enquiry(villa_id):
    if request.method == 'POST':
        # Enquiry logic yahan...
        return render_template('success.html', name=request.form.get('name'), settings=get_settings())
    villas = get_sheet_data("Villas")
    villa = next((v for v in villas if str(v.get('Villa_ID')).strip() == str(villa_id).strip()), None)
    return render_template('enquiry.html', villa=villa, settings=get_settings())

# PAGES FIX
@app.route('/privacy-policy')
def privacy_policy(): return render_template('privacy_policy.html', settings=get_settings())

@app.route('/terms-conditions')
def terms_conditions(): return render_template('terms_conditions.html', settings=get_settings())

@app.route('/admin')
def admin_login(): return render_template('admin_login.html')

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
    
