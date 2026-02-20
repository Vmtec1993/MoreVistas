import os
import json
import gspread
from flask import Flask, render_template, request
from oauth2client.service_account import ServiceAccountCredentials
import requests

app = Flask(__name__)

# --- Database Connection ---
creds_json = os.environ.get('GOOGLE_CREDS')
sheet = None

if creds_json:
    try:
        info = json.loads(creds_json)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(info, scope)
        client = gspread.authorize(creds)
        SHEET_ID = "1wXlMNAUuW2Fr4L05ahxvUNn0yvMedcVosTRJzZf_1ao"
        sheet = client.open_by_key(SHEET_ID).sheet1
    except Exception as e:
        print(f"DB Error: {e}")

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
        villa = next((v for v in villas if str(v.get('Villa_ID')) == str(villa_id)), None)
        if villa:
            return render_template('villa_details.html', villa=villa)
    return "Villa Not Found", 404

# ... (बाकी Telegram और Enquiry वाला पुराना कोड वही रहेगा)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
    
