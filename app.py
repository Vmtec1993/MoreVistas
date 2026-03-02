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
        
        today_day = datetime.now().weekday()
        today_str = datetime.now().strftime("%Y-%m-%d") 
        
        for row in data[1:]:
            padded_row = row + [''] * (len(headers) - len(row))
            item = dict(zip(headers, padded_row))
            
            # --- 1. Auto Sold Out Logic ---
            sold_dates_str = str(item.get('Sold_Dates', '')).strip()
            if today_str in sold_dates_str:
                item['Status'] = 'Sold Out'

            # --- 2. Price Cleaning (Error Proof) ---
            def clean_p(key):
                val = str(item.get(key, '')).replace(',', '').replace('₹', '').strip()
                # ✅ ADDED: Agar price khali hai ya nan hai, to ise 0 set karein taaki front-end par "Price on Request" dikhe
                if not val or val.lower() == 'nan' or val == '0':
                    return 0
                try:
                    return int(float(val))
                except:
                    return 0

            try:
                item['Price'] = clean_p('Price')
                item['Original_Price'] = clean_p('Original_Price')
                item['Weekday_Price'] = clean_p('Weekday_Price')
                item['Weekend_Price'] = clean_p('Weekend_Price')
                
                # Dynamic Logic
                p_base = item['Price']
                if today_day >= 4: # Fri, Sat, Sun
                    item['current_display_price'] = item['Weekend_Price'] if item['Weekend_Price'] > 0 else p_base
                else:
                    item['current_display_price'] = item['Weekday_Price'] if item['Weekday_Price'] > 0 else p_base
                
                # Savings
                p = item['current_display_price']
                op = item['Original_Price']
                item['amount_saved'] = op - p if op > p else 0
                item['discount_perc'] = int(((op - p) / op) * 100) if op > p > 0 else 0
            except:
                item['current_display_price'] = 0
                item['amount_saved'] = 0

            # --- Rules Logic ---
            raw_rules = str(item.get('Rules', '')).strip()
            if raw_rules:
                rules_array = []
                if '|' in raw_rules: rules_array = raw_rules.split('|')
                elif '•' in raw_rules: rules_array = raw_rules.split('•')
                elif '\n' in raw_rules: rules_array = raw_rules.split('\n')
                else: rules_array = [raw_rules]
                item['Rules_List'] = [r.strip() for r in rules_array if r.strip()]
            else:
                item['Rules_List'] = ["ID Proof Required", "Standard Rules Apply"]

            item['Villa_ID'] = str(item.get('Villa_ID', '')).strip()
            item['Sold_Dates'] = sold_dates_str
            final_list.append(item)
        return final_list
    except Exception as e:
        print(f"Error in get_rows: {e}")
        return []

# --- Routes (Sabh routes original hain bina kisi badlav ke) ---

@app.route('/')
def index():
    villas = get_rows(sheet)
    places = get_rows(places_sheet)
    settings = {'Offer_Text': "Welcome", 'Banner_URL': "", 'Banner_Show': 'FALSE'}
    if settings_sheet:
        try:
            s_data = settings_sheet.get_all_values()
            for r in s_data:
                if len(r) >= 2: settings[r[0].strip()] = r[1].strip()
        except: pass
    return render_template('index.html', villas=villas, tourist_places=places, settings=settings)

@app.route('/villa/<villa_id>')
def villa_details(villa_id):
    villas = get_rows(sheet)
    villa = next((v for v in villas if v.get('Villa_ID') == str(villa_id).strip()), None)
    if not villa: return "Villa Not Found", 404
    imgs = [villa.get(f'Image_URL_{i}') for i in range(1, 21) if villa.get(f'Image_URL_{i}')]
    if not imgs: imgs = [villa.get('Image_URL')]
    return render_template('villa_details.html', villa=villa, villa_images=imgs)

@app.route('/enquiry/<villa_id>', methods=['GET', 'POST'])
def enquiry(villa_id):
    villas = get_rows(sheet)
    villa = next((v for v in villas if v.get('Villa_ID') == str(villa_id).strip()), None)
    if request.method == 'POST':
        name, phone = request.form.get('name'), request.form.get('phone')
        dates, guests = request.form.get('stay_dates'), request.form.get('guests')
        v_name = villa.get('Villa_Name', 'Villa') if villa else "Villa"
        if enquiry_sheet:
            try: enquiry_sheet.append_row([datetime.now().strftime("%d-%m-%Y %H:%M"), name, phone, dates, guests, v_name])
            except: pass
        alert = f"🚀 *New Enquiry!*\n🏡 *Villa:* {v_name}\n👤 *Name:* {name}\n📞 *Phone:* {phone}\n📅 *Dates:* {dates}\n👥 *Guests:* {guests}"
        requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", params={"chat_id": TELEGRAM_CHAT_ID, "text": alert, "parse_mode": "Markdown"})
        return render_template('success.html', name=name, villa_name=v_name)
    return render_template('enquiry.html', villa=villa)

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        u = request.form.get('username')
        p = request.form.get('password')
        if u == ADMIN_USER and p == ADMIN_PASS:
            session['logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            error = "Invalid Username"
    return render_template('admin_login.html', error=error)

@app.route('/admin')
def admin_dashboard():
    if not session.get('logged_in'): return redirect(url_for('admin_login'))
    villas = get_rows(sheet)
    all_enquiries = get_rows(enquiry_sheet)
    enquiries = all_enquiries[-10:] if all_enquiries else []
    settings = {}
    if settings_sheet:
        try:
            s_data = settings_sheet.get_all_values()
            for r in s_data:
                if len(r) >= 2: settings[r[0].strip()] = r[1].strip()
        except: pass
    return render_template('admin_dashboard.html', villas=villas, enquiries=enquiries, settings=settings)

@app.route('/admin-logout')
def admin_logout():
    session.pop('logged_in', None)
    return redirect(url_for('index'))

@app.route('/update-settings', methods=['POST'])
def update_settings():
    if not session.get('logged_in'): return redirect(url_for('admin_login'))
    if settings_sheet:
        try:
            settings_sheet.update('B1', request.form.get('banner_url'))
            settings_sheet.update('B2', request.form.get('offer_text'))
            show = "TRUE" if request.form.get('banner_show') else "FALSE"
            settings_sheet.update('B3', show)
        except: pass
    return redirect(url_for('admin_dashboard'))

@app.route('/update-offline-dates', methods=['POST'])
def update_offline_dates():
    if not session.get('logged_in'): return redirect(url_for('admin_login'))
    villa_id = request.form.get('Villa_ID')
    sold_dates = request.form.get('Sold_Dates')
    if sheet:
        try:
            data = sheet.get_all_values()
            headers = data[0]
            id_idx = headers.index('Villa_ID')
            sold_idx = headers.index('Sold_Dates') if 'Sold_Dates' in headers else -1
            if sold_idx != -1:
                for i, row in enumerate(data[1:], start=2):
                    if str(row[id_idx]).strip() == str(villa_id).strip():
                        sheet.update_cell(i, sold_idx + 1, sold_dates)
                        break
        except: pass
    return redirect(url_for('admin_dashboard'))

@app.route('/update-full-villa', methods=['POST'])
def update_full_villa():
    if not session.get('logged_in'): return redirect(url_for('admin_login'))
    v_id = request.form.get('Villa_ID')
    updates = {
        'Villa_Name': request.form.get('Villa_Name'),
        'BHK': request.form.get('BHK'),
        'Status': request.form.get('Status'),
        'Original_Price': request.form.get('Original_Price', '').strip(),
        'Weekday_Price': request.form.get('Weekday_Price', '').strip(),
        'Weekend_Price': request.form.get('Weekend_Price', '').strip(),
        'Amenities': request.form.get('Amenities'),
        'Rules': request.form.get('Rules')
    }
    if sheet:
        try:
            data = sheet.get_all_values()
            headers = data[0]
            id_idx = headers.index('Villa_ID')
            for i, row in enumerate(data[1:], start=2):
                if str(row[id_idx]).strip() == str(v_id).strip():
                    for key, value in updates.items():
                        if key in headers:
                            col_idx = headers.index(key) + 1
                            # ✅ Admin Dashboard se khali karne par sheet se bhi hat jayega
                            sheet.update_cell(i, col_idx, value if value else "")
                    break
        except: pass
    return redirect(url_for('admin_dashboard'))

@app.route('/quick-status-update', methods=['POST'])
def quick_status_update():
    if not session.get('logged_in'): return redirect(url_for('admin_login'))
    v_id = request.form.get('Villa_ID')
    curr = request.form.get('current_status')
    new_status = "Sold Out" if curr.lower() == 'available' else "Available"
    if sheet:
        try:
            data = sheet.get_all_values()
            headers = data[0]
            id_idx = headers.index('Villa_ID')
            st_idx = headers.index('Status')
            for i, row in enumerate(data[1:], start=2):
                if str(row[id_idx]).strip() == str(v_id).strip():
                    sheet.update_cell(i, st_idx + 1, new_status)
                    break
        except: pass
    return redirect(url_for('admin_dashboard'))

@app.route('/explore')
def explore(): return render_template('explore.html', tourist_places=get_rows(places_sheet))

@app.route('/contact')
def contact(): return render_template('contact.html')

@app.route('/legal')
def legal(): return render_template('legal.html')

@app.route('/list-property')
def list_property(): return render_template('list_property.html')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
    
