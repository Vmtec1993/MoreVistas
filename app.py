import os
import json
from flask import Flask, render_template, request, redirect, url_for
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Gunicorn को इस 'app' वेरिएबल की सख्त ज़रूरत होती है
app = Flask(__name__)

def get_sheets_data():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        # Render की Environment Setting से JSON उठाना
        creds_json = os.environ.get("GOOGLE_CREDS")
        
        if creds_json:
            # अगर Render में JSON डेटा मिल गया
            creds_dict = json.loads(creds_json)
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        else:
            # अगर आप कभी कंप्यूटर पर चलाएं, तो फाइल ढूंढेगा
            creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
            
        client = gspread.authorize(creds)
        sheet = client.open("Geetai_Villa_Data").get_all_records()
        return sheet
    except Exception as e:
        print(f"Error connecting to Google Sheets: {e}")
        return []

@app.route('/')
def index():
    villas = get_sheets_data()
    return render_template('index.html', villas=villas)

@app.route('/villa/<villa_id>')
def villa_details(villa_id):
    villas = get_sheets_data()
    villa = next((v for v in villas if str(v.get('Villa_ID', '')) == str(villa_id)), None)
    if not villa:
        return "Villa Not Found", 404
    return render_template('villa_details.html', villa=villa)

@app.route('/enquiry/<villa_id>')
def enquiry(villa_id):
    # इसमें भी विला डेटा पास करना ताकि नाम दिख सके
    villas = get_sheets_data()
    villa = next((v for v in villas if str(v.get('Villa_ID', '')) == str(villa_id)), None)
    return render_template('enquiry.html', villa=villa)

@app.route('/submit_enquiry', methods=['POST'])
def submit_enquiry():
    return redirect(url_for('success'))

@app.route('/success')
def success():
    return render_template('success.html')

if __name__ == '__main__':
    import os
    # Render को पोर्ट बताने के लिए यह लाइन बहुत ज़रूरी है
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

    
