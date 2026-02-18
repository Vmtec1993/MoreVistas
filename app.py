import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from flask import Flask, render_template

app = Flask(__name__)

def get_villas():
    # सुरक्षा के लिए हम Environment Variable का इस्तेमाल करेंगे
    # अगर फाइल नहीं मिलती तो यह Vercel की सेटिंग्स से डेटा उठाएगा
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # यह हिस्सा GitHub/Vercel के लिए है
    creds_json = os.environ.get('GOOGLE_CREDS')
    if creds_json:
        creds_dict = json.loads(creds_json)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    else:
        # यह आपके लोकल कंप्यूटर पर टेस्टिंग के लिए है
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    
    client = gspread.authorize(creds)
    sheet = client.open("Geetai_Villa_Admin").sheet1
    return sheet.get_all_records()

@app.route('/')
def index():
    try:
        villas = get_villas()
        return render_template('index.html', villas=villas)
    except Exception as e:
        return f"Error: {e}"

@app.route('/villa/<villa_id>')
def villa_details(villa_id):
    all_villas = get_villas()
    villa = next((v for v in all_villas if str(v['Villa_ID']) == villa_id), None)
    if villa:
        return render_template('villa_details.html', villa=villa)
    return "Villa not found!", 404

if __name__ == "__main__":
    app.run(debug=True)
    
