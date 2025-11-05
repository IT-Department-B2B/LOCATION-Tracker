# ip_locator.py

import requests

def get_location_from_ip(ip_address):
    """
    Fetches the general geographic location (city, country) 
    from an IP address using a public API.
    """
    # Using a free service for demonstration (check their usage limits)
    url = f"http://ip-api.com/json/{ip_address}"
    
    try:
        response = requests.get(url, timeout=5) # Added a timeout for safety
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
            # Handle API failure or rate limiting
            print(f"Geolocation API failed for IP {ip_address}: {data.get('message', 'Unknown error')}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"An error occurred during the API request: {e}")
        return None

# Simple test to verify the function works
if __name__ == '__main__':
    # Using a test IP (Google DNS)
    test_ip = "8.8.8.8"
    location = get_location_from_ip(test_ip)
    print(f"Test IP {test_ip} location: {location}")