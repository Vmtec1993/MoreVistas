import os
import json
from flask import Flask, render_template
import gspread
from google.oauth2.service_account import Credentials

app = Flask(__name__)

def get_sheets_data():
    try:
        # यहाँ हमने 'drive' वाला स्कोप बढ़ा दिया है, जो 403 एरर को खत्म करेगा
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        creds_raw = os.environ.get("GOOGLE_CREDS")
        if not creds_raw: return []

        creds_raw = creds_raw.strip().strip("'").strip('"')
        info = json.loads(creds_raw)
        
        if "private_key" in info:
            info["private_key"] = info["private_key"].replace("\\n", "\n")
            
        creds = Credentials.from_service_account_info(info, scopes=scopes)
        client = gspread.authorize(creds)
        
        # शीट का नाम पक्का करें
        spreadsheet = client.open("Geetai_Villa_Data")
        sheet = spreadsheet.get_worksheet(0)
        return sheet.get_all_records()
    except Exception as e:
        return [{"Name": f"Almost There: {str(e)}", "Price": "Checking Permission"}]

@app.route('/')
def index():
    villas = get_sheets_data()
    return render_template('index.html', villas=villas)

@@app.route('/villa/<villa_id>')
def villa_details(villa_id):
    villas = get_sheets_data()
    # यहाँ हम दोनों को String में बदलकर मैच करेंगे ताकि गलती की गुंजाइश न रहे
    villa = next((v for v in villas if str(v.get('Villa_ID', '')) == str(villa_id)), None)
    
    if not villa:
        return "<h1>Villa not found!</h1><p>ID: " + str(villa_id) + " does not match any villa.</p><a href='/'>Back to Home</a>", 404
        
    return render_template('villa_details.html', villa=villa)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
    
