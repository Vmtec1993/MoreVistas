import os
import json
import logging
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# एरर और प्रोसेस को ट्रैक करने के लिए लॉगिंग
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Google Sheets को कनेक्ट करने वाला फंक्शन
def get_gspread_client():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        # Render के Environment Variables से 'GOOGLE_CREDS' उठाना
        creds_json = os.environ.get("GOOGLE_CREDS")
        
        if not creds_json:
            logger.error("GOOGLE_CREDS variable is missing in Render settings!")
            return None

        creds_dict = json.loads(creds_json)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)
    except Exception as e:
        logger.error(f"Failed to connect to Google Sheets: {e}")
        return None

# होम पेज - सभी विला दिखाने के लिए
@app.route('/')
def index():
    try:
        client = get_gspread_client()
        if client:
            sheet = client.open("Geetai_Villa_Data").get_worksheet(0)
            villas = sheet.get_all_records()
            return render_template('index.html', villas=villas)
        return "Database Connection Error", 500
    except Exception as e:
        logger.error(f"Index Error: {e}")
        return "Something went wrong on the Home Page", 500

# विला डिटेल्स पेज
@app.route('/villa/<villa_id>')
def villa_details(villa_id):
    try:
        client = get_gspread_client()
        if client:
            sheet = client.open("Geetai_Villa_Data").get_worksheet(0)
            villas = sheet.get_all_records()
            # विला ID मैच करना (स्ट्रिपिंग ताकि कोई स्पेस एरर न दे)
            villa = next((v for v in villas if str(v.get('Villa_ID', '')).strip() == str(villa_id).strip()), None)
            
            if not villa:
                return "Villa Not Found", 404
            return render_template('villa_details.html', villa=villa)
        return "Database Error", 500
    except Exception as e:
        logger.error(f"Details Error: {e}")
        return "Error fetching villa details", 500

# एन्क्वायरी फॉर्म पेज
@app.route('/enquiry/<villa_id>')
def enquiry(villa_id):
    return render_template('enquiry.html', villa_id=villa_id)

# फॉर्म सबमिट करने वाला रूट (डेटा शीट में लिखेगा)
@app.route('/submit_enquiry', methods=['POST'])
def submit_enquiry():
    try:
        # फॉर्म से डेटा निकालना
        name = request.form.get('name')
        phone = request.form.get('phone')
        message = request.form.get('message')
        date_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        client = get_gspread_client()
        if client:
            # पक्का करें कि आपकी Google Sheet में 'Enquiries' नाम की टैब मौजूद है
            sheet = client.open("Geetai_Villa_Data").worksheet("Enquiries")
            sheet.append_row([date_now, name, phone, message])
            logger.info(f"New enquiry
