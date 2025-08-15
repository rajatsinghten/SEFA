import os
from dotenv import load_dotenv

load_dotenv()
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
SECRET_KEY = os.urandom(24)
TOKENS_DIR = "tokens"
KEY_FILE = "secret.key"
LABEL_NAME = "AddedToCalendar"

CLIENT_ID = "8080fa82-1354-4d72-af67-da194392aa4a"
CLIENT_SECRET = os.getenv("CLIENT_SECRET") 
AUTHORITY = f"https://login.microsoftonline.com/consumers"
REDIRECT_PATH = "/callback"
REDIRECT_URI = "http://localhost:5000/callback"
SCOPES = [
    'https://graph.microsoft.com/Mail.Read',
    'https://graph.microsoft.com/Mail.ReadWrite',
    'https://graph.microsoft.com/Calendars.Read',
    'https://graph.microsoft.com/Calendars.ReadWrite',
    'https://graph.microsoft.com/User.Read'
]
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
