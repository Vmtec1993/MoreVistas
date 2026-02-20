import os
import json
import gspread
from flask import Flask, render_template, request, redirect, url_for
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
        sheet = main_spreadsheet.sheet1  # Villas Data
        
        try:
            enquiry_sheet = main_spreadsheet.worksheet("Enquiries")
        except:
            enquiry_sheet = sheet
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
    return render_template('index.html', villas=villas)

@app.route('/villa/<villa_id>')
def villa_details(villa_id):
    if sheet:
        villas = sheet.get_all_records()
        # Villa ID match karne ka logic
        villa = next((v for v in villas if str(v.get('Villa_ID')) == str(villa_id)), None)
        if villa:
            return render_template('villa_details.html', villa=villa)
    return "Villa info not found", 404

# --- YE RHA MISSING ENQUIRY ROUTE (FIXED) ---
# app.py के enquiry वाले हिस्से में इसे बदलें
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
            msg = request.form.get('message', 'No message provided') # Message column fix

            if enquiry_sheet:
                enquiry_sheet.append_row([villa_id, villa.get('Villa_Name'), name, phone, check_in, check_out, guests, msg])

            # TELEGRAM MESSAGE (Pehle jaisa format)
            alert_text = (
                f"🔔 *New Villa Enquiry!*\n\n"
                f"🏡 *Villa:* {villa.get('Villa_Name')}\n"
                f"👤 *Name:* {name}\n"
                f"📞 *Phone:* {phone}\n"
                f"📅 *Dates:* {check_in} to {check_out}\n"
                f"👥 *Guests:* {guests}\n"
                f"📝 *Message:* {msg}"
            )
            send_telegram_alert(alert_text)
            
            return render_template('success.html', name=name) # Professional Success Page

        return render_template('enquiry.html', villa=villa)
    return "Error", 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
