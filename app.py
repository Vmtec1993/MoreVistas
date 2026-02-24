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
places_sheet = None 

if creds_json:
    try:
        info = json.loads(creds_json)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(info, scope)
        client = gspread.authorize(creds)
        
        SHEET_ID = "1wXlMNAUuW2Fr4L05ahxvUNn0yvMedcVosTRJzZf_1ao"
        main_spreadsheet = client.open_by_key(SHEET_ID)
        sheet = main_spreadsheet.sheet1
        
        try:
            enquiry_sheet = main_spreadsheet.worksheet("Enquiries")
        except:
            enquiry_sheet = sheet

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
    except:
        pass

# --- ✅ Live Weather Fetch ---
def get_lonavala_weather():
    try:
        api_key = "b8ee20104f767837862a93361e68787c" 
        url = f"https://api.openweathermap.org/data/2.5/weather?q=Lonavala&units=metric&appid={api_key}"
        data = requests.get(url, timeout=5).json()
        return {
            'temp': round(data['main']['temp']),
            'desc': data['weather'][0]['description'].title(),
            'icon': data['weather'][0]['icon']
        }
    except:
        return None

# --- Routes ---

@app.route('/')
def index():
    weather_data = get_lonavala_weather()
    villas = []
    if sheet:
        try:
            villas = sheet.get_all_records(head=1)
            for v in villas:
                v['Status'] = v.get('Status', 'Available')
        except:
            pass
    return render_template('index.html', villas=villas, weather=weather_data)

@app.route('/explore-lonavala')
def explore_lonavala():
    places = []
    if places_sheet:
        try:
            places = places_sheet.get_all_records(head=1)
        except:
            pass
    return render_template('explore.html', places=places)

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
        try:
            villas = sheet.get_all_records(head=1)
        except: pass
    if enquiry_sheet:
        try:
            enquiries = enquiry_sheet.get_all_records(head=1)
            enquiries.reverse()
        except: pass
    return render_template('admin_dashboard.html', enquiries=enquiries, villas=villas)

@app.route('/update-status/<villa_id>/<new_status>')
def update_villa_status(villa_id, new_status):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    if sheet:
        try:
            all_records = sheet.get_all_records(head=1)
            headers = sheet.row_values(1)
            if "Status" in headers:
                status_col_index = headers.index("Status") + 1
                row_index = 2
                for v in all_records:
                    if str(v.get('Villa_ID')) == str(villa_id):
                        sheet.update_cell(row_index, status_col_index, new_status)
                        break
                    row_index += 1
        except:
            pass
    return redirect(url_for('admin_dashboard', t=datetime.now().timestamp()))

@app.route('/admin-logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

@app.route('/villa/<villa_id>')
def villa_details(villa_id):
    if sheet:
        try:
            villas = sheet.get_all_records(head=1)
            villa = next((v for v in villas if str(v.get('Villa_ID')) == str(villa_id)), None)
            if villa:
                villa['Status'] = villa.get('Status', 'Available')
                villa_images = []
                
                # Check Image_URL and Image_URL_1 to 20
                for i in range(1, 21):
                    # Trying common column names
                    col_names = [f"Image_URL_{i}", f"Image_URL_{i}", "Image_URL" if i==1 else None]
                    img_url = None
                    for name in col_names:
                        if name and name in villa:
                            img_url = villa.get(name)
                            break
                    
                    if img_url and str(img_url).strip() != "" and str(img_url).lower() != 'nan': 
                        if img_url not in villa_images:
                            villa_images.append(img_url)
                
                return render_template('villa_details.html', villa=villa, villa_images=villa_images)
        except Exception as e:
            print(f"Details Error: {e}")
            
    return "Villa info not found", 404

@app.route('/enquiry/<villa_id>', methods=['GET', 'POST'])
def enquiry(villa_id):
    if sheet:
        try:
            villas = sheet.get_all_records(head=1)
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
                    enquiry_sheet.append_row([today_date, name, phone, check_in, check_out, guests, msg])

                alert_text = (f"🔔 *New Booking Enquiry!*\n\n🏡 *Villa:* {villa.get('Villa_Name')}\n👤 *Name:* {name}\n📞 *Phone:* {phone}")
                send_telegram_alert(alert_text)
                return render_template('success.html', name=name)

            return render_template('enquiry.html', villa=villa)
        except:
            pass
    return "Error", 500

if __name__ == "__main__":
    # Render uses port 10000 by default
    port = int(os.environ.get("PORT", 10000)) 
    app.run(host='0.0.0.0', port=port)
                
