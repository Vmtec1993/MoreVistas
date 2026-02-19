import os
import json
from flask import Flask, render_template
import gspread
from google.oauth2.service_account import Credentials

app = Flask(__name__)

def get_sheets_data():
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_raw = os.environ.get("GOOGLE_CREDS")
        if not creds_raw: return []
        creds_raw = creds_raw.strip().strip("'").strip('"')
        info = json.loads(creds_raw)
        if "private_key" in info:
            info["private_key"] = info["private_key"].replace("\\n", "\n")
        creds = Credentials.from_service_account_info(info, scopes=scopes)
        client = gspread.authorize(creds)
        spreadsheet = client.open("Geetai_Villa_Data")
        sheet = spreadsheet.get_worksheet(0)
        return sheet.get_all_records()
    except Exception:
        return []

@app.route('/')
def index():
    villas = get_sheets_data()
    return render_template('index.html', villas=villas)

@app.route('/villa/<villa_id>')
def villa_details(villa_id):
    villas = get_sheets_data()
    # ID मैच करने का सबसे पक्का तरीका
    villa = next((v for v in villas if str(v.get('Villa_ID', '')) == str(villa_id)), None)
    if not villa:
        return "<h1>Villa Not Found!</h1><a href='/'>Go Back</a>", 404
    return render_template('villa_details.html', villa=villa)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
    
