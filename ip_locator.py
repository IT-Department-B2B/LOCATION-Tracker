# ip_locator.py (Final Version)

import requests

def get_location_from_ip(ip_address):
    # If testing locally, use a known public IP for the lookup test
    if ip_address == '127.0.0.1' or ip_address.startswith('192.168.'):
        ip_address = "8.8.8.8" # Use Google DNS for a guaranteed lookup

    url = f"http://ip-api.com/json/{ip_address}"
    
    try:
        response = requests.get(url, timeout=5) 
        response.raise_for_status() 
        data = response.json()
        
        if data and data.get('status') == 'success':
            return {
                "country": data.get('country'),
                "city": data.get('city'),
                "latitude": data.get('lat'),
                "longitude": data.get('lon'),
                "isp": data.get('isp')
            }
        else:
            return None
            
    except requests.exceptions.RequestException:
        return None