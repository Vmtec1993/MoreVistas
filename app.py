import os
import json
import gspread
import datetime
from flask import Flask, render_template, request
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)

# 1. Google Sheets Connection Function
def get_gspread_client():
    # सिर्फ Render के Environment Variable से डेटा उठाएगा
    creds_json = os.environ.get('GOOGLE_CREDS')
    
    if not creds_json:
        print("ERROR: GOOGLE_CREDS variable not found in Render settings!")
        return None
    
    try:
        # डेटा को साफ़ करके लोड करना
        creds_dict = json.loads(creds_json.strip())
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)
    except Exception as e:
        print(f"Auth Error: {e}")
        return None


# 2. Main Page Route (यह गायब था, इसलिए Not Found आ रहा था)
@app.route('/')
def index():
    try:
        client = get_gspread_client()
        if not client:
            return "Error: Database connection failed."
        sheet = client.open("Geetai_Villa_Admin").sheet1
        villas = sheet.get_all_records()
        return render_template('index.html', villas=villas)
    except Exception as e:
        return f"Error loading index: {str(e)}"

# 3. Villa Details Route
@app.route('/villa/<villa_id>')
def villa_details(villa_id):
    try:
        client = get_gspread_client()
        sheet = client.open("Geetai_Villa_Admin").sheet1
        villas = sheet.get_all_records()
        villa = next((v for v in villas if str(v['Villa_ID']) == villa_id), None)
        
        if villa:
            return render_template('villa_details.html', villa=villa)
        return "Villa Not Found", 404
    except Exception as e:
        return f"Error loading details: {str(e)}"

# 4. Inquiry Form Route
@app.route('/submit_inquiry', methods=['POST'])
def submit_inquiry():
    try:
        name = request.form.get('name')
        phone = request.form.get('phone')
        message = request.form.get('message')
        today = str(datetime.date.today())

        client = get_gspread_client()
        inquiry_sheet = client.open("Geetai_Villa_Admin").worksheet("Inquiries")
        inquiry_sheet.append_row([name, phone, message, today])

        return "<h1>Success!</h1><p>Redirecting to WhatsApp...</p><script>setTimeout(function(){ window.location.href='/'; }, 3000);</script>"
    except Exception as e:
        return f"Form Error: {str(e)}"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
    
