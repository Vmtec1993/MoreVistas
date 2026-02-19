import os
import random
import json
from flask import Flask, render_template, request
import gspread
from google.oauth2.service_account import Credentials

app = Flask(__name__)

def get_sheets_data():
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        
        # 1. Check if file exists
        if not os.path.exists("credentials.json"):
            print("DEBUG: credentials.json file NOT FOUND in GitHub repository!")
            return []

        # 2. Try to Load Credentials
        creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
        client = gspread.authorize(creds)
        
        # 3. Check Sheet Name (Ensure it matches exactly)
        sheet_name = "Geetai_Villa_Data" 
        spreadsheet = client.open(sheet_name)
        sheet = spreadsheet.get_worksheet(0)
        
        data = sheet.get_all_records()
        print(f"DEBUG: Success! Found {len(data)} rows.")
        return data

    except Exception as e:
        print(f"DEBUG ERROR: {str(e)}")
        return []

@app.route('/')
def index():
    villas = get_sheets_data()
    
    # Fallback if sheet fails (To check if site is live)
    if not villas:
        villas = [{
            "Villa_ID": 1, 
            "Name": "Sheet Not Connected Yet", 
            "BHK": "Check Credentials", 
            "Price": "0", 
            "Rating": 0.0,
            "Image_Main": "https://via.placeholder.com/800x400?text=Check+Render+Logs+for+Error"
        }]
        
    return render_template('index.html', villas=villas)

@app.route('/villa/<int:villa_id>')
def villa_details(villa_id):
    villas = get_sheets_data()
    villa = next((v for v in villas if v.get('Villa_ID') == villa_id), None)
    if not villa:
        return "Villa not found or sheet error", 404
    return render_template('villa_details.html', villa=villa)

if __name__ == '__main__':
    app.run(debug=True)
