#!/usr/bin/env python3
"""
More detailed API testing to understand the 401 errors
"""
import json
import requests
from utils.auth import get_token_from_cache

def detailed_api_test(user_id):
    """Test API calls with detailed error information"""
    token = get_token_from_cache(user_id)
    if not token:
        print("❌ No token available")
        return
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    print("Testing different API endpoints...")
    
    # Test different mail endpoints
    mail_endpoints = [
        'https://graph.microsoft.com/v1.0/me/mailFolders',
        'https://graph.microsoft.com/v1.0/me/mailFolders/inbox',
        'https://graph.microsoft.com/v1.0/me/messages?$top=1',
        'https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages?$top=1'
    ]
    
    for endpoint in mail_endpoints:
        print(f"\n📧 Testing: {endpoint}")
        try:
            response = requests.get(endpoint, headers=headers)
            print(f"   Status: {response.status_code}")
            
            if response.status_code != 200:
                # Try to get detailed error information
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Error (raw): {response.text}")
                    
                # Check response headers for more info
                if 'www-authenticate' in response.headers:
                    print(f"   WWW-Authenticate: {response.headers['www-authenticate']}")
                if 'x-ms-diagnostics' in response.headers:
                    print(f"   X-MS-Diagnostics: {response.headers['x-ms-diagnostics']}")
            else:
                print(f"   ✅ Success!")
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")
    
    # Test calendar endpoints
    calendar_endpoints = [
        'https://graph.microsoft.com/v1.0/me/calendars',
        'https://graph.microsoft.com/v1.0/me/calendar',
        'https://graph.microsoft.com/v1.0/me/events?$top=1'
    ]
    
    for endpoint in calendar_endpoints:
        print(f"\n📅 Testing: {endpoint}")
        try:
            response = requests.get(endpoint, headers=headers)
            print(f"   Status: {response.status_code}")
            
            if response.status_code != 200:
                # Try to get detailed error information
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Error (raw): {response.text}")
                    
                # Check response headers for more info
                if 'www-authenticate' in response.headers:
                    print(f"   WWW-Authenticate: {response.headers['www-authenticate']}")
                if 'x-ms-diagnostics' in response.headers:
                    print(f"   X-MS-Diagnostics: {response.headers['x-ms-diagnostics']}")
            else:
                print(f"   ✅ Success!")
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")

if __name__ == "__main__":
    user_id = "181d7dda-2898-4e2a-882b-7fc1338b6f11"
    detailed_api_test(user_id)
