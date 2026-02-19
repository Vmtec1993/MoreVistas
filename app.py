import os
import random
from flask import Flask, render_template, request
import gspread
from google.oauth2.service_account import Credentials

app = Flask(__name__)

def get_sheets_data():
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        # credentials.json check
        if os.path.exists("credentials.json"):
            creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
            client = gspread.authorize(creds)
            # Apni sheet ka naam yahan sahi karein
            sheet = client.open("Geetai_Villa_Data").get_worksheet(0)
            return sheet.get_all_records()
    except Exception as e:
        print(f"Sheet Sync Error: {e}")
    return []

@app.route('/')
def index():
    villas = get_sheets_data()
    
    # AGAR DATA NAHI MILA TO YE DUMMY DATA DIKHEGA (TAKKI SITE KHALI NA LAGE)
    if not villas:
        villas = [{
            "Villa_ID": 1, 
            "Name": "Geetai Premium Villa", 
            "BHK": "4 BHK", 
            "Price": "12,000", 
            "Rating": 4.9,
            "Image_Main": "https://images.unsplash.com/photo-1580587771525-78b9dba3b914?auto=format&fit=crop&w=800"
        }]
        
    return render_template('index.html', villas=villas)

@app.route('/villa/<int:villa_id>')
def villa_details(villa_id):
    villas = get_sheets_data()
    villa = next((v for v in villas if v.get('Villa_ID') == villa_id), None)
    if not villa:
        # Fallback for dummy villa
        villa = {"Villa_ID": 1, "Name": "Geetai Premium Villa", "BHK": "4 BHK", "Price": "12,000", "Rating": 4.9, "Description": "Luxury stay in Lonavala.", "Image_Main": "https://images.unsplash.com/photo-1580587771525-78b9dba3b914?auto=format&fit=crop&w=800"}
    return render_template('villa_details.html', villa=villa)

@app.route('/inquiry')
def inquiry():
    return render_template('inquiry.html')

if __name__ == '__main__':
    app.run(debug=True)
    
