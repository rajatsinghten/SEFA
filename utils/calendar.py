# backend/utils/calendar.py
import json
import requests
from datetime import datetime, timedelta
import traceback
import pytz
from tzlocal import get_localzone
from utils.auth import get_token_from_cache, get_msal_app
from config import SCOPES

def get_fresh_token_for_calendar(user_id):
    """Get a fresh token specifically for calendar operations"""
    print(f"\n=== GETTING FRESH CALENDAR TOKEN ===")
    
    # First try the cached token
    cached_token = get_token_from_cache(user_id)
    if not cached_token:
        print("No cached token available")
        return None
    
    # Try to get a fresh token using MSAL with the SAME scopes from config
    app = get_msal_app()
    accounts = app.get_accounts()
    
    if accounts:
        print(f"Found {len(accounts)} MSAL accounts")
        for account in accounts:
            print(f"Trying account: {account.get('username', 'unknown')}")
            
            # Use the same scopes from config that were originally granted
            result = app.acquire_token_silent(SCOPES, account=account)
            if result and 'access_token' in result:
                print("✅ Got fresh token for calendar using config scopes")
                return result['access_token']
            else:
                print(f"Failed to get fresh token: {result.get('error', 'Unknown error') if result else 'No result'}")
    else:
        print("No MSAL accounts found")
    
    # Fallback to cached token
    print("Using cached token as fallback")
    print("=== END FRESH CALENDAR TOKEN ===\n")
    return cached_token

def make_graph_request(access_token, url, method='GET', data=None, params=None):
    """
    Make a properly formatted Microsoft Graph API request with comprehensive error handling
    """
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0 (compatible; RUNDOWN-App/1.0)',
        'X-AnchorMailbox': 'UPN',  # Helps with routing
        'Prefer': 'outlook.timezone="UTC"',  # Consistent timezone handling
        'ConsistencyLevel': 'eventual'  # For advanced queries
    }
    
    print(f"\n=== MAKING GRAPH API REQUEST ===")
    print(f"Method: {method}")
    print(f"URL: {url}")
    print(f"Token (last 10 chars): ...{access_token[-10:]}")
    if params:
        print(f"Params: {params}")
    if data:
        print(f"Data: {json.dumps(data, indent=2)}")
    
    try:
        import requests
        if method.upper() == 'GET':
            response = requests.get(url, headers=headers, params=params, timeout=30)
        elif method.upper() == 'POST':
            response = requests.post(url, headers=headers, json=data, timeout=30)
        elif method.upper() == 'DELETE':
            response = requests.delete(url, headers=headers, timeout=30)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        print(f"Response Status: {response.status_code}")
        
        # Enhanced error handling
        if response.status_code >= 400:
            print(f"Error Response Headers: {dict(response.headers)}")
            print(f"Error Response Text: {response.text}")
            handle_graph_api_error(response)
            return None
        
        print("✅ Request successful")
        return response
        
    except Exception as e:
        print(f"Request failed with exception: {e}")
        return None
    finally:
        print("=== END GRAPH API REQUEST ===\n")

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
        if any(keyword in header.lower() for keyword in ['error', 'www-authenticate', 'request-id', 'date']):
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

def create_calendar_event(user_id, subject, sender, date_str, iso_date, end_date=None, description=None, set_reminder=False):
    """Creates a calendar event based on email details.
    
    Args:
        user_id: User ID to get access token for
        subject: Event subject/title
        sender: Email sender
        date_str: Original date string
        iso_date: ISO formatted date for the event start time
        end_date: Optional end time (if None, will be set to start + 1 hour)
        description: Optional detailed description for the event
        set_reminder: Whether to set a reminder 24 hours before the event
    """
    access_token = get_fresh_token_for_calendar(user_id)
    if not access_token:
        raise Exception("No valid access token available")
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    # Debug incoming date information
    print(f"\n==== CALENDAR EVENT CREATION ====")
    print(f"Subject: {subject}")
    print(f"ISO Date: {iso_date}")
    print(f"End Date: {end_date}")
    
    # Get user's local timezone
    try:
        local_tz = get_localzone()
        timezone_str = str(local_tz)
        print(f"Using timezone: {timezone_str}")
    except:
        # Fallback to a common timezone if detection fails
        timezone_str = 'America/New_York'
        print(f"Timezone detection failed, using fallback: {timezone_str}")
    
    # Remove the Z from ISO date which indicates UTC
    if iso_date.endswith('Z'):
        iso_date = iso_date[:-1]
        print(f"Removed Z suffix, new ISO date: {iso_date}")
    
    # If no specific end date is provided, set it to 1 hour after start time
    if not end_date:
        # Parse the iso_date to datetime
        try:
            start_dt = datetime.fromisoformat(iso_date)
            print(f"Parsed start date: {start_dt}")
            end_dt = start_dt + timedelta(hours=1)
            end_iso_date = end_dt.isoformat()
            print(f"Calculated end date: {end_dt} -> {end_iso_date}")
        except Exception as e:
            # Fallback if parsing fails
            end_iso_date = iso_date
            print(f"Failed to calculate end date: {e}")
            print(f"Using same time for end date: {iso_date}")
    else:
        if end_date.endswith('Z'):
            end_iso_date = end_date[:-1]
            print(f"Removed Z suffix from end date: {end_iso_date}")
        else:
            end_iso_date = end_date
            print(f"Using provided end date: {end_iso_date}")
    
    # Use provided description or create default one
    event_description = description if description else f"From: {sender}\nDate: {date_str}\nSubject: {subject}"
    
    # Verbose check to make sure we're not using default values
    if iso_date.endswith('T09:00:00'):
        print(f"WARNING: Date appears to be default 9am time: {iso_date}")
    
    # Create event body for Microsoft Graph
    event_body = {
        'subject': subject,
        'body': {
            'contentType': 'text',
            'content': event_description
        },
        'start': {
            'dateTime': iso_date,
            'timeZone': timezone_str
        },
        'end': {
            'dateTime': end_iso_date,
            'timeZone': timezone_str
        },
        'isReminderOn': True,
        'reminderMinutesBeforeStart': 30
    }
    
    print(f"Event start datetime: {iso_date}")
    print(f"Event end datetime: {end_iso_date}")
    print(f"Event timezone: {timezone_str}")
    
    try:
        url = "https://graph.microsoft.com/v1.0/me/events"
        response = make_graph_request(access_token, url, method='POST', data=event_body)
        
        if response and response.status_code == 201:
            event = response.json()
            print(f"Created event: {event.get('webLink')} with reminder set")
            print(f"==== END CALENDAR EVENT CREATION ====\n")
            return event
        else:
            # Try beta endpoint if v1.0 fails
            print("v1.0 endpoint failed, trying beta endpoint...")
            beta_url = "https://graph.microsoft.com/beta/me/events"
            beta_response = make_graph_request(access_token, beta_url, method='POST', data=event_body)
            
            if beta_response and beta_response.status_code == 201:
                event = beta_response.json()
                print(f"Created event via beta endpoint: {event.get('webLink')}")
                print(f"==== END CALENDAR EVENT CREATION ====\n")
                return event
            else:
                error_msg = f"Failed to create calendar event on both v1.0 and beta endpoints"
                print(error_msg)
                raise Exception(error_msg)
            
    except Exception as e:
        print(f"Error creating calendar event: {e}")
        print(traceback.format_exc())
        raise

def delete_calendar_event(user_id, event_id):
    """Deletes a calendar event by ID."""
    access_token = get_fresh_token_for_calendar(user_id)
    if not access_token:
        raise Exception("No valid access token available")
    
    try:
        print(f"Attempting to delete calendar event with ID: {event_id}")
        
        # First, try to get the event to confirm it exists
        url = f"https://graph.microsoft.com/v1.0/me/events/{event_id}"
        response = make_graph_request(access_token, url, method='GET')
        
        if response is None:
            print(f"Failed to check event existence")
            raise Exception("Failed to verify event existence")
        elif response.status_code == 404:
            print(f"Event {event_id} not found - it may have been already deleted")
            return {"status": "not_found", "message": "Event already deleted"}
        elif response.status_code == 200:
            event = response.json()
            print(f"Found event to delete: {event.get('subject', 'No title')} ({event_id})")
        else:
            print(f"Error checking event existence: {response.status_code}")
            raise Exception(f"Error checking event: {response.status_code}")
        
        # If we got here, the event exists, so delete it
        delete_response = make_graph_request(access_token, url, method='DELETE')
        
        if delete_response and delete_response.status_code == 204:
            print(f"Successfully deleted event with ID: {event_id}")
            return {"status": "deleted", "message": "Event deleted successfully"}
        else:
            print(f"Error deleting event")
            raise Exception(f"Failed to delete event")
            
    except Exception as e:
        print(f"Error during event deletion: {str(e)}")
        print(traceback.format_exc())
        raise

def debug_calendar_access(user_id):
    """Debug function to test different approaches to calendar access"""
    print(f"\n=== DEBUGGING CALENDAR ACCESS ===")
    
    access_token = get_token_from_cache(user_id)
    if not access_token:
        print("No access token available")
        return
    
    import requests
    
    # Test different header combinations
    test_cases = [
        {
            "name": "Minimal Headers",
            "headers": {
                'Authorization': f'Bearer {access_token}',
                'Accept': 'application/json'
            }
        },
        {
            "name": "Standard Headers",
            "headers": {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        },
        {
            "name": "Extended Headers",
            "headers": {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'User-Agent': 'Mozilla/5.0 (compatible; RUNDOWN-App/1.0)',
                'ConsistencyLevel': 'eventual'
            }
        }
    ]
    
    urls_to_test = [
        "https://graph.microsoft.com/v1.0/me",
        "https://graph.microsoft.com/v1.0/me/events",
        "https://graph.microsoft.com/v1.0/me/calendar/events",
        "https://graph.microsoft.com/beta/me/events"
    ]
    
    for test_case in test_cases:
        print(f"\n--- Testing {test_case['name']} ---")
        for url in urls_to_test:
            try:
                response = requests.get(url, headers=test_case['headers'], timeout=10)
                print(f"{url}: {response.status_code}")
                if response.status_code != 200:
                    print(f"  Error: {response.text[:100]}...")
            except Exception as e:
                print(f"{url}: Exception - {e}")
    
    print("=== END CALENDAR DEBUG ===\n")

def fetch_calendar_events(user_id):
    """Fetch upcoming calendar events."""
    print(f"\n===== FETCHING CALENDAR EVENTS FOR USER {user_id} =====")
    
    # Debug calendar access first
    debug_calendar_access(user_id)
    
    # Get fresh token specifically for calendar operations
    access_token = get_fresh_token_for_calendar(user_id)
    if not access_token:
        print(f"No valid access token for user {user_id}")
        raise Exception("No valid access token available - user needs to re-authenticate")
    
    # Verify token format
    print(f"Access token obtained (first 10 chars): {access_token[:10]}...")
    
    try:
        now = datetime.utcnow().isoformat() + 'Z'
        print(f"Fetching events after: {now}")
        
        # Try simple endpoint without complex filters first
        simple_endpoints = [
            "https://graph.microsoft.com/v1.0/me/events?$top=5",
            "https://graph.microsoft.com/beta/me/events?$top=5",
            "https://graph.microsoft.com/v1.0/me/calendar/events?$top=5"
        ]
        
        # First try without complex filters
        for endpoint in simple_endpoints:
            print(f"\nTrying simple endpoint: {endpoint}")
            response = make_graph_request(access_token, endpoint, method='GET')
            
            if response and response.status_code == 200:
                events_data = response.json().get('value', [])
                print(f"✅ SUCCESS with simple query! Found {len(events_data)} events from {endpoint}")
                
                # Now try with filters
                filtered_endpoint = endpoint.replace('?$top=5', '')
                params = {
                    '$filter': f"start/dateTime ge '{now}'",
                    '$top': 10,
                    '$orderby': 'start/dateTime',
                    '$select': 'id,subject,bodyPreview,start,end,webLink'
                }
                
                filtered_response = make_graph_request(access_token, filtered_endpoint, method='GET', params=params)
                if filtered_response and filtered_response.status_code == 200:
                    filtered_events = filtered_response.json().get('value', [])
                    formatted_events = []
                    
                    for event in filtered_events:
                        formatted_event = {
                            "id": event.get("id", ""),
                            "summary": event.get("subject", "No Title"),
                            "description": event.get("bodyPreview", ""),
                            "start": event.get("start", {}),
                            "end": event.get("end", {}),
                            "webLink": event.get("webLink", "")
                        }
                        formatted_events.append(formatted_event)
                    
                    return formatted_events
                else:
                    # Return the simple results without filters
                    formatted_events = []
                    for event in events_data:
                        formatted_event = {
                            "id": event.get("id", ""),
                            "summary": event.get("subject", "No Title"),
                            "description": event.get("bodyPreview", ""),
                            "start": event.get("start", {}),
                            "end": event.get("end", {}),
                            "webLink": event.get("webLink", "")
                        }
                        formatted_events.append(formatted_event)
                    
                    return formatted_events
            else:
                print(f"❌ Failed with simple endpoint: {endpoint}")
                continue
        
        # If all simple endpoints failed, suggest re-authentication
        print("❌ All calendar endpoints failed - this suggests a permission issue")
        print("🔧 SOLUTION: You need to:")
        print("   1. Go to Azure Portal → App registrations → Rundown")
        print("   2. Add Application permissions for Calendars.Read and Calendars.ReadWrite")
        print("   3. Grant admin consent")
        print("   4. Wait 10-15 minutes")
        print("   5. Or re-authenticate with updated permissions")
        
        # Return empty list instead of throwing exception
        return []
            
    except Exception as e:
        print(f"Error fetching calendar events: {str(e)}")
        print(traceback.format_exc())
        # Return empty list instead of throwing exception to keep app working
        return []
