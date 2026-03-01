import os
import json
import gspread
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from oauth2client.service_account import ServiceAccountCredentials
import requests
from datetime import datetime

app = Flask(__name__)
app.secret_key = "morevistas_secure_2026" 

# --- CONFIG ---
TELEGRAM_TOKEN = "7913354522:AAH1XxMP1EMWC59fpZezM8zunZrWQcAqH18"
TELEGRAM_CHAT_ID = "6746178673"

ADMIN_USER = "Admin"
ADMIN_PASS = "MV@2026" 

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
            all_ws = {ws.title: ws for ws in main_spreadsheet.worksheets()}
            
            places_sheet = all_ws.get("Places")
            enquiry_sheet = all_ws.get("Enquiries")
            settings_sheet = all_ws.get("Settings")
            print("✅ All Sheets Linked Successfully")
        except Exception as e:
            print(f"❌ Sheet Init Error: {e}")

init_sheets()

def get_rows(target_sheet):
    if not target_sheet: return []
    try:
        data = target_sheet.get_all_values()
        if not data or len(data) < 1: return []
        headers = [h.strip() for h in data[0]]
        final_list = []
        for row in data[1:]:
            padded_row = row + [''] * (len(headers) - len(row))
            item = dict(zip(headers, padded_row))
            
            # --- Price & Discount Logic ---
            try:
                p_val = str(item.get('Price', '0')).replace(',', '').replace('₹', '').strip()
                op_val = str(item.get('Original_Price', '0')).replace(',', '').replace('₹', '').strip()
                current = int(float(p_val)) if p_val and p_val.lower() != 'nan' else 0
                original = int(float(op_val)) if op_val and op_val.lower() != 'nan' else 0
                item['Price'] = current
                item['Original_Price'] = original
                item['discount_perc'] = int(((original - current) / original) * 100) if original > current > 0 else 0
            except:
                item['discount_perc'] = 0

            # --- Rules Splitting Logic ---
            raw_rules = str(item.get('Rules', '')).strip()
            if raw_rules:
                if '|' in raw_rules: rules_array = raw_rules.split('|')
                elif '•' in raw_rules: rules_array = raw_rules.split('•')
                elif '\n' in raw_rules: rules_array = raw_rules.split('\n')
                else: rules_array = [raw_rules]
                item['Rules_List'] = [r.strip() for r in rules_array if r.strip()]
            else:
                item['Rules_List'] = ["ID Proof Required", "Standard Rules Apply"]

            item['Villa_ID'] = str(item.get('Villa_ID', '')).strip()

            # --- AUTO SOLD OUT LOGIC ---
            booked_dates = str(item.get('Sold_Dates', '')).strip()
            if datetime.now().strftime("%Y-%m-%d") in booked_dates:
                item['Status'] = 'Sold Out'

            final_list.append(item)
        return final_list
    except Exception as e:
        print(f"Error in get_rows: {e}")
        return []

# --- Routes ---

@app.route('/')
def index():
    villas = get_rows(sheet)
    places = get_rows(places_sheet)
    settings = {'Offer_Text': "Welcome to MoreVistas", 'Banner_URL': "", 'Banner_Show': 'TRUE'}
    if settings_sheet:
        try:
            s_data = settings_sheet.get_all_values()
            for r in s_data:
                if len(r) >= 2: settings[r[0].strip()] = r[1].strip()
        except: pass
    return render_template('index.html', villas=villas, tourist_places=places, settings=settings)

@app.route('/update-offline-dates', methods=['POST'])
def update_offline_dates():
    if not session.get('logged_in'): return redirect(url_for('admin_login'))
    if sheet:
        try:
            villa_id = request.form.get('Villa_ID')
            dates = request.form.get('Sold_Dates')
            data = sheet.get_all_values()
            headers = [h.strip() for h in data[0]]
            id_idx = headers.index('Villa_ID') if 'Villa_ID' in headers else 0
            date_col_idx = headers.index('Sold_Dates') + 1 if 'Sold_Dates' in headers else -1
            if date_col_idx != -1:
                for i, row in enumerate(data[1:], start=2):
                    if str(row[id_idx]).strip() == str(villa_id).strip():
                        sheet.update_cell(i, date_col_idx, dates)
                        break
            return redirect(url_for('admin_dashboard'))
        except Exception as e: return f"Error: {e}", 500
    return redirect(url_for('admin_dashboard'))

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('username') == ADMIN_USER and request.form.get('password') == ADMIN_PASS:
            session['logged_in'] = True
            return redirect(url_for('admin_dashboard'))
    return render_template('admin_login.html')

@app.route('/admin')
def admin_dashboard():
    if not session.get('logged_in'): return redirect(url_for('admin_login'))
    villas = get_rows(sheet)
    enquiries = []
    if enquiry_sheet:
        try:
            data = enquiry_sheet.get_all_values()
            if len(data) > 1:
                headers = data[0]
                for row in data[1:]: enquiries.append(dict(zip(headers, row)))
        except: pass
    return render_template('admin_dashboard.html', villas=villas, enquiries=enquiries[::-1])

@app.route('/enquiry/<villa_id>', methods=['GET', 'POST'])
def enquiry(villa_id):
    villas = get_rows(sheet)
    villa = next((v for v in villas if v.get('Villa_ID') == str(villa_id).strip()), None)
    if request.method == 'POST':
        name = request.form.get('name')
        # PHONE FIX: Country code auto add
        raw_phone = str(request.form.get('phone', '')).strip()
        phone = f"+91 {raw_phone}" if raw_phone and not raw_phone.startswith('+') else raw_phone
        
        # SHEET SYNC: Match columns (Date, Name, Phone, Check-in, Check-out, Guests, Message)
        check_in = request.form.get('check_in', 'N/A')
        check_out = request.form.get('check_out', 'N/A')
        guests = request.form.get('guests', '0')
        message = villa.get('Villa_Name', 'Villa Booking') if villa else "Booking"

        if enquiry_sheet:
            try:
                enquiry_sheet.append_row([
                    datetime.now().strftime("%d-%m-%Y %H:%M"), 
                    name, phone, check_in, check_out, guests, message
                ])
            except: pass
        
        alert = f"🚀 *New Enquiry!*\n🏡 *Villa:* {message}\n👤 *Name:* {name}\n📞 *Phone:* {phone}\n📅 *In:* {check_in} | *Out:* {check_out}\n👥 *Guests:* {guests}"
        requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", params={"chat_id": TELEGRAM_CHAT_ID, "text": alert, "parse_mode": "Markdown"})
        return render_template('success.html', name=name)
    return render_template('enquiry.html', villa=villa)

# ... (Baki ke routes: update-full-villa, villa-details, sitemap same rahenge)

@app.route('/update-full-villa', methods=['POST'])
def update_full_villa():
    if not session.get('logged_in'): return redirect(url_for('admin_login'))
    if sheet:
        try:
            villa_id = request.form.get('Villa_ID')
            data = sheet.get_all_values()
            headers = [h.strip() for h in data[0]]
            updated_fields = request.form.to_dict()
            id_idx = headers.index('Villa_ID') if 'Villa_ID' in headers else 0
            for i, row in enumerate(data[1:], start=2):
                if str(row[id_idx]).strip() == str(villa_id).strip():
                    for key, val in updated_fields.items():
                        if key in headers:
                            col_idx = headers.index(key) + 1
                            sheet.update_cell(i, col_idx, val)
                    break
            return redirect(url_for('admin_dashboard'))
        except Exception as e: return f"Error: {e}", 500
    return redirect(url_for('admin_dashboard'))

@app.route('/villa/<villa_id>')
def villa_details(villa_id):
    villas = get_rows(sheet)
    villa = next((v for v in villas if v.get('Villa_ID') == str(villa_id).strip()), None)
    if not villa: return "Villa Not Found", 404
    imgs = [villa.get(f'Image_URL_{i}') for i in range(1, 21) if villa.get(f'Image_URL_{i}')]
    if not imgs: imgs = [villa.get('Image_URL')]
    return render_template('villa_details.html', villa=villa, villa_images=imgs)

@app.route('/admin-logout')
def admin_logout():
    session.pop('logged_in', None)
    return redirect(url_for('index'))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
    
