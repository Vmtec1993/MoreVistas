import os, json, gspread
from flask import Flask, render_template, request, session, redirect, url_for
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)
app.secret_key = "morevistas_final_2026"

# --- CONFIG ---
ADMIN_PASSWORD = "MoreVistas@2026"
SHEET_ID = "1wXlMNAUuW2Fr4L05ahxvUNn0yvMedcVosTRJzZf_1ao"

def get_master_data(tab_name):
    try:
        creds_json = os.environ.get('GOOGLE_CREDS')
        info = json.loads(creds_json)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(info, scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SHEET_ID).worksheet(tab_name)
        data = sheet.get_all_values()
        if not data or len(data) <= 1: return []
        headers = [h.strip() for h in data[0]]
        return [dict(zip(headers, row)) for row in data[1:] if any(row)]
    except: return []

def get_settings():
    res = {'Banner_Status': 'OFF', 'Contact': '8830024994', 'Logo_Height': '60', 'Logo_URL': ''}
    try:
        data = get_master_data("Settings")
        for item in data:
            cols = list(item.values())
            if len(cols) >= 2: res[str(cols[0]).strip()] = str(cols[1]).strip()
    except: pass
    return res

@app.route('/')
def index():
    return render_template('index.html', villas=get_master_data("Villas"), settings=get_settings(), tourist_places=get_master_data("Places"))

@app.route('/privacy-policy')
def privacy_policy(): return render_template('privacy_policy.html', settings=get_settings())

@app.route('/terms-conditions')
def terms_conditions(): return render_template('terms_conditions.html', settings=get_settings())

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'): return redirect(url_for('admin_login'))
    return render_template('admin_dashboard.html', enquiries=get_master_data("Enquiries"))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
    
