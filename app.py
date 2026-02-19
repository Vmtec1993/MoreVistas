import os
import json
import logging
from flask import Flask, render_template, request, redirect, url_for
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# एरर को लॉग्स में देखने के लिए सेटिंग
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)

def get_sheets_data():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_json = os.environ.get("GOOGLE_CREDS")
        
        if not creds_json:
            app.logger.error("GOOGLE_CREDS environment variable NOT found!")
            return []

        creds_dict = json.loads(creds_json)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        # यहाँ 'Geetai_Villa_Data' की जगह अपनी शीट का सटीक नाम लिखें
        spreadsheet = client.open("Geetai_Villa_Data")
        sheet = spreadsheet.get_worksheet(0)
        data = sheet.get_all_records()
        app.logger.info(f"Successfully fetched {len(data)} records from Google Sheets")
        return data
    except Exception as e:
        app.logger.error(f"DETAILED ERROR: {str(e)}")
        return []

@app.route('/')
def index():
    try:
        villas = get_sheets_data()
        return render_template('index.html', villas=villas)
    except Exception as e:
        app.logger.error(f"Index Route Error: {e}")
        return str(e)

@app.route('/villa/<villa_id>')
def villa_details(villa_id):
    try:
        villas = get_sheets_data()
        villa = next((v for v in villas if str(v.get('Villa_ID', '')).strip() == str(villa_id).strip()), None)
        if not villa:
            app.logger.warning(f"Villa ID {villa_id} not found in data")
            return "Villa Not Found", 404
        return render_template('villa_details.html', villa=villa)
    except Exception as e:
        app.logger.error(f"Details Route Error: {e}")
        return str(e)

if __name__ == '__main__':
    # रेंडर के लिए पोर्ट बाइंडिंग (यह बहुत ज़रूरी है)
    port = int(os.environ.get("PORT", 5000))
    app.logger.info(f"Starting app on port {port}")
    app.run(host='0.0.0.0', port=port)
    
