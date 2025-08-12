# backend/utils/auth.py
import os
import json
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
