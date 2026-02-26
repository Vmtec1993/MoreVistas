import os
import json
import gspread
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from oauth2client.service_account import ServiceAccountCredentials
import requests
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
            
            print("✅ Sheets Linked Successfully")
        except Exception as e:
            print(f"❌ Sheet Init Error: {e}")

init_sheets()

# --- Utility Functions ---

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
            item = dict(zip(headers, padded_row))
            
            # Price Processing
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
            
            # Rules Processing
            raw_rules = item.get('Rules', '')
            item['Rules_List'] = [r.strip() for r in raw_rules.split('|')] if '|' in raw_rules else ([raw_rules.strip()] if raw_rules else ["ID Proof Required"])
            item['Villa_ID'] = str(item.get('Villa_ID', '')).strip()
            final_list.append(item)
        return final_list
    except: return []

def get_settings():
    res = {
        'Offer_Text': "Welcome to MoreVistas", 
        'Contact': "8830024994", 
        'Logo_URL': '', 
        'Logo_Width': '160', 
        'Banner_URL': '', 
        'Banner_Status': 'OFF'
    }
    if settings_sheet:
        try:
            data = settings_sheet.get_all_values()
            for r in data:
                if len(r) >= 2:
                    key = r[0].strip()
                    val = r[1].strip()
                    if key: res[key] = val
        except: pass
    return res

# --- Routes ---

@app.route('/')
def index():
    settings = get_settings()
    villas = get_rows(sheet)
    places = get_rows(places_sheet)
    sorted_villas = sorted(villas, key=lambda x: str(x.get('Status', '')).lower() == 'sold out')
    return render_template('index.html', villas=sorted_villas, tourist_places=places, settings=settings)

@app.route('/admin', methods=['GET', 'POST'])
def admin_dashboard():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
        else:
            return "<script>alert('Incorrect Password!'); window.location='/admin';</script>"
            
    if not session.get('admin_logged_in'):
        return render_template('admin_login.html')

    villas = get_rows(sheet)
    settings = get_settings()
    enquiries = []
    
    if enquiry_sheet:
        try:
            raw_enq = enquiry_sheet.get_all_values()
            if len(raw_enq) > 1:
                headers = [h.strip() for h in raw_enq[0]]
                rows = [r for r in raw_enq[1:] if any(r)]
                rows.reverse() # Latest entries first
                enquiries = [dict(zip(headers, r + [''] * (len(headers) - len(r)))) for r in rows]
        except: pass
        
    # Yahan render_template ka naam dashboard wali file par set kar diya
    return render_template('admin_dashboard.html', villas=villas, enquiries=enquiries, settings=settings)

@app.route('/admin/update', methods=['POST'])
def update_data():
    if not session.get('admin_logged_in'): return jsonify({"status": "error"}), 403
    target = request.form.get('target')
    key = request.form.get('key')
    val = request.form.get('value')
    v_id = request.form.get('villa_id')
    
    try:
        if target == "settings" and settings_sheet:
            try:
                cell = settings_sheet.find(key)
                settings_sheet.update_cell(cell.row, 2, val)
            except:
                settings_sheet.append_row([key, val])
        elif target == "villas" and sheet:
            cell = sheet.find(str(v_id))
            headers = sheet.row_values(1)
            col_index = headers.index(key) + 1
            sheet.update_cell(cell.row, col_index, val)
        return jsonify({"status": "success"})
    except Exception as e: 
        return jsonify({"status": "error", "message": str(e)})

@app.route('/villa/<villa_id>')
def villa_details(villa_id):
    villas = get_rows(sheet)
    villa = next((v for v in villas if str(v.get('Villa_ID', '')).strip() == str(villa_id).strip()), None)
    if not villa: return "Villa Not Found", 404
    imgs = [villa.get(f'Image_URL_{i}') for i in range(1, 21) if villa.get(f'Image_URL_{i}')] or [villa.get('Image_URL')]
    return render_template('villa_details.html', villa=villa, villa_images=imgs, settings=get_settings())

@app.route('/enquiry/<villa_id>', methods=['GET', 'POST'])
def enquiry(villa_id):
    villas = get_rows(sheet)
    villa = next((v for v in villas if str(v.get('Villa_ID', '')).strip() == str(villa_id).strip()), None)
    settings = get_settings()
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        dates = request.form.get('stay_dates')
        guests = request.form.get('guests')
        v_name = villa.get('Villa_Name', 'Villa') if villa else "Villa"
        
        if enquiry_sheet:
            try: 
                enquiry_sheet.append_row([datetime.now().strftime("%d-%m-%Y %H:%M"), name, phone, dates, guests, v_name])
            except: pass
            
        alert = f"🚀 *New Enquiry!*\n🏡 *Villa:* {v_name}\n👤 *Name:* {name}\n📞 *Phone:* {phone}\n📅 *Dates:* {dates}\n👥 *Guests:* {guests}"
        requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", params={"chat_id": TELEGRAM_CHAT_ID, "text": alert, "parse_mode": "Markdown"})
        return render_template('success.html', name=name, villa_name=v_name, settings=settings)
        
    return render_template('enquiry.html', villa=villa, settings=settings)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('index'))

@app.route('/explore')
def explore():
    return render_template('explore.html', tourist_places=get_rows(places_sheet), settings=get_settings())

@app.route('/contact')
def contact(): 
    return render_template('contact.html', settings=get_settings())

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
