import os
import json
import gspread
from flask import Flask, render_template, request, redirect, url_for, session
from oauth2client.service_account import ServiceAccountCredentials
import requests
from datetime import datetime

app = Flask(__name__)
app.secret_key = "morevistas_admin_secure_key_2026" 

# --- Google Sheets Setup ---
creds_json = os.environ.get('GOOGLE_CREDS')
sheet = None
enquiry_sheet = None
places_sheet = None 

if creds_json:
    try:
        info = json.loads(creds_json)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(info, scope)
        client = gspread.authorize(creds)
        
        SHEET_ID = "1wXlMNAUuW2Fr4L05ahxvUNn0yvMedcVosTRJzZf_1ao"
        main_spreadsheet = client.open_by_key(SHEET_ID)
        sheet = main_spreadsheet.sheet1  # Villas Data
        
        try:
            enquiry_sheet = main_spreadsheet.worksheet("Enquiries")
        except:
            enquiry_sheet = sheet

        try:
            places_sheet = main_spreadsheet.worksheet("Places")
        except:
            places_sheet = None

    except Exception as e:
        print(f"Sheet Error: {e}")

# --- Telegram Setup ---
TELEGRAM_TOKEN = "7913354522:AAH1XxMP1EMWC59fpZezM8zunZrWQcAqH18"
TELEGRAM_CHAT_ID = "6746178673"

def send_telegram_alert(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        params = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        requests.get(url, params=params, timeout=10)
    except: pass

# --- ✅ Live Weather Fetch Function ---
def get_lonavala_weather():
    try:
        api_key = "b8ee20104f767837862a93361e68787c" 
        url = f"https://api.openweathermap.org/data/2.5/weather?q=Lonavala&units=metric&appid={api_key}"
        data = requests.get(url, timeout=5).json()
        return {
            'temp': round(data['main']['temp']),
            'desc': data['weather'][0]['description'].title(),
            'icon': data['weather'][0]['icon']
        }
    except:
        return None

# --- Routes ---

@app.route('/')
def index():
    weather_data = get_lonavala_weather()
    villas = []
    if sheet:
        try:
            # head=1 ensures we read headers correctly even if sheet has issues
            villas = sheet.get_all_records(head=1)
            for v in villas:
                v['Status'] = v.get('Status', 'Available')
        except Exception as e:
            print(f"Data Fetch Error: {e}")
    return render_template('index.html', villas=villas, weather=weather_data)

@app.route('/explore-lonavala')
def explore_lonavala():
    places = []
    if places_sheet:
        try:
            places = places_sheet.get_all_records(head=1)
        except Exception as e:
            print(f"Places Fetch Error: {e}")
    return render_template('explore.html', places=places)

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        user = request.form.get('username')
        pwd = request.form.get('password')
        if user == "admin" and pwd == "MoreVistas@2026":
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            error = "Invalid Username or Password!"
    return render_template('admin_login.html', error=error)

@app.route('/admin-dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    enquiries = []
    villas = []
    if sheet:
        villas = sheet.get_all_records(head=1)
    if enquiry_sheet:
        enquiries = enquiry_sheet.get_all_records(head=1)
        enquiries.reverse()
        
    return render_template('admin_dashboard.html', enquiries=enquiries, villas=villas)

@app.route('/update-status/<villa_id>/<new_status>')
def update_villa_status(villa_id, new_status):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    if sheet:
            
