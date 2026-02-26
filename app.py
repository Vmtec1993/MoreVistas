import os, json, gspread, requests
from flask import Flask, render_template, request, session, redirect, url_for
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

app = Flask(__name__)
app.secret_key = "morevistas_2026_final_vault"

# --- CONFIG ---
ADMIN_PASSWORD = "MoreVistas@2026"
TELEGRAM_TOKEN = "7913354522:AAH1XxMP1EMWC59fpZezM8zunZrWQcAqH18"
TELEGRAM_CHAT_ID = "6746178673"
SHEET_ID = "1wXlMNAUuW2Fr4L05ahxvUNn0yvMedcVosTRJzZf_1ao"

# --- CORE DATA ENGINE ---
def get_master_data(tab_name):
    try:
        creds_json = os.environ.get('GOOGLE_CREDS')
        if not creds_json: return []
        info = json.loads(creds_json)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(info, scope)
        client = gspread.authorize(creds)
        
        spreadsheet = client.open_by_key(SHEET_ID)
        sheet = spreadsheet.worksheet(tab_name)
        data = sheet.get_all_values()
        if not data or len(data) <= 1: return []
        
        headers = [h.strip() for h in data[0]]
        rows = []
        for row in data[1:]:
            if any(row):
                item = dict(zip(headers, row + [''] * (len(headers) - len(row))))
                
                # Rules List Fix
                item['Rules_List'] = [v.strip() for k, v in item.items() if 'rule' in k.lower() and v.strip()]
                
                # Price & Discount Logic
                try:
                    p = int(str(item.get('Price', 0)).replace(',', ''))
                    op = int(str(item.get('Original_Price', 0)).replace(',', ''))
                    item['discount_perc'] = round(((op - p) / op) * 100) if op > p else 0
                except: item['discount_perc'] = 0
                rows.append(item)
        return rows
    except Exception as e:
        print(f"Sheet Error ({tab_name}): {e}")
        return []

def get_settings():
    res = {'Banner_Status': 'OFF', 'Contact': '8830024994', 'Logo_Height': '50', 'Offer_Tag': 'OFFER', 'Logo_URL': '', 'Banner_URL': ''}
    try:
        data = get_master_data("Settings")
        for item in data:
            cols = list(item.values())
            if len(cols) >= 2:
                key, val = str(cols[0]).strip(), str(cols[1]).strip()
                if 'URL' in key and val and not val.startswith('http'): val = 'https://' + val
                res[key] = val
    except: pass
    return res

# --- PUBLIC ROUTES ---

@app.route('/')
def index():
    # 'Villas', 'Settings', aur 'Places' tab se data aayega
    return render_template('index.html', 
                           villas=get_master_data("Villas"), 
                           settings=get_settings(), 
                           tourist_places=get_master_data("Places"))

@app.route('/villa/<villa_id>')
def villa_details(villa_id):
    villas = get_master_data("Villas")
    villa = next((v for v in villas if str(v.get('Villa_ID')).strip() == str(villa_id).strip()), None)
    if not villa: return "Villa Not Found", 404
    
    imgs = [villa.get(f'Image_URL_{i}') for i in range(1, 21) if villa.get(f'Image_URL_{i}')]
    if not any(imgs): imgs = [villa.get('Image_URL')]
    
    return render_template('villa_details.html', villa=villa, villa_images=imgs, settings=get_settings())

@app.route('/privacy-policy')
def privacy_policy():
    return render_template('privacy_policy.html', settings=get_settings())

@app.route('/terms-conditions')
def terms_conditions():
    return render_template('terms_conditions.html', settings=get_settings())

@app.route('/enquiry/<villa_id>', methods=['GET', 'POST'])
def enquiry(villa_id):
    villas = get_master_data("Villas")
    villa = next((v for v in villas if str(v.get('Villa_ID')).strip() == str(villa_id).strip()), None)
    if request.method == 'POST':
        # Telegram & Google Sheet Enquiry Logic
        return render_template('success.html', name=request.form.get('name'), settings=get_settings())
    return render_template('enquiry.html', villa=villa, settings=get_settings())

# --- ADMIN ROUTES (FIXED METHODS) ---

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        return "Invalid Password", 401
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'): return redirect(url_for('admin_login'))
    return render_template('admin_dashboard.html', enquiries=get_master_data("Enquiries"))

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('index'))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
    
