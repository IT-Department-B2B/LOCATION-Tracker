# ip_locator.py

import requests

def get_location_from_ip(ip_address):
    url = f"http://ip-api.com/json/{ip_address}"
    
    try:
        # Added timeout to prevent process hanging
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

if __name__ == '__main__':
    # Test with Google DNS
    test_ip = "8.8.8.8"
    location = get_location_from_ip(test_ip)
    print(f"Test IP {test_ip} location: {location}")