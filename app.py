import os
import json
from flask import Flask, render_template
import gspread
from google.oauth2.service_account import Credentials

app = Flask(__name__)

def get_sheets_data():
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds_raw = os.environ.get("GOOGLE_CREDS")
        
        if not creds_raw: return []

        # सफाई: शुरुआत और अंत के फालतू हिस्से हटाना
        creds_raw = creds_raw.strip().strip("'").strip('"')
        
        # अगर गलती से दो JSON चिपक गए हों, तो पहले वाले को ही उठाना
        if creds_raw.count('{') > 1:
            creds_raw = creds_raw.split('}{')[0] + '}'
            
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
        # अब एरर मैसेज और भी साफ दिखेगा
        return [{"Name": f"Final Step: {str(e)}", "Price": "Fix JSON in Render"}]

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
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
    
