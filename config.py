# backend/config.py
import os
from dotenv import load_dotenv

load_dotenv()

# Allow OAuthlib to run without HTTPS for local development
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Flask secret key (used for sessions)
SECRET_KEY = os.urandom(24)

# Token storage & encryption configuration
TOKENS_DIR = "tokens"
KEY_FILE = "secret.key"
LABEL_NAME = "AddedToCalendar"

# Microsoft Graph API configuration
CLIENT_ID = "4b7b4c3c-60f0-4f92-bd1d-c222f7683a64"
TENANT_ID = "c68bfe4b-5da1-432f-a631-69a9f35b5f4b"
CLIENT_SECRET = os.getenv("CLIENT_SECRET")  # Store this in .env file
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
REDIRECT_PATH = "/oauth/callback"
REDIRECT_URI = "http://localhost:5000/oauth/callback"

# Microsoft Graph API scopes required by your app
SCOPES = [
    'https://graph.microsoft.com/Mail.Read',
    'https://graph.microsoft.com/Mail.ReadWrite',
    'https://graph.microsoft.com/Calendars.ReadWrite',
    'https://graph.microsoft.com/User.Read'
]

# Google API key for generative AI (make sure to set it in your .env file)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
