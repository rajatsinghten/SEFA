import json
import requests
from datetime import datetime, timedelta
import pytz
from tzlocal import get_localzone
from utils.auth import get_token_from_cache, get_msal_app
from config import SCOPES

def get_fresh_token_for_calendar(user_id):
    cached_token = get_token_from_cache(user_id)
    if not cached_token:
        return None
    app = get_msal_app()
    accounts = app.get_accounts()
    if accounts:
        for account in accounts:
            result = app.acquire_token_silent(SCOPES, account=account)
            if result and 'access_token' in result:
                return result['access_token']
    return cached_token

def make_graph_request(access_token, url, method='GET', data=None, params=None):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0 (compatible; RUNDOWN-App/1.0)',
        'X-AnchorMailbox': 'UPN',
        'Prefer': 'outlook.timezone="UTC"',
        'ConsistencyLevel': 'eventual'
    }
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
        if response.status_code >= 400:
            handle_graph_api_error(response)
            return None
        return response
    except Exception as e:
        return None

def handle_graph_api_error(response):
    try:
        error_data = response.json()
    except Exception as json_error:
        pass

def create_calendar_event(user_id, subject, sender, date_str, iso_date, end_date=None, description=None, set_reminder=False):
    access_token = get_fresh_token_for_calendar(user_id)
    if not access_token:
        raise Exception("No valid access token available")
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    timezone_str = 'Asia/Kolkata'
    if iso_date.endswith('Z'):
        iso_date = iso_date[:-1]
    if not end_date:
        try:
            start_dt = datetime.fromisoformat(iso_date)
            end_dt = start_dt + timedelta(hours=1)
            end_iso_date = end_dt.isoformat()
        except Exception as e:
            end_iso_date = iso_date
    else:
        if end_date.endswith('Z'):
            end_iso_date = end_date[:-1]
        else:
            end_iso_date = end_date
    event_description = description if description else f"From: {sender}\nDate: {date_str}\nSubject: {subject}"
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
    try:
        url = "https://graph.microsoft.com/v1.0/me/events"
        response = make_graph_request(access_token, url, method='POST', data=event_body)
        if response and response.status_code == 201:
            event = response.json()
            return event
        else:
            beta_url = "https://graph.microsoft.com/beta/me/events"
            beta_response = make_graph_request(access_token, beta_url, method='POST', data=event_body)
            if beta_response and beta_response.status_code == 201:
                event = beta_response.json()
                return event
            else:
                error_msg = f"Failed to create calendar event on both v1.0 and beta endpoints"
                raise Exception(error_msg)
    except Exception as e:
        raise

def delete_calendar_event(user_id, event_id):
    access_token = get_fresh_token_for_calendar(user_id)
    if not access_token:
        raise Exception("No valid access token available")
    try:
        url = f"https://graph.microsoft.com/v1.0/me/events/{event_id}"
        response = make_graph_request(access_token, url, method='GET')
        if response is None:
            raise Exception("Failed to verify event existence")
        elif response.status_code == 404:
            return {"status": "not_found", "message": "Event already deleted"}
        elif response.status_code == 200:
            event = response.json()
        else:
            raise Exception(f"Error checking event: {response.status_code}")
        delete_response = make_graph_request(access_token, url, method='DELETE')
        if delete_response and delete_response.status_code == 204:
            return {"status": "deleted", "message": "Event deleted successfully"}
        else:
            raise Exception(f"Failed to delete event")
    except Exception as e:
        raise

def fetch_calendar_events(user_id):
    access_token = get_fresh_token_for_calendar(user_id)
    if not access_token:
        raise Exception("No valid access token available - user needs to re-authenticate")
    try:
        now = datetime.utcnow().isoformat() + 'Z'
        simple_endpoints = [
            "https://graph.microsoft.com/v1.0/me/events?$top=5",
            "https://graph.microsoft.com/beta/me/events?$top=5",
            "https://graph.microsoft.com/v1.0/me/calendar/events?$top=5"
        ]
        for endpoint in simple_endpoints:
            response = make_graph_request(access_token, endpoint, method='GET')
            if response and response.status_code == 200:
                events_data = response.json().get('value', [])
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
        return []
    except Exception as e:
        return []
