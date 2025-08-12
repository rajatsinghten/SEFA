from flask import Flask, render_template, session, redirect, request, jsonify
from flask_cors import CORS
from flask_session import Session
from apscheduler.schedulers.background import BackgroundScheduler
import google.generativeai as genai
import os
 
# Configuration and utility imports
from config import SECRET_KEY, TOKENS_DIR, LABEL_NAME, GOOGLE_API_KEY
from utils.auth import get_token_from_cache
from utils.outlook import create_outlook_category, fetch_emails, mark_email_with_category, extract_email_content
from utils.calendar import create_calendar_event, fetch_calendar_events
from utils.models import UserPreferences

app = Flask(__name__)
# Fix CORS issues by allowing all routes and origins with proper configuration
CORS(app, 
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

# Configure session to be more robust
app.secret_key = SECRET_KEY
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = True
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours in seconds

Session(app)

# Configure the Generative AI model (used in blueprints)
genai.configure(api_key=GOOGLE_API_KEY)

# Add a route to check session status
@app.route('/api/session', methods=['GET'])
def check_session():
    if 'user_id' in session:
        return jsonify({
            "authenticated": True,
            "user_id": session['user_id']
        })
    else:
        return jsonify({
            "authenticated": False,
            "redirect": "/login"
        }), 401

# Handle CORS preflight for all routes
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', request.headers.get('Origin', '*'))
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Requested-With')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

# Scheduler for processing emails periodically
scheduler = BackgroundScheduler(daemon=True)
scheduler.start()

def process_emails():
    """Periodic task to process emails and create calendar events."""
    print("Processing emails...")
    for token_file in os.listdir(TOKENS_DIR):
        if not token_file.endswith('.json') or '_preferences' in token_file:
            continue
            
        user_id = token_file.split('.')[0]
        access_token = get_token_from_cache(user_id)
        if not access_token:
            print(f"No valid access token for user {user_id}")
            continue
            
        try:
            # Load user preferences
            user_preferences = UserPreferences.load_preferences(user_id)
            if not user_preferences.get('enabled', True):
                print(f"Email processing disabled for user {user_id}")
                continue
                
            # Get user interests for filtering
            user_interests = user_preferences.get('interests', [])
            
            # Ensure category exists
            category_name = create_outlook_category(access_token, LABEL_NAME)
            if not category_name:
                print(f"Failed to create/get category for user {user_id}")
                continue
            
            # Fetch recent emails
            emails = fetch_emails(user_id, days=1)  # Process emails from last day
            if not emails or isinstance(emails, dict) and 'error' in emails:
                print(f"Failed to fetch emails for user {user_id}: {emails}")
                continue
                
            for email in emails:
                if isinstance(email, dict) and 'error' in email:
                    continue
                    
                # Check if already processed (has our category)
                if LABEL_NAME in email.get('categories', []):
                    continue
                
                email_id = email['id']
                subject = email['subject']
                sender = email['sender']
                content = extract_email_content(email['content'], email.get('bodyType', 'text'))
                received_date = email['receivedDateTime']
                
                # If user has interests and filtering is enabled, check if email matches interests
                if user_interests:
                    matches_interest = False
                    email_content = f"{subject} {content}".lower()
                    
                    for interest in user_interests:
                        if interest.lower() in email_content:
                            matches_interest = True
                            print(f"Email matched interest: {interest}")
                            break
                            
                    if not matches_interest:
                        print(f"Email doesn't match user interests: {subject}")
                        # Mark as processed without creating an event
                        mark_email_with_category(access_token, email_id, LABEL_NAME)
                        continue
                
                # Use AI to extract the actual event date from the email content
                prompt = f"""
                Email Subject: {subject}
                Email Content: {content}
                
                Extract the following information from this email:
                1. The SPECIFIC date and time of the event mentioned (EXACT DATE AND TIME, not relative dates)
                2. The location of the event (if mentioned)
                3. A brief description of what this event is about
                
                Format your response as JSON:
                {{
                    "event_date": "YYYY-MM-DD HH:MM" or "none" if not found,
                    "location": "location string or 'none' if not found",
                    "description": "brief description of the event"
                }}
                
                IMPORTANT: For the event_date, you must provide the EXACT date and time in YYYY-MM-DD HH:MM format.
                Do not use "tomorrow", "next week", or any other relative dates. Convert them to actual calendar dates.
                """
                
                try:
                    # Configure the AI model if not already done
                    if not genai.get_default_api_key():
                        genai.configure(api_key=GOOGLE_API_KEY)
                    
                    model = genai.GenerativeModel("gemini-1.5-flash")
                    response = model.generate_content(prompt)
                    
                    if response and response.text:
                        # Extract the JSON response
                        import json
                        import re
                        
                        response_text = response.text.strip()
                        # Extract JSON if it's wrapped in code blocks
                        if "```json" in response_text:
                            json_str = response_text.split("```json")[1].split("```")[0].strip()
                        elif "```" in response_text:
                            json_str = response_text.split("```")[1].strip()
                        else:
                            json_str = response_text
                            
                        # Parse the extracted JSON
                        extracted_data = json.loads(json_str)
                        
                        # Get the event date from the extraction or use email date as fallback
                        event_date = extracted_data.get('event_date', 'none')
                        location = extracted_data.get('location', 'none')
                        event_description = extracted_data.get('description', '')
                        
                        if event_date and event_date.lower() != 'none':
                            # Parse the event date
                            from datetime import datetime
                            try:
                                # Try with standard format first
                                event_dt = datetime.strptime(event_date, "%Y-%m-%d %H:%M")
                                print(f"Successfully parsed event date using standard format: {event_date}")
                            except Exception as date_error:
                                try:
                                    # Try with dateutil parser which is more flexible
                                    from dateutil import parser
                                    event_dt = parser.parse(event_date)
                                    print(f"Successfully parsed event date using dateutil: {event_date} -> {event_dt}")
                                except Exception as parser_error:
                                    print(f"Error parsing event date with both methods: {date_error} and {parser_error}")
                                    # Fallback to email date
                                    event_dt = datetime.fromisoformat(received_date.replace('Z', ''))
                                    print(f"Using fallback email timestamp: {event_dt}")
                                
                            # Create ISO format date
                            iso_date = event_dt.isoformat()
                            print(f"Extracted event date: {event_date} -> ISO format: {iso_date}")
                        else:
                            # Use email date if no event date found
                            print(f"No event date found in: {subject}, using email date")
                            event_dt = datetime.fromisoformat(received_date.replace('Z', ''))
                            iso_date = event_dt.isoformat()
                        
                        # Enhanced event description with location
                        full_description = f"From: {sender}\nDate: {received_date}\nSubject: {subject}"
                        if event_description:
                            full_description += f"\n\nDetails: {event_description}"
                        if location and location.lower() != 'none':
                            full_description += f"\n\nLocation: {location}"
                            
                        # Create calendar event with the extracted date and enhanced description
                        create_calendar_event(
                            user_id, 
                            subject, 
                            sender, 
                            received_date, 
                            iso_date, 
                            description=full_description,
                            set_reminder=True
                        )
                    else:
                        # Fallback to email date if AI extraction fails
                        event_dt = datetime.fromisoformat(received_date.replace('Z', ''))
                        iso_date = event_dt.isoformat()
                        create_calendar_event(user_id, subject, sender, received_date, iso_date)
                        
                except Exception as ai_error:
                    print(f"Error using AI to extract date: {ai_error}")
                    # Fallback to email date
                    from datetime import datetime
                    event_dt = datetime.fromisoformat(received_date.replace('Z', ''))
                    iso_date = event_dt.isoformat()
                    create_calendar_event(user_id, subject, sender, received_date, iso_date)
                
                # Mark as processed
                mark_email_with_category(access_token, email_id, LABEL_NAME)
                
        except Exception as e:
            print(f"Error processing emails for {user_id}: {e}")
            import traceback
            print(traceback.format_exc())

scheduler.add_job(func=process_emails, trigger='interval', minutes=50)

# Import and register blueprints
from routes.auth_routes import auth_bp
from routes.chat_routes import chat_bp
from routes.outlook_routes import outlook_bp
from routes.calendar_routes import calendar_bp
from routes.preferences_routes import preferences_bp

app.register_blueprint(auth_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(outlook_bp)  # Updated blueprint registration
app.register_blueprint(calendar_bp)
app.register_blueprint(preferences_bp)

@app.route('/')
def index():
    if 'user_id' in session:
        # Check if user has set preferences yet
        user_id = session['user_id']
        preferences = UserPreferences.load_preferences(user_id)
        
        # If user hasn't set preferences, redirect to preferences page
        if not preferences.get('interests'):
            return redirect('/preferences')
            
        return render_template('chat.html')
    return render_template('login.html')

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
