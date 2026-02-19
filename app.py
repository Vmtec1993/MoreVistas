import json
import os

# Google Sheets Setup (नया तरीका)
def get_sheets_data():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        # यहाँ हम फाइल के बजाय Environment Variable का इस्तेमाल कर रहे हैं
        creds_json = os.environ.get("GOOGLE_CREDS")
        if creds_json:
            creds_dict = json.loads(creds_json)
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        else:
            # बैकअप के लिए पुराना तरीका अगर फाइल मौजूद हो
            creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
            
        client = gspread.authorize(creds)
        sheet = client.open("Geetai_Villa_Data").get_all_records()
        return sheet
    except Exception as e:
        print(f"Error: {e}")
        return []
        
