import json
import requests
import os
from datetime import datetime, timedelta
from utils.auth import get_token_from_cache

def make_graph_request(access_token, url, method='GET', data=None, params=None):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0 (compatible; RUNDOWN-App/1.0)',
        'X-AnchorMailbox': 'UPN', 
        'Prefer': 'outlook.timezone="UTC"'
    }
    try:
        if method.upper() == 'GET':
            response = requests.get(url, headers=headers, params=params, timeout=30)
        elif method.upper() == 'POST':
            response = requests.post(url, headers=headers, json=data, timeout=30)
        elif method.upper() == 'PATCH':
            response = requests.patch(url, headers=headers, json=data, timeout=30)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        if response.status_code >= 400:
            return response 
        return response
    except Exception as e:
        return None

def handle_outlook_api_error(response):
    try:
        error_data = response.json()
    except:
        pass

def create_outlook_category(access_token, category_name):
    url = "https://graph.microsoft.com/v1.0/me/outlook/masterCategories"
    response = make_graph_request(access_token, url, method='GET')
    if response and response.status_code == 200:
        categories = response.json().get('value', [])
        for category in categories:
            if category['displayName'] == category_name:
                return category['displayName']
    category_data = {
        "displayName": category_name,
        "color": "preset2"
    }
    create_response = make_graph_request(access_token, url, method='POST', data=category_data)
    if create_response and create_response.status_code == 201:
        return create_response.json()['displayName']
    else:
        return None

def get_email_details(access_token, email_id):
    url = f"https://graph.microsoft.com/v1.0/me/messages/{email_id}"
    response = make_graph_request(access_token, url, method='GET')
    if response and response.status_code == 200:
        email_data = response.json()
        return {
            'id': email_id,
            'subject': email_data.get('subject', 'No Subject'),
            'sender': email_data.get('from', {}).get('emailAddress', {}).get('address', 'Unknown Sender'),
            'content': email_data.get('body', {}).get('content', 'No content available'),
            'bodyType': email_data.get('body', {}).get('contentType', 'text'),
            'receivedDateTime': email_data.get('receivedDateTime', ''),
            'categories': email_data.get('categories', [])
        }
    else:
        return {'error': f'Failed to fetch email: {response.status_code if response else "No response"}'}

def save_emails_to_json(user_id, emails):
    try:
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'emails')
        os.makedirs(data_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"emails_{user_id}_{timestamp}.json"
        filepath = os.path.join(data_dir, filename)
        email_data = {
            'user_id': user_id,
            'fetch_timestamp': datetime.now().isoformat(),
            'email_count': len(emails),
            'emails': emails
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(email_data, f, indent=2, ensure_ascii=False)
        return filepath
    except Exception as e:
        return None

def load_emails_from_json(user_id, latest=True):
    try:
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'emails')
        if not os.path.exists(data_dir):
            return None
        user_files = []
        for filename in os.listdir(data_dir):
            if filename.startswith(f"emails_{user_id}_") and filename.endswith('.json'):
                filepath = os.path.join(data_dir, filename)
                user_files.append(filepath)
        if not user_files:
            return None
        if latest:
            user_files.sort(key=os.path.getmtime, reverse=True)
            filepath = user_files[0]
        else:
            filepath = user_files[0]
        with open(filepath, 'r', encoding='utf-8') as f:
            email_data = json.load(f)
        return email_data
    except Exception as e:
        return None

def get_stored_email_files(user_id=None):
    try:
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'emails')
        if not os.path.exists(data_dir):
            return []
        files_info = []
        for filename in os.listdir(data_dir):
            if filename.endswith('.json'):
                if user_id and not filename.startswith(f"emails_{user_id}_"):
                    continue
                filepath = os.path.join(data_dir, filename)
                try:
                    parts = filename.replace('.json', '').split('_')
                    if len(parts) >= 4:
                        file_user_id = '_'.join(parts[1:-2])
                        date_part = parts[-2]
                        time_part = parts[-1]
                        stat = os.stat(filepath)
                        files_info.append({
                            'filename': filename,
                            'filepath': filepath,
                            'user_id': file_user_id,
                            'date': f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}",
                            'time': f"{time_part[:2]}:{time_part[2:4]}:{time_part[4:6]}",
                            'size_bytes': stat.st_size,
                            'modified_time': datetime.fromtimestamp(stat.st_mtime).isoformat()
                        })
                except Exception as e:
                    pass
        files_info.sort(key=lambda x: x['modified_time'], reverse=True)
        return files_info
    except Exception as e:
        return []

def mark_email_with_category(access_token, email_id, category_name):
    url = f"https://graph.microsoft.com/v1.0/me/messages/{email_id}"
    response = make_graph_request(access_token, url, method='GET')
    if response and response.status_code == 200:
        email_data = response.json()
        current_categories = email_data.get('categories', [])
        if category_name not in current_categories:
            current_categories.append(category_name)
        update_data = {
            "categories": current_categories
        }
        update_response = make_graph_request(access_token, url, method='PATCH', data=update_data)
        return update_response and update_response.status_code == 200
    return False

def extract_email_content(email_body, body_type):
    if body_type == 'html':
        import re
        text = re.sub('<[^<]+?>', '', email_body)
        return text.strip()
    else:
        return email_body.strip()

def fetch_emails_with_mime(user_id, days=7):
    access_token = get_token_from_cache(user_id)
    if not access_token:
        return []
    try:
        date_from = (datetime.now() - timedelta(days=days)).isoformat() + 'Z'
        url = "https://graph.microsoft.com/v1.0/me/messages"
        params = {
            '$filter': f"receivedDateTime ge {date_from}",
            '$top': 10,
            '$orderby': 'receivedDateTime desc',
            '$select': 'id,subject,from,receivedDateTime,body,categories'
        }
        response = make_graph_request(access_token, url, method='GET', params=params)
        if response and response.status_code == 200:
            emails_data = response.json().get('value', [])
            emails = []
            for email_data in emails_data:
                email_id = email_data['id']
                mime_url = f"https://graph.microsoft.com/v1.0/me/messages/{email_id}/$value"
                mime_headers = {
                    'Authorization': f'Bearer {access_token}',
                    'Accept': 'application/octet-stream'
                }
                mime_resp = requests.get(mime_url, headers=mime_headers, timeout=30)
                mime_content = mime_resp.text if mime_resp.status_code == 200 else None
                email = {
                    'id': email_id,
                    'subject': email_data.get('subject', 'No Subject'),
                    'sender': email_data.get('from', {}).get('emailAddress', {}).get('address', 'Unknown Sender'),
                    'content': email_data.get('body', {}).get('content', 'No content available'),
                    'bodyType': email_data.get('body', {}).get('contentType', 'text'),
                    'receivedDateTime': email_data.get('receivedDateTime', ''),
                    'categories': email_data.get('categories', []),
                    'mime': mime_content
                }
                emails.append(email)
            filepath = save_emails_to_json(user_id, emails)
            return emails
        elif response and response.status_code == 401:
            beta_url = "https://graph.microsoft.com/beta/me/mailFolders/inbox/messages"
            beta_response = make_graph_request(access_token, beta_url, method='GET', params=params)
            if beta_response and beta_response.status_code == 200:
                emails_data = beta_response.json().get('value', [])
                emails = []
                for email_data in emails_data:
                    email_id = email_data['id']
                    mime_url = f"https://graph.microsoft.com/beta/me/messages/{email_id}/$value"
                    mime_headers = {
                        'Authorization': f'Bearer {access_token}',
                        'Accept': 'application/octet-stream'
                    }
                    mime_resp = requests.get(mime_url, headers=mime_headers, timeout=30)
                    mime_content = mime_resp.text if mime_resp.status_code == 200 else None
                    email = {
                        'id': email_id,
                        'subject': email_data.get('subject', 'No Subject'),
                        'sender': email_data.get('from', {}).get('emailAddress', {}).get('address', 'Unknown Sender'),
                        'content': email_data.get('body', {}).get('content', 'No content available'),
                        'bodyType': email_data.get('body', {}).get('contentType', 'text'),
                        'receivedDateTime': email_data.get('receivedDateTime', ''),
                        'categories': email_data.get('categories', []),
                        'mime': mime_content
                    }
                    emails.append(email)
                filepath = save_emails_to_json(user_id, emails)
                return emails
            else:
                return []
        else:
            handle_outlook_api_error(response)
            return []
    except Exception as e:
        return []