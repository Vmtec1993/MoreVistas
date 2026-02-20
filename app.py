import os
import gspread
from flask import Flask, render_template, request, redirect, url_for
from oauth2client.service_account import ServiceAccountCredentials
import requests  # टेलीग्राम मैसेज भेजने के लिए

app = Flask(__name__)

# --- Google Sheets Setup ---
# पक्का करें कि आपकी 'credentials.json' फाइल GitHub में मौजूद है
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

# अपनी Google Sheet का नाम यहाँ लिखें
sheet = client.open("Villas_Data").sheet1  # Sheet1 का डेटा (Villas List)
enquiry_sheet = client.open("Villas_Data").get_worksheet(1)  # दूसरी शीट (Enquiries)

# --- Telegram Config ---
TELEGRAM_TOKEN = "7913354522:AAH1XxMP1EMWC59fpZezM8zunZrWQcAqH18"
TELEGRAM_CHAT_ID = "6746178673"

def send_telegram_alert(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        requests.post(url, data=payload)
    except Exception as e:
        print(f"Telegram Alert Error: {e}")

# --- Routes ---

@app.route('/')
def index():
    # Google Sheet से सभी विला का डेटा लाना
    villas = sheet.get_all_records()
    return render_template('index.html', villas=villas)

@app.route('/villa/<villa_id>')
def villa_details(villa_id):
    villas = sheet.get_all_records()
    # ID के आधार पर सही विला चुनना
    villa = next((v for v in villas if str(v['Villa_ID']) == str(villa_id)), None)
    if villa:
        return render_template('villa_details.html', villa=villa)
    return "Villa not found", 404

@app.route('/enquiry/<villa_id>', methods=['GET', 'POST'])
def enquiry(villa_id):
    if request.method == 'POST':
        # फॉर्म से डेटा लेना
        name = request.form.get('name')
        phone = request.form.get('phone')
        checkin = request.form.get('checkin')
        checkout = request.form.get('checkout')
        guests = request.form.get('guests')

        # Google Sheet (Enquiries वाली शीट) में सेव करना
        try:
            enquiry_sheet.append_row([villa_id, name, phone, checkin, checkout, guests])
        except:
            # अगर दूसरी शीट नहीं है, तो पहली में ही नीचे डाल देगा
            sheet.append_row([f"ENQ-{villa_id}", name, phone, checkin, checkout, guests])

        # --- टेलीग्राम पर तुरंत अलर्ट भेजना ---
        alert_msg = (
            f"🔔 *New Villa Enquiry!*\n\n"
            f"🏡 *Villa ID:* {villa_id}\n"
            f"👤 *Customer:* {name}\n"
            f"📞 *Phone:* {phone}\n"
            f"📅 *Check-in:* {checkin}\n"
            f"📅 *Check-out:* {checkout}\n"
            f"👥 *Total Guests:* {guests}\n\n"
            f"✅ *Please contact the customer soon!*"
        )
        send_telegram_alert(alert_msg)

        return render_template('success.html')
    
    return render_template('enquiry.html', villa_id=villa_id)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
    
