# backend/utils/calendar.py
import json
import requests
from datetime import datetime, timedelta
import traceback
import pytz
from tzlocal import get_localzone
from utils.auth import get_token_from_cache

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
    access_token = get_token_from_cache(user_id)
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
        response = requests.post(url, headers=headers, json=event_body)
        
        if response.status_code == 201:
            event = response.json()
            print(f"Created event: {event.get('webLink')} with reminder set")
            print(f"==== END CALENDAR EVENT CREATION ====\n")
            return event
        else:
            print(f"Error creating event: {response.status_code} - {response.text}")
            raise Exception(f"Failed to create calendar event: {response.status_code}")
            
    except Exception as e:
        print(f"Error creating calendar event: {e}")
        print(traceback.format_exc())
        raise

def delete_calendar_event(user_id, event_id):
    """Deletes a calendar event by ID."""
    access_token = get_token_from_cache(user_id)
    if not access_token:
        raise Exception("No valid access token available")
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    try:
        print(f"Attempting to delete calendar event with ID: {event_id}")
        
        # First, try to get the event to confirm it exists
        url = f"https://graph.microsoft.com/v1.0/me/events/{event_id}"
        response = requests.get(url, headers=headers)
        
        if response.status_code == 404:
            print(f"Event {event_id} not found - it may have been already deleted")
            return {"status": "not_found", "message": "Event already deleted"}
        elif response.status_code == 200:
            event = response.json()
            print(f"Found event to delete: {event.get('subject', 'No title')} ({event_id})")
        else:
            print(f"Error checking event existence: {response.status_code}")
            raise Exception(f"Error checking event: {response.status_code}")
        
        # If we got here, the event exists, so delete it
        response = requests.delete(url, headers=headers)
        
        if response.status_code == 204:
            print(f"Successfully deleted event with ID: {event_id}")
            return {"status": "deleted", "message": "Event deleted successfully"}
        else:
            print(f"Error deleting event: {response.status_code} - {response.text}")
            raise Exception(f"Failed to delete event: {response.status_code}")
            
    except Exception as e:
        print(f"Error during event deletion: {str(e)}")
        print(traceback.format_exc())
        raise

def fetch_calendar_events(user_id):
    """Fetch upcoming calendar events."""
    print(f"\n===== FETCHING CALENDAR EVENTS FOR USER {user_id} =====")
    access_token = get_token_from_cache(user_id)
    if not access_token:
        print(f"No valid access token for user {user_id}")
        raise Exception("No valid access token available - user needs to re-authenticate")
    
    # Verify token format
    print(f"Access token obtained (first 10 chars): {access_token[:10]}...")
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    try:
        now = datetime.utcnow().isoformat() + 'Z'
        print(f"Fetching events after: {now}")
        
        url = "https://graph.microsoft.com/v1.0/me/events"
        params = {
            '$filter': f"start/dateTime ge '{now}'",
            '$top': 10,
            '$orderby': 'start/dateTime',
            '$select': 'id,subject,bodyPreview,start,end,webLink' # Select only needed fields
        }
        
        print(f"Making request to: {url}")
        response = requests.get(url, headers=headers, params=params)
        
        print(f"Response status: {response.status_code}")
        if response.status_code == 200:
            events_data = response.json().get('value', [])
            formatted_events = []
            
            print(f"Found {len(events_data)} calendar events")
            for event in events_data:
                formatted_event = {
                    "id": event.get("id", ""),
                    "summary": event.get("subject", "No Title"),  # Microsoft uses 'subject' instead of 'summary'
                    "description": event.get("bodyPreview", ""),
                    "start": event.get("start", {}),
                    "end": event.get("end", {}),
                    "webLink": event.get("webLink", "")
                }
                formatted_events.append(formatted_event)
            
            return formatted_events
        elif response.status_code == 401:
            print("Authentication error (401) - token expired or invalid")
            # Clear the cached token to force re-authentication
            print(f"Response text: {response.text}")
            raise Exception(f"PERMISSION_ERROR: Microsoft Graph API access denied. This usually means the application doesn't have the required permissions or consent wasn't properly completed.")
        else:
            print(f"Error fetching events: {response.status_code} - {response.text}")
            raise Exception(f"Failed to fetch calendar events: {response.status_code}")
            
    except Exception as e:
        print(f"Error fetching calendar events: {str(e)}")
        print(traceback.format_exc())
        raise
