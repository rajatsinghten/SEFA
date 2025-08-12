#!/usr/bin/env python3
"""
Debug script to test Microsoft Graph API token and permissions
"""
import json
import base64
import requests
from utils.auth import get_token_from_cache, load_credentials

def decode_jwt_payload(token):
    """Decode JWT payload to see what scopes are included"""
    try:
        # JWT tokens have 3 parts separated by dots
        parts = token.split('.')
        if len(parts) != 3:
            return None
            
        # Add padding if needed
        payload = parts[1]
        payload += '=' * (4 - len(payload) % 4)
        
        # Decode base64
        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)
    except Exception as e:
        print(f"Error decoding token: {e}")
        return None

def test_token_permissions(user_id):
    """Test what permissions the current token has"""
    print("\n" + "="*50)
    print("MICROSOFT GRAPH TOKEN DEBUG")
    print("="*50)
    
    # Get the token
    token = get_token_from_cache(user_id)
    if not token:
        print("❌ No token available")
        return
    
    print(f"✅ Token obtained (length: {len(token)} chars)")
    
    # Decode the token to see what's in it
    payload = decode_jwt_payload(token)
    if payload:
        print(f"\n📋 Token Details:")
        print(f"   Audience (aud): {payload.get('aud', 'Not found')}")
        print(f"   Issuer (iss): {payload.get('iss', 'Not found')}")
        print(f"   Subject (sub): {payload.get('sub', 'Not found')}")
        print(f"   App ID (appid): {payload.get('appid', 'Not found')}")
        print(f"   Scopes (scp): {payload.get('scp', 'Not found')}")
        print(f"   Roles: {payload.get('roles', 'Not found')}")
        
        # Check expiration
        import time
        exp = payload.get('exp')
        if exp:
            current_time = int(time.time())
            time_left = exp - current_time
            if time_left > 0:
                print(f"   Expires in: {time_left} seconds ({time_left/3600:.1f} hours)")
            else:
                print(f"   ⚠️  Token EXPIRED {-time_left} seconds ago!")
    
    # Test basic Microsoft Graph API endpoints
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Test 1: Get user profile (should work with User.Read)
    print(f"\n🔍 Testing User Profile Access...")
    try:
        response = requests.get('https://graph.microsoft.com/v1.0/me', headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            user_data = response.json()
            print(f"   ✅ User: {user_data.get('displayName', 'Unknown')} ({user_data.get('userPrincipalName', 'Unknown')})")
        else:
            print(f"   ❌ Error: {response.text}")
    except Exception as e:
        print(f"   ❌ Exception: {e}")
    
    # Test 2: Get mailbox (requires Mail.Read)
    print(f"\n📧 Testing Mail Access...")
    try:
        response = requests.get('https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages?$top=1', headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            mail_data = response.json()
            email_count = len(mail_data.get('value', []))
            print(f"   ✅ Mail access successful (found {email_count} recent emails)")
        else:
            print(f"   ❌ Error: {response.text}")
    except Exception as e:
        print(f"   ❌ Exception: {e}")
    
    # Test 3: Get calendar (requires Calendars.Read)
    print(f"\n📅 Testing Calendar Access...")
    try:
        response = requests.get('https://graph.microsoft.com/v1.0/me/events?$top=1', headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            calendar_data = response.json()
            event_count = len(calendar_data.get('value', []))
            print(f"   ✅ Calendar access successful (found {event_count} recent events)")
        else:
            print(f"   ❌ Error: {response.text}")
    except Exception as e:
        print(f"   ❌ Exception: {e}")
    
    # Show raw token data
    print(f"\n📄 Raw Token Data:")
    creds = load_credentials(user_id)
    if creds:
        print(f"   Has access_token: {'access_token' in creds}")
        print(f"   Has refresh_token: {'refresh_token' in creds}")
        print(f"   Token type: {creds.get('token_type', 'Unknown')}")
        print(f"   Scope in response: {creds.get('scope', 'Unknown')}")
    
    print("\n" + "="*50)
    print("END TOKEN DEBUG")
    print("="*50)

if __name__ == "__main__":
    # You need to provide your user_id here
    # Check your terminal output or session to find it
    user_id = "181d7dda-2898-4e2a-882b-7fc1338b6f11"  # From your logs
    test_token_permissions(user_id)
