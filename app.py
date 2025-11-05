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

# --- Database Setup (No Change) ---
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
            source TEXT,  /* New: 'IP' or 'GPS' */
            user_agent TEXT
        )
    """)
    conn.commit()
    conn.close()

# --- Database Logging Function (Updated with 'source') ---
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
        
        # NOTE: Updated column list to include 'source'
        cursor.execute("""
            INSERT INTO clicks (timestamp, ip_address, country, city, latitude, longitude, source, user_agent) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, data)
        
        conn.commit()
        conn.close()
        print(f"--- LOGGED ({source}) --- IP: {ip} | Loc: {location.get('city', 'N/A')}, {location.get('country', 'N/A')} | Coords: {location.get('latitude')}")
        
    except sqlite3.Error as e:
        print(f"SQLite error during logging: {e}")


# --- 1. Main Link Click (Entry Point) ---
# The user's link will point here. Instead of redirecting, it asks for location.
@app.route('/track_click')
def track_click():
    # Capture IP and user agent immediately
    user_ip = request.remote_addr 
    user_agent = request.headers.get('User-Agent', 'Unknown')
    
    # Store these in Flask session or pass as query params (we pass as query for simplicity)
    # Redirect to the page that requests GPS location via JavaScript
    return redirect(f"/request_location?ip={user_ip}&ua={user_agent}")


# --- 2. Location Request Page (Serves HTML with JS) ---
# This is the page where the user sees the "Share Location?" pop-up.
@app.route('/request_location')
def request_location():
    # Pass the IP and User Agent data through to the JavaScript success/error paths
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

    # Log the precise GPS data
    log_click_data(ip, location_data, ua, source="GPS")

    # This is where you would integrate the location data with your service.
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
    
    # Redirect to the standard destination
    return redirect(FINAL_DESTINATION_URL)


# --- 5. View Logs (Added 'source' column) ---
@app.route('/view_logs')
def view_logs():
    if not os.path.exists(DATABASE_FILE):
        return render_template_string("<h1>Logs</h1><p>Database file not found.</p>")

    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    # NOTE: Select statement updated to include 'source'
    cursor.execute("SELECT id, timestamp, ip_address, country, city, latitude, longitude, source, user_agent FROM clicks ORDER BY timestamp DESC")
    logs = cursor.fetchall()
    conn.close()

    html = "<h1>Click Tracking Logs</h1><table border='1' style='width: 100%;'><tr><th>ID</th><th>Time</th><th>IP</th><th>Country</th><th>City</th><th>Lat</th><th>Lon</th><th>Source</th><th>User Agent</th></tr>"
    for row in logs:
        ua_display = row[8][:50] + '...' if len(row[8]) > 50 else row[8]
        html += f"<tr><td>{row[0]}</td><td>{row[1]}</td><td>{row[2]}</td><td>{row[3]}</td><td>{row[4]}</td><td>{row[5]}</td><td>{row[6]}</td><td>{row[7]}</td><td>{ua_display}</td></tr>"
    html += "</table>"
    return render_template_string(html)


# --- Debugging Route (No Change) ---
@app.route('/test_ip_lookup', methods=['GET', 'POST'])
def test_ip_lookup():
    # ... (code from previous response, uses ip_locator.py)
    # NOTE: Omitted for brevity, include the full version from previous responses
    # ...
    return render_template_string("<h1>Test IP Lookup</h1>...")


if __name__ == '__main__':
    # Initialize the database and create a 'templates' folder if it doesn't exist
    init_db() 
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    print("\n" + "="*50)
    print("--- Flask GPS/IP Geolocation Tracker Running ---")
    print(f"Tracking Link: http://127.0.0.1:5000/track_click")
    print(f"*** REQUIRES HTTPS & DEPLOYMENT FOR GPS TO WORK ***")
    print("="*50 + "\n")
    app.run(debug=True, host='127.0.0.1', port=5000)