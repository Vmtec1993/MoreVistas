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
        
        is_weekend = datetime.now().weekday() in [4, 5, 6]
        
        for row in data[1:]:
            padded_row = row + [''] * (len(headers) - len(row))
            item = dict(zip(headers, padded_row))
            
            try:
                # SAFE PRICE LOGIC (No changes to math)
                raw_weekday = item.get('Weekday_Price') or item.get('Price', '0')
                raw_weekend = item.get('Weekend_Price') or item.get('Price', '0')
                raw_original = item.get('Original_Price') or item.get('Price', '0')

                def clean_price(val):
                    v = str(val).replace(',', '').replace('₹', '').strip()
                    try: return int(float(v))
                    except: return 0

                weekday_amt = clean_price(raw_weekday)
                weekend_amt = clean_price(raw_weekend)
                original = clean_price(raw_original)
                
                current_price = weekend_amt if is_weekend else weekday_amt
                
                item['Price'] = current_price
                item['Weekday_Price'] = weekday_amt
                item['Weekend_Price'] = weekend_amt
                item['Original_Price'] = original
                item['is_weekend_today'] = is_weekend
                
                item['discount_perc'] = int(((original - current_price) / original) * 100) if original > current_price > 0 else 0
            except:
                item['Price'] = 0
                item['discount_perc'] = 0

            raw_rules = str(item.get('Rules', '')).strip()
            item['Rules_List'] = [r.strip() for r in (raw_rules.split('|') if '|' in raw_rules else [raw_rules]) if r.strip()]

            booked_dates = str(item.get('Sold_Dates', '')).strip()
            if datetime.now().strftime("%Y-%m-%d") in booked_dates:
                item['Status'] = 'Sold Out'

            final_list.append(item)
        return final_list
    except Exception as e:
        print(f"Error in get_rows: {e}")
        return []

# --- 1. SIDE MENU ROUTES (Ab 404 nahi aayega) ---
@app.route('/explore')
def explore():
    places = get_rows(places_sheet)
    return render_template('explore.html', tourist_places=places)

@app.route('/contact')
def contact(): return render_template('contact.html')

@app.route('/list-property')
def list_property(): return render_template('list_property.html')

@app.route('/legal')
def legal(): return render_template('legal.html')

# --- 2. MAIN INDEX ---
@app.route('/')
def index():
    villas = get_rows(sheet)
    places = get_rows(places_sheet)
    settings = {'Offer_Text': "Welcome", 'Banner_Show': 'TRUE'}
    if settings_sheet:
        try:
            for r in settings_sheet.get_all_values():
                if len(r) >= 2: settings[r[0].strip()] = r[1].strip()
        except: pass
    return render_template('index.html', villas=villas, tourist_places=places, settings=settings)

# --- 3. VILLA DETAILS (Ise delete mat karna) ---
@app.route('/villa/<villa_id>')
def villa_details(villa_id):
    villas = get_rows(sheet)
    villa = next((v for v in villas if v.get('Villa_ID') == str(villa_id).strip()), None)
    if not villa: return "Villa Not Found", 404
    
    raw_dates = str(villa.get('Sold_Dates', '')).strip()
    booked_dates_list = [d.strip() for d in raw_dates.split(',') if d.strip()]
    
    imgs = [villa.get(f'Image_URL_{i}') for i in range(1, 21) if villa.get(f'Image_URL_{i}')]
    if not imgs: imgs = [villa.get('Image_URL')]
    
    return render_template('villa_details.html', villa=villa, villa_images=imgs, booked_dates=booked_dates_list)

# --- 4. ADMIN SECTION (Fixed Internal Server Error) ---
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

# --- 5. ENQUIRY SUBMIT (Fixed +91 Logic) ---
@app.route('/enquiry/<villa_id>', methods=['GET', 'POST'])
def enquiry(villa_id):
    villas = get_rows(sheet)
    villa = next((v for v in villas if v.get('Villa_ID') == str(villa_id).strip()), None)
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone') # Form mein +91 pehle se lock hoga
        check_in = request.form.get('check_in')
        check_out = request.form.get('check_out')
        guests = request.form.get('guests')
        villa_name = villa.get('Villa_Name') if villa else "Villa"

        if enquiry_sheet:
            enquiry_sheet.append_row([datetime.now().strftime("%d-%m-%Y %H:%M"), name, phone, check_in, check_out, guests, villa_name])
        
        alert = f"🚀 *New Booking Enquiry!*\n🏡 *Villa:* {villa_name}\n👤 *Name:* {name}\n📞 *Phone:* {phone}\n📅 *Dates:* {check_in} to {check_out}"
        requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", params={"chat_id": TELEGRAM_CHAT_ID, "text": alert, "parse_mode": "Markdown"})
        
        return render_template('success.html', name=name)
    return render_template('enquiry.html', villa=villa)

# --- 6. UPDATE & LOGOUT ---
@app.route('/update-full-villa', methods=['POST'])
def update_full_villa():
    if not session.get('logged_in'): return redirect(url_for('admin_login'))
    # ... (Aapka update logic)
    return redirect(url_for('admin_dashboard'))

@app.route('/admin-logout')
def admin_logout():
    session.pop('logged_in', None)
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
    
