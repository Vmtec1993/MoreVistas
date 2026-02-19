import os
import json
from flask import Flask, render_template
import gspread
from google.oauth2.service_account import Credentials

app = Flask(__name__)

def get_sheets_data():
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds_json = os.environ.get("GOOGLE_CREDS")
        
        if not creds_json:
            print("DEBUG: GOOGLE_CREDS is missing in Environment Variables")
            return []

        # JSON क्लीनिंग: कभी-कभी पेस्ट करते समय शुरुआत/अंत में फालतू कोट्स आ जाते हैं
        creds_json = creds_json.strip()
        if creds_json.startswith("'") and creds_json.endswith("'"):
            creds_json = creds_json[1:-1]
        
        info = json.loads(creds_json)
        
        # Private key की नई लाइन फिक्स करना
        if "private_key" in info:
            info["private_key"] = info["private_key"].replace("\\n", "\n")
        
        creds = Credentials.from_service_account_info(info, scopes=scopes)
        client = gspread.authorize(creds)
        
        spreadsheet = client.open("Geetai_Villa_Data")
        sheet = spreadsheet.get_worksheet(0)
        return sheet.get_all_records()

    except Exception as e:
        print(f"FINAL DEBUG ERROR: {str(e)}")
        return []

@app.route('/')
def index():
    villas = get_sheets_data()
    return render_template('index.html', villas=villas)

@app.route('/villa/<int:villa_id>')
def villa_details(villa_id):
    villas = get_sheets_data()
    villa = next((v for v in villas if v.get('Villa_ID') == villa_id), None)
    if not villa: return "Villa not found", 404
    return render_template('villa_details.html', villa=villa)

if __name__ == '__main__':
    # रेंडर के लिए पोर्ट सेट करना
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

    
