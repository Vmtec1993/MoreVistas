import os
import json
import gspread
from flask import Flask, render_template
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)

# --- Google Sheets Setup ---
def get_sheet_data():
    try:
        creds_json = os.environ.get('GOOGLE_CREDS')
        if not creds_json:
            return []
        info = json.loads(creds_json)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(info, scope)
        client = gspread.authorize(creds)
        # अपनी शीट ID यहाँ पक्का करें
        sheet = client.open_by_key("1wXlMNAUuW2Fr4L05ahxvUNn0yvMedcVosTRJzZf_1ao").sheet1
        data = sheet.get_all_records()
        
        # फोटो कॉलम फिक्स (Image_Main या Image_Link में से जो मिले)
        for row in data:
            row['display_image'] = row.get('Image_Main') or row.get('Image_Link') or ""
        return data
    except Exception as e:
        print(f"Sheet Error: {e}")
        return []

@app.route('/')
@app.route('/gallery')
def gallery_main():
    villas = get_sheet_data()
    return render_template('gallery.html', villas=villas)

@app.route('/gallery/<villa_slug>')
def villa_gallery(villa_slug):
    all_data = get_sheet_data()
    # विला नाम को बिना स्पेस के मैच करना
    villa_photos = [v for v in all_data if v.get('Name', '').lower().replace(' ', '') == villa_slug.lower()]
    
    if villa_photos:
        v_name = villa_photos[0].get('Name', 'Our Villa')
        return render_template('villa_gallery.html', photos=villa_photos, villa_name=v_name)
    
    return "Villa Not Found", 404

if __name__ == '__main__':
    # Render के लिए पोर्ट बाइंडिंग (0.0.0.0 अनिवार्य है)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
