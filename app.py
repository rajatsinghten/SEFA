from flask import Flask, render_template, session, redirect, request, jsonify
from flask_cors import CORS
from flask_session import Session
from apscheduler.schedulers.background import BackgroundScheduler
import google.generativeai as genai
import os
import json
 
from config import SECRET_KEY, TOKENS_DIR, LABEL_NAME, GOOGLE_API_KEY
from utils.auth import get_token_from_cache
from utils.outlook import create_outlook_category, fetch_emails_with_mime, mark_email_with_category, extract_email_content
from utils.calendar import create_calendar_event
from utils.models import UserPreferences

app = Flask(__name__)
CORS(app, 
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])


app.secret_key = SECRET_KEY
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = True
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 86400 

Session(app)


genai.configure(api_key=GOOGLE_API_KEY)

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


@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', request.headers.get('Origin', '*'))
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Requested-With')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response


scheduler = BackgroundScheduler(daemon=True)
scheduler.start()

def process_emails():
    """Periodic task to process emails."""
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
            
            user_preferences = UserPreferences.load_preferences(user_id)
            if not user_preferences.get('enabled', True):
                print(f"Email processing disabled for user {user_id}")
                continue
                
            
            user_interests = user_preferences.get('interests', [])
            
           
            category_name = create_outlook_category(access_token, LABEL_NAME)
            if not category_name:
                print(f"Failed to create/get category for user {user_id}")
                continue
            
            
            emails = fetch_emails_with_mime(user_id, days=1)  
            if not emails or isinstance(emails, dict) and 'error' in emails:
                print(f"Failed to fetch emails for user {user_id}: {emails}")
                continue
                
            for email in emails:
                if isinstance(email, dict) and 'error' in email:
                    continue
                    
               
                if LABEL_NAME in email.get('categories', []):
                    continue
                
                email_id = email['id']
                subject = email['subject']
                sender = email['sender']
                content = extract_email_content(email['content'], email.get('bodyType', 'text'))
                received_date = email['receivedDateTime']
                
                
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
                       
                        mark_email_with_category(access_token, email_id, LABEL_NAME)
                        continue
                
                mark_email_with_category(access_token, email_id, LABEL_NAME)
                
                # AI-powered date detection and calendar event creation
                try:
                    import google.generativeai as genai
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    
                    prompt = f"""
                    Analyze this email for any dates, deadlines, meetings, or events that should be added to a calendar.
                    
                    Email Subject: {subject}
                    Email Content: {content[:1000]}  # Limit content for AI processing
                    
                    If there are any calendar-worthy items, respond with JSON in this format:
                    {{
                        "has_events": true,
                        "events": [
                            {{
                                "title": "Event title",
                                "date": "YYYY-MM-DD",
                                "time": "HH:MM" (if specified, otherwise "09:00"),
                                "description": "Brief description"
                            }}
                        ]
                    }}
                    
                    If no calendar items found, respond with: {{"has_events": false}}
                    
                    Only extract real dates and events, not hypothetical ones.
                    """
                    
                    response = model.generate_content(prompt)
                    ai_result = response.text.strip()
                    
                    try:
                        # Clean the response in case it has markdown formatting
                        if ai_result.startswith('```json'):
                            ai_result = ai_result.split('```json')[1].split('```')[0].strip()
                        elif ai_result.startswith('```'):
                            ai_result = ai_result.split('```')[1].strip()
                        
                        calendar_data = json.loads(ai_result)
                        
                        if calendar_data.get('has_events', False):
                            for event_data in calendar_data.get('events', []):
                                try:
                                    # Create calendar event
                                    event_result = create_calendar_event(
                                        user_id=user_id,
                                        subject=event_data['title'],
                                        sender=sender,
                                        date_str=event_data['date'],
                                        iso_date=f"{event_data['date']}T{event_data.get('time', '09:00')}:00",
                                        description=f"From email: {subject}\n\n{event_data.get('description', '')}"
                                    )
                                    
                                    if event_result and 'error' not in event_result:
                                        print(f"✅ Created calendar event: {event_data['title']} on {event_data['date']}")
                                    else:
                                        print(f"❌ Failed to create calendar event: {event_result}")
                                        
                                except Exception as event_error:
                                    print(f"❌ Error creating calendar event: {event_error}")
                                    
                    except json.JSONDecodeError as json_error:
                        print(f"❌ Failed to parse AI response as JSON: {json_error}")
                        print(f"AI Response: {ai_result}")
                        
                except Exception as ai_error:
                    print(f"❌ AI processing error: {ai_error}")
                
                print(f"✅ Processed email: {subject}")
                
        except Exception as e:
            print(f"Error processing emails for {user_id}: {e}")
            import traceback
            print(traceback.format_exc())

scheduler.add_job(func=process_emails, trigger='interval', minutes=50)


from routes.auth_routes import auth_bp
from routes.chat_routes import chat_bp
from routes.calendar_routes import calendar_bp
from routes.outlook_routes import outlook_bp
from routes.preferences_routes import preferences_bp

app.register_blueprint(auth_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(calendar_bp)
app.register_blueprint(outlook_bp)  
app.register_blueprint(preferences_bp)

@app.route('/')
def index():
    if 'user_id' in session:
        user_id = session['user_id']
        preferences = UserPreferences.load_preferences(user_id)
        
        
        if not preferences.get('interests'):
            return redirect('/preferences')
            
        return render_template('chat.html')
    return render_template('login.html')

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
