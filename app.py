import os
import json
import logging
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Logging setup for Render
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def get_gspread_client():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_json = os.environ.get("GOOGLE_CREDS")
        if not creds_json:
            logger.error("GOOGLE_CREDS missing in Render settings!")
            return None
        creds_dict = json.loads(creds_json)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)
    except Exception as e:
        logger.error(f"Gspread Connection Error: {e}")
        return None

@app.route('/')
def index():
    try:
        client = get_gspread_client()
        if client:
            sheet = client.open("Geetai_Villa_Data").get_worksheet(0)
            villas = sheet.get_all_records()
            # यहाँ हम यह सुनिश्चित कर रहे हैं कि डेटा खाली न हो
            return render_template('index.html', villas=villas)
        return "Database Connection Failed", 500
    except Exception as e:
        logger.error(f"Home Page Error: {e}")
        return render_template('index.html', villas=[]) # खाली लिस्ट भेजें ताकि एरर न आए


@app.route('/villa/<villa_id>')
def villa_details(villa_id):
    try:
        client = get_gspread_client()
        if client:
            sheet = client.open("Geetai_Villa_Data").get_worksheet(0)
            villas = sheet.get_all_records()
            villa = next((v for v in villas if str(v.get('Villa_ID', '')).strip() == str(villa_id).strip()), None)
            if not villa:
                return "Villa Not Found", 404
            return render_template('villa_details.html', villa=villa)
        return "Database Error", 500
    except Exception as e:
        logger.error(f"Details Page Error: {e}")
        return "Error loading villa details", 500

@app.route('/submit_enquiry', methods=['POST'])
def submit_enquiry():
    try:
        data = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            request.form.get('name'),
            request.form.get('phone'),
            request.form.get('check_in'),
            request.form.get('check_out'),
            request.form.get('guests'),
            request.form.get('message')
        ]
        client = get_gspread_client()
        sheet = client.open("Geetai_Villa_Data").worksheet("Enquiries")
        sheet.append_row(data)
        return redirect(url_for('success'))
    except Exception as e:
        return f"Error: {e}", 500

@app.route('/success')
def success():
    return render_template('success.html')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
    
