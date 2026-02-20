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

# डेटाबेस कनेक्शन को और मज़बूत बनाया गया है
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
        print(f"CRITICAL: Database connection failed: {e}")

# --- Telegram Alert (Direct GET Method) ---
TELEGRAM_TOKEN = "7913354522:AAH1XxMP1EMWC59fpZezM8zunZrWQcAqH18"
TELEGRAM_CHAT_ID = "6746178673"

def send_telegram_alert(message):
    try:
        # ब्राउज़र लिंक वाला तरीका जो 100% काम करता है
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        params = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
        requests.get(url, params=params, timeout=10)
    except:
        pass

# --- Routes ---

@app.route('/')
def index():
    # अगर डेटाबेस कनेक्ट नहीं है, तो खाली लिस्ट दिखाओ ताकि एरर न आए
    villas = []
    if sheet:
        try:
            villas = sheet.get_all_records()
        except:
            pass
    return render_template('index.html', villas=villas)

@app.route('/villa/<villa_id>')
def villa_details(villa_id):
    if sheet:
        try:
            villas = sheet.get_all_records()
            villa = next((v for v in villas if str(v.get('Villa_ID')) == str(villa_id)), None)
            if villa:
                return render_template('villa_details.html', villa=villa)
        except:
            pass
    return "Villa info temporarily unavailable", 404

@app.route('/enquiry/<villa_id>', methods=['GET', 'POST'])
def enquiry(villa_id):
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        
        # गूगल शीट अपडेट
        if enquiry_sheet:
            try:
                enquiry_sheet.append_row([villa_id, name, phone, "N/A", "N/A", "N/A", "Form Submit"])
            except:
                pass

        # टेलीग्राम अलर्ट
        send_telegram_alert(f"🚀 New Enquiry!\nName: {name}\nPhone: {phone}\nVilla: {villa_id}")
        
        return "<h1>Thank you! We will call you soon.</h1><a href='/'>Back</a>"
    
    return render_template('enquiry.html', villa_id=villa_id)

if __name__ == '__main__':
    # पोर्ट एरर फिक्स: रेंडर को 10000 पोर्ट पसंद है
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
    
