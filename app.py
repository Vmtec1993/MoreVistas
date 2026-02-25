import os
import json
import gspread
from flask import Flask, render_template, request, jsonify
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
            
            # --- Price & Offer Logic ---
            try:
                p_val = str(item.get('Price', '0')).replace(',', '').replace('₹', '').strip()
                op_val = str(item.get('Original_Price', '0')).replace(',', '').replace('₹', '').strip()
                current = int(float(p_val)) if p_val and p_val.lower() != 'nan' else 0
                original = int(float(op_val)) if op_val and op_val.lower() != 'nan' else 0
                item['Price'] = current
                item['Original_Price'] = original
                if original > current > 0:
                    item['discount_perc'] = int(((original - current) / original) * 100)
                else:
                    item['discount_perc'] = 0
            except:
                item['discount_perc'] = 0

            # --- Rules Splitting ---
            raw_rules = item.get('Rules', '')
            if '|' in raw_rules:
                item['Rules_List'] = [r.strip() for r in raw_rules.split('|')]
            else:
                item['Rules_List'] = [raw_rules.strip()] if raw_rules else ["ID Proof Required"]

            item['Villa_ID'] = str(item.get('Villa_ID', '')).strip()
            final_list.append(item)
        return final_list
    except:
        return []

# --- Routes ---

@app.route('/')
def index():
    villas = get_rows(sheet)
    places = get_rows(places_sheet)
    
    # Settings Sheet Logic for Holi Banner & Text
    settings = {'Offer_Text': "Welcome to MoreVistas Lonavala", 'Contact': "8830024994"}
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

@app.route('/explore')
def explore():
    places = get_rows(places_sheet)
    return render_template('explore.html', tourist_places=places)

# ✅ LEGAL ROUTE (For Terms & Privacy Tabs)
@app.route('/legal')
def legal():
    return render_template('legal.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
    
