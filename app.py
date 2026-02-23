import os
import json
import gspread
from flask import Flask, render_template, request, redirect, url_for, session
from oauth2client.service_account import ServiceAccountCredentials
import requests
from datetime import datetime

app = Flask(__name__)
app.secret_key = "morevistas_admin_secure_key_2026" 

# --- Google Sheets Setup ---
creds_json = os.environ.get('GOOGLE_CREDS')
sheet = None
enquiry_sheet = None
places_sheet = None # ✅ नया: टूरिस्ट पॉइंट्स के लिए

if creds_json:
    try:
        info = json.loads(creds_json)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(info, scope)
        client = gspread.authorize(creds)
        
        SHEET_ID = "1wXlMNAUuW2Fr4L05ahxvUNn0yvMedcVosTRJzZf_1ao"
        main_spreadsheet = client.open_by_key(SHEET_ID)
        sheet = main_spreadsheet.sheet1  # Villas Data
        
        try:
            enquiry_sheet = main_spreadsheet.worksheet("Enquiries")
        except:
            enquiry_sheet = sheet

        # ✅ नया: "Places" वर्कशीट लोड करना
        try:
            places_sheet = main_spreadsheet.worksheet("Places")
        except:
            places_sheet = None

    except Exception as e:
        print(f"Sheet Error: {e}")

# --- Telegram Setup ---
TELEGRAM_TOKEN = "7913354522:AAH1XxMP1EMWC59fpZezM8zunZrWQcAqH18"
TELEGRAM_CHAT_ID = "6746178673"

def send_telegram_alert(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        params = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        requests.get(url, params=params, timeout=10)
    except: pass

# --- Routes ---

@app.route('/')
def index():
    villas = []
    if sheet:
        villas = sheet.get_all_records()
        for v in villas:
            v['Status'] = v.get('Status', 'Available')
    return render_template('index.html', villas=villas)

# ✅ नया: Explore Lonavala Route
@app.route('/explore-lonavala')
def explore_lonavala():
    places = []
    if places_sheet:
        try:
            places = places_sheet.get_all_records()
        except Exception as e:
            print(f"Places Fetch Error: {e}")
    return render_template('explore.html', places=places)

# ✅ Admin Routes
@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        user = request.form.get('username')
        pwd = request.form.get('password')
        if user == "admin" and pwd == "MoreVistas@2026":
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            error = "Invalid Username or Password!"
    return render_template('admin_login.html', error=error)

@app.route('/admin-dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    enquiries = []
    villas = []
    if sheet:
        villas = sheet.get_all_records()
    if enquiry_sheet:
        enquiries = enquiry_sheet.get_all_records()
        enquiries.reverse()
        
    return render_template('admin_dashboard.html', enquiries=enquiries, villas=villas)

@app.route('/update-status/<villa_id>/<new_status>')
def update_villa_status(villa_id, new_status):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    if sheet:
        try:
            all_records = sheet.get_all_records()
            headers = sheet.row_values(1)
            try:
                status_col_index = headers.index("Status") + 1
            except ValueError:
                return "Error: Please add a column named 'Status' in your Google Sheet"

            row_index = 2
            for v in all_records:
                if str(v.get('Villa_ID')) == str(villa_id):
                    sheet.update_cell(row_index, status_col_index, new_status)
                    break
                row_index += 1
        except Exception as e:
            print(f"Update Error: {e}")
            
    # ✅ Auto-refresh फिक्स के लिए टाइमस्टैम्प के साथ रीडायरेक्ट
    return redirect(url_for('admin_dashboard', t=datetime.now().timestamp()))

@app.route('/admin-logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

@app.route('/villa/<villa_id>')
def villa_details(villa_id):
    if sheet:
        villas = sheet.get_all_records()
        villa = next((v for v in villas if str(v.get('Villa_ID')) == str(villa_id)), None)
        if villa:
            villa['Status'] = villa.get('Status', 'Available')
            return render_template('villa_details.html', villa=villa)
    return "Villa info not found", 404

@app.route('/enquiry/<villa_id>', methods=['GET', 'POST'])
def enquiry(villa_id):
    if sheet:
        villas = sheet.get_all_records()
        villa = next((v for v in villas if str(v.get('Villa_ID')) == str(villa_id)), None)
        
        if request.method == 'POST':
            name = request.form.get('name')
            phone = request.form.get('phone')
            check_in = request.form.get('check_in')
            check_out = request.form.get('check_out')
            guests = request.form.get('guests')
            msg = request.form.get('message', 'No message')
            today_date = datetime.now().strftime("%d-%m-%Y %H:%M")

            if enquiry_sheet:
                try:
                    enquiry_sheet.append_row([today_date, name, phone, check_in, check_out, guests, msg])
                except: pass

            alert_text = (f"🔔 *New Booking Enquiry!*\n\n🏡 *Villa:* {villa.get('Villa_Name')}\n👤 *Name:* {name}\n📞 *Phone:* {phone}")
            send_telegram_alert(alert_text)
            return render_template('success.html', name=name)

        return render_template('enquiry.html', villa=villa)
    return "Error", 500

if __name__ == "__main__":
    # Render के लिए पोर्ट को डायनामिक रखें
    port = int(os.environ.get("PORT", 5000)) 
    # host को '0.0.0.0' रखना बहुत ज़रूरी है
    app.run(host='0.0.0.0', port=port)

            
