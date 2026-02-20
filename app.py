import os
import json
import gspread
from flask import Flask, render_template, request
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)

# --- Google Sheets Setup ---
def get_sheet_data():
    try:
        creds_json = os.environ.get('GOOGLE_CREDS')
        if not creds_json: return []
        info = json.loads(creds_json)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(info, scope)
        client = gspread.authorize(creds)
        # आपकी शीट ID
        sheet = client.open_by_key("1wXlMNAUuW2Fr4L05ahxvUNn0yvMedcVosTRJzZf_1ao").sheet1
        data = sheet.get_all_records()
        
        # फोटो कॉलम को फिक्स करना
        for row in data:
            row['display_image'] = row.get('Image_Main') or row.get('Image_Link')
        return data
    except Exception as e:
        print(f"Error: {e}")
        return []

@app.route('/gallery')
def gallery_main():
    villas = get_sheet_data()
    return render_template('gallery.html', villas=villas)

@app.route('/gallery/<villa_slug>')
def villa_gallery(villa_slug):
    all_data = get_sheet_data()
    # विला के नाम से फोटो फिल्टर करना
    villa_photos = [v for v in all_data if v.get('Name', '').lower().replace(' ', '') == villa_slug.lower()]
    
    if villa_photos:
        v_name = villa_photos[0].get('Name', 'Our Villa')
        # यह लाइन 'villa_gallery.html' फाइल को ढूंढती है
        return render_template('villa_gallery.html', photos=villa_photos, villa_name=v_name)
    return "Villa Not Found", 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
