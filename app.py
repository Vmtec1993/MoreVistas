import os
import json
import gspread
from flask import Flask, render_template, request
from oauth2client.service_account import ServiceAccountCredentials
import requests

app = Flask(__name__)

# --- Google Sheets Setup ---
creds_json = os.environ.get('GOOGLE_CREDS')
sheet = None
enquiry_sheet = None

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
    except Exception as e:
        print(f"Sheet Error: {e}")

# --- Telegram Alert (Direct Method - Fixed) ---
TELEGRAM_TOKEN = "7913354522:AAH1XxMP1EMWC59fpZezM8zunZrWQcAqH18"
TELEGRAM_CHAT_ID = "6746178673"

def send_telegram_alert(message):
    try:
        # वही GET तरीका जो आपके ब्राउज़र लिंक में सफल रहा
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        params = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message
        }
        # बिना किसी भारी डेटा के सीधा रिक्वेस्ट भेजना
        requests.get(url, params=params, timeout=10)
    except Exception as e:
        print(f"Telegram Error: {e}")

# --- Routes ---

@app.route('/')
def index():
    if sheet:
        try:
            villas = sheet.get_all_records()
            return render_template('index.html', villas=villas)
        except: pass
    return "Database Connection Error", 500

@app.route('/villa/<villa_id>')
def villa_details(villa_id):
    if sheet:
        try:
            villas = sheet.get_all_records()
            villa = next((v for v in villas if str(v.get('Villa_ID')) == str(villa_id)), None)
            if villa:
                return render_template('villa_details.html', villa=villa)
        except: pass
    return "Villa not found", 404

@app.route('/enquiry/<villa_id>', methods=['GET', 'POST'])
def enquiry(villa_id):
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        check_in = request.form.get('check_in')
        check_out = request.form.get('check_out')
        guests = request.form.get('guests')
        message = request.form.get('message')

        # Google Sheet Update
        if enquiry_sheet:
            try:
                enquiry_sheet.append_row([villa_id, name, phone, check_in, check_out, guests, message])
            except: pass

        # टेलीग्राम अलर्ट
        alert_text = f"New Enquiry!\nName: {name}\nPhone: {phone}\nVilla: {villa_id}"
        send_telegram_alert(alert_text)
        
        # क्रैश से बचने के लिए सीधा मैसेज
        return "<h1>Thank You! Your Enquiry has been sent.</h1><a href='/'>Back to Home</a>"
    
    return render_template('enquiry.html', villa_id=villa_id)

if __name__ == '__main__':
    # Render Port Fix: रेंडर PORT एनवायरनमेंट वेरिएबल का इस्तेमाल करता है
    # हमने यहाँ '0.0.0.0' और डायनामिक पोर्ट सेट किया है
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
    
