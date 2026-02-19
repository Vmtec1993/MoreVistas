import os
import json
from flask import Flask, render_template
import gspread
from google.oauth2.service_account import Credentials

app = Flask(__name__)

def get_sheets_data():
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        # credentials.json फाइल को सुरक्षित तरीके से लोड करना
        if os.path.exists("credentials.json"):
            with open("credentials.json", "r") as f:
                info = json.load(f)
            
            # Invalid JWT Signature से बचने के लिए private_key को साफ करना
            if "private_key" in info:
                info["private_key"] = info["private_key"].replace("\\n", "\n")
            
            creds = Credentials.from_service_account_info(info, scopes=scopes)
            client = gspread.authorize(creds)
            
            # अपनी गूगल शीट का नाम यहाँ चेक करें
            spreadsheet = client.open("Geetai_Villa_Data")
            sheet = spreadsheet.get_worksheet(0)
            return sheet.get_all_records()
    except Exception as e:
        # रेंडर के लॉग्स में अब असली वजह साफ़ दिखेगी
        print(f"SHEET CONNECTION ERROR: {str(e)}")
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
    app.run(debug=True)
    
