import os
import json
import logging
from flask import Flask, render_template, request, redirect, url_for
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# एरर को रेंडर के लॉग्स में देखने के लिए (Debugging)
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def get_sheets_data():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_json = os.environ.get("GOOGLE_CREDS")
        
        if not creds_json:
            logger.error("!!! ERROR: GOOGLE_CREDS environment variable is MISSING !!!")
            return []

        creds_dict = json.loads(creds_json)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        # यहाँ पक्का करें कि आपकी शीट का नाम यही है
        spreadsheet = client.open("Geetai_Villa_Data")
        sheet = spreadsheet.get_worksheet(0) # पहली शीट उठाएगा
        data = sheet.get_all_records()
        logger.info(f"Successfully loaded {len(data)} villas from Google Sheets.")
        return data
    except Exception as e:
        logger.error(f"!!! GOOGLE SHEETS CONNECTION ERROR: {str(e)} !!!")
        return []

@app.route('/')
def index():
    villas = get_sheets_data()
    return render_template('index.html', villas=villas)

@app.route('/villa/<villa_id>')
def villa_details(villa_id):
    villas = get_sheets_data()
    # ID को मैच करने का सबसे सुरक्षित तरीका
    villa = next((v for v in villas if str(v.get('Villa_ID', '')).strip() == str(villa_id).strip()), None)
    if not villa:
        logger.warning(f"Villa with ID {villa_id} not found.")
        return "Villa Not Found", 404
    return render_template('villa_details.html', villa=villa)

# Enquiry & Success Routes
@app.route('/enquiry/<villa_id>')
def enquiry(villa_id):
    return render_template('enquiry.html', villa_id=villa_id)

@app.route('/success')
def success():
    return render_template('success.html')

if __name__ == '__main__':
    # रेंडर के लिए पोर्ट बाइंडिंग
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"App is starting on port {port}")
    app.run(host='0.0.0.0', port=port)
