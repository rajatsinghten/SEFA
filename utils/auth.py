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

Path(TOKENS_DIR).mkdir(exist_ok=True)
if not os.path.exists(KEY_FILE):
    key = Fernet.generate_key()
    with open(KEY_FILE, 'wb') as f:
        f.write(key)
else:
    with open(KEY_FILE, 'rb') as f:
        key = f.read()

cipher = Fernet(key)

def get_msal_app():
    return msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET,
    )

def get_auth_url():
    app = get_msal_app()
    from config import REDIRECT_URI
    auth_url = app.get_authorization_request_url(
        SCOPES,
        redirect_uri=REDIRECT_URI,
        state=str(hash(f"state-{REDIRECT_URI}-{__import__('time').time()}")),
        prompt="consent"
    )
    return auth_url

def save_credentials(user_id, token_response):
    token_path = os.path.join(TOKENS_DIR, f"{user_id}.json")
    token_json = json.dumps(token_response)
    encrypted_token = cipher.encrypt(token_json.encode())
    with open(token_path, 'wb') as f:
        f.write(encrypted_token)

def load_credentials(user_id):
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
        return None

def get_token_from_cache(user_id):
    token_response = load_credentials(user_id)
    if not token_response:
        return None
    if 'error' in token_response:
        return None
    app = get_msal_app()
    accounts = app.get_accounts()
    if accounts:
        for account in accounts:
            result = app.acquire_token_silent(SCOPES, account=account)
            if result and "access_token" in result:
                save_credentials(user_id, result)
                return result["access_token"]
    if "refresh_token" in token_response:
        try:
            result = app.acquire_token_by_refresh_token(
                token_response["refresh_token"], 
                scopes=SCOPES
            )
            if result and "access_token" in result:
                save_credentials(user_id, result)
                return result["access_token"]
        except Exception as e:
            pass
    return None

def require_auth(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            if request and (
                request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 
                request.headers.get('Content-Type') == 'application/json'
            ):
                return jsonify({"error": "Authentication required", "redirect": "/login"}), 401
            return redirect('/login')
        user_id = session['user_id']
        token = get_token_from_cache(user_id)
        if not token:
            session.clear()
            if request and (
                request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 
                request.headers.get('Content-Type') == 'application/json'
            ):
                return jsonify({"error": "Session expired", "redirect": "/login"}), 401
            return redirect('/login')
        return view(*args, **kwargs)
    return wrapper
