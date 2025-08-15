# backend/utils/auth.py
import os
import json
import jwt
import base64
from pathlib import Path
from functools import wraps
from flask import session, jsonify, request, redirect, url_for
from cryptography.fernet import Fernet
import msal

from config import CLIENT_ID, CLIENT_SECRET, AUTHORITY, SCOPES, TOKENS_DIR, KEY_FILE, REDIRECT_PATH

# Ensure the tokens directory exists
Path(TOKENS_DIR).mkdir(exist_ok=True)

# Initialize the encryption cipher
if not os.path.exists(KEY_FILE):
    key = Fernet.generate_key()
    with open(KEY_FILE, 'wb') as f:
        f.write(key)
else:
    with open(KEY_FILE, 'rb') as f:
        key = f.read()

cipher = Fernet(key)

def debug_token_claims(access_token):
    """Debug function to decode and display token claims without verification."""
    try:
        print("\n====== TOKEN DEBUGGING ======")
        # Decode without verification to see claims
        decoded = jwt.decode(access_token, options={"verify_signature": False})
        print("Token claims:")
        print(json.dumps(decoded, indent=2))
        
        # Check specific claims
        print(f"\nScopes (scp): {decoded.get('scp', 'No scp claim found')}")
        print(f"Roles: {decoded.get('roles', 'No roles claim found')}")
        print(f"App ID (appid): {decoded.get('appid', 'No appid claim found')}")
        print(f"Tenant ID (tid): {decoded.get('tid', 'No tid claim found')}")
        print(f"User Principal Name (upn): {decoded.get('upn', 'No upn claim found')}")
        print(f"Audience (aud): {decoded.get('aud', 'No aud claim found')}")
        print(f"Issuer (iss): {decoded.get('iss', 'No iss claim found')}")
        
        # Check expiration
        import time
        current_time = int(time.time())
        exp = decoded.get('exp', 0)
        if exp:
            time_left = exp - current_time
            if time_left > 0:
                print(f"Token expires in {time_left} seconds ({time_left/3600:.1f} hours)")
            else:
                print(f"Token expired {-time_left} seconds ago")
        
        print("==============================\n")
        return decoded
        
    except Exception as e:
        print(f"Error decoding token: {e}")
        print("This might be because the token is not a JWT or is malformed.")
        # Try to inspect the token structure
        try:
            parts = access_token.split('.')
            print(f"Token has {len(parts)} parts (should be 3 for JWT)")
            if len(parts) >= 2:
                # Try to decode the payload part
                payload_part = parts[1]
                # Add padding if needed
                padding = 4 - (len(payload_part) % 4)
                if padding != 4:
                    payload_part += '=' * padding
                decoded_payload = base64.b64decode(payload_part)
                print("Raw payload:")
                print(decoded_payload.decode('utf-8', errors='ignore'))
        except Exception as decode_error:
            print(f"Error inspecting token structure: {decode_error}")
        print("==============================\n")
        return None

def test_token_validity(access_token):
    """
    Test if the access token works with basic Graph API calls
    """
    import requests
    
    print("\n====== TOKEN VALIDITY TEST ======")
    
    # Test 1: Basic user info (should always work)
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0 (compatible; RUNDOWN-App/1.0)'
    }
    
    try:
        print("Testing basic /me endpoint...")
        response = requests.get('https://graph.microsoft.com/v1.0/me', headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            user_data = response.json()
            print(f"✅ Basic token works! User: {user_data.get('displayName', 'Unknown')}")
        else:
            print("❌ Basic token test failed")
            handle_graph_api_error(response)
            
    except Exception as e:
        print(f"Error during token test: {e}")
    
    print("==============================\n")

def handle_graph_api_error(response):
    """
    Extract detailed error information from Microsoft Graph API responses
    """
    print("=== MICROSOFT GRAPH API ERROR DETAILS ===")
    print(f"Status Code: {response.status_code}")
    print(f"Status Text: {response.reason}")
    
    # Print response headers for debugging
    print("\nResponse Headers:")
    for header, value in response.headers.items():
        if 'error' in header.lower() or 'www-authenticate' in header.lower():
            print(f"  {header}: {value}")
    
    # Try to parse JSON error response
    try:
        error_data = response.json()
        print("\nError Response Body:")
        print(json.dumps(error_data, indent=2))
        
        # Extract specific error information
        if 'error' in error_data:
            error_info = error_data['error']
            print(f"\nError Code: {error_info.get('code', 'Unknown')}")
            print(f"Error Message: {error_info.get('message', 'Unknown')}")
            
            # Check for inner errors
            if 'innerError' in error_info:
                inner = error_info['innerError']
                print(f"Inner Error: {inner}")
                
    except Exception as json_error:
        print(f"\nRaw Response Text (not JSON): {response.text}")
        print(f"JSON Parse Error: {json_error}")
    
    print("============================================\n")

def quick_test(access_token):
    """Quick test function for immediate debugging"""
    import requests
    
    print("\n====== QUICK TOKEN TEST ======")
    
    # Test the simplest endpoint first
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    try:
        response = requests.get('https://graph.microsoft.com/v1.0/me', headers=headers, timeout=10)
        print(f"Basic /me endpoint: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Error: {response.text}")
        else:
            print("✅ Basic token works!")
            
            # Now test calendar
            cal_response = requests.get('https://graph.microsoft.com/v1.0/me/calendars', headers=headers, timeout=10)
            print(f"Calendar endpoint: {cal_response.status_code}")
            if cal_response.status_code != 200:
                print(f"Calendar Error: {cal_response.text}")
            else:
                print("✅ Calendar works too!")
                
    except Exception as e:
        print(f"Quick test error: {e}")
    
    print("===============================\n")

def get_msal_app():
    """Create and return an MSAL confidential client application."""
    return msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET,
    )

def get_auth_url():
    """Generate the Microsoft OAuth authorization URL."""
    app = get_msal_app()
    # Use explicit redirect URI from config instead of dynamic URL generation
    from config import REDIRECT_URI
    
    # Print debug information about the redirect URI
    print("\n====== OAUTH DEBUG INFO ======")
    print(f"Using Redirect URI: {REDIRECT_URI}")
    print("Please make sure this EXACT URI is registered in Azure")
    print("==============================\n")
    
    auth_url = app.get_authorization_request_url(
        SCOPES,
        redirect_uri=REDIRECT_URI,
        # Add state parameter for security and to help prevent caching issues
        state=str(hash(f"state-{REDIRECT_URI}-{__import__('time').time()}")),
        # Force consent to ensure all permissions are granted
        prompt="consent"
    )
    return auth_url

def save_credentials(user_id, token_response):
    """Encrypt and save Microsoft token response to a file."""
    token_path = os.path.join(TOKENS_DIR, f"{user_id}.json")
    token_json = json.dumps(token_response)
    encrypted_token = cipher.encrypt(token_json.encode())
    with open(token_path, 'wb') as f:
        f.write(encrypted_token)

def load_credentials(user_id):
    """Load and decrypt Microsoft token from a file."""
    token_path = os.path.join(TOKENS_DIR, f"{user_id}.json")
    if not os.path.exists(token_path):
        return None
    try:
        with open(token_path, 'rb') as f:
            encrypted_token = f.read()
        decrypted_token = cipher.decrypt(encrypted_token).decode()
        token_response = json.loads(decrypted_token)
        return token_response
    except Exception as e:
        print(f"Error loading credentials for user {user_id}: {e}")
        return None

def get_token_from_cache(user_id):
    """Get a valid access token from cache or refresh if needed."""
    token_response = load_credentials(user_id)
    if not token_response:
        print(f"No token found for user {user_id}")
        return None
    
    # Check if the token contains an error
    if 'error' in token_response:
        print(f"Token error: {token_response.get('error')} - {token_response.get('error_description', '')}")
        return None
        
    # Check if token is present
    if 'access_token' not in token_response:
        print(f"No access_token found in token_response")
    
    app = get_msal_app()
    
    # Debug: Check current accounts
    accounts = app.get_accounts()
    print(f"Found {len(accounts)} accounts in MSAL cache")
    
    # Debug token expiration
    if 'expires_in' in token_response or 'expires_on' in token_response:
        # Check if token is expired
        import time
        current_time = int(time.time())
        expires = token_response.get('expires_on', 0)
        if expires == 0 and 'expires_in' in token_response:
            # If we only have expires_in, calculate expires_on
            expires = token_response.get('created_at', current_time) + token_response.get('expires_in', 0)
        
        time_left = expires - current_time
        if time_left > 0:
            print(f"Token expires in {time_left} seconds")
        else:
            print(f"Token expired {-time_left} seconds ago")
    else:
        print("No expiration information found in token")
    
    # Try to get token silently first
    if accounts:
        for account in accounts:
            print(f"Attempting silent token acquisition for account: {account.get('username', 'unknown')}")
            result = app.acquire_token_silent(SCOPES, account=account)
            if result and "access_token" in result:
                print("Successfully acquired token silently")
                # Debug the token claims
                debug_token_claims(result["access_token"])
                # Test token validity
                test_token_validity(result["access_token"])
                save_credentials(user_id, result)
                return result["access_token"]
            else:
                print("Silent token acquisition failed")
                if 'error' in result:
                    print(f"Error: {result.get('error')} - {result.get('error_description', '')}")
    else:
        print("No accounts found in MSAL cache")
    
    # If we have a refresh token, try to refresh
    if "refresh_token" in token_response:
        try:
            print(f"Attempting to refresh token using refresh_token")
            result = app.acquire_token_by_refresh_token(
                token_response["refresh_token"], 
                scopes=SCOPES
            )
            if result and "access_token" in result:
                print("Successfully refreshed token")
                # Debug the token claims
                debug_token_claims(result["access_token"])
                # Test token validity
                test_token_validity(result["access_token"])
                save_credentials(user_id, result)
                return result["access_token"]
            else:
                print("Token refresh failed")
                if 'error' in result:
                    print(f"Error: {result.get('error')} - {result.get('error_description', '')}")
        except Exception as e:
            print(f"Error refreshing token: {e}")
    else:
        print("No refresh token available")
    
    print("Failed to obtain a valid token - user needs to re-authenticate")
    return None

def require_auth(view):
    """Decorator to require authentication for routes."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            # For AJAX requests, return a JSON response instead of redirecting
            if request and (
                request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 
                request.headers.get('Content-Type') == 'application/json'
            ):
                return jsonify({"error": "Authentication required", "redirect": "/login"}), 401
            return redirect('/login')
            
        # Verify that we have a valid token
        user_id = session['user_id']
        token = get_token_from_cache(user_id)
        if not token:
            # Clear session and force re-authentication
            print(f"No valid token for user {user_id}, clearing session")
            session.clear()
            
            # For AJAX requests, return a JSON response instead of redirecting
            if request and (
                request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 
                request.headers.get('Content-Type') == 'application/json'
            ):
                return jsonify({"error": "Session expired", "redirect": "/login"}), 401
            return redirect('/login')
            
        return view(*args, **kwargs)
    return wrapper
