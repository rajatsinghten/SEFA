# backend/utils/outlook.py
import json
import requests
import os
from datetime import datetime, timedelta
from utils.auth import get_token_from_cache


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
        'Prefer': 'outlook.timezone="UTC"'  # Consistent timezone handling
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
            print(f"⚠️ API Error: {response.status_code} - {response.reason}")
            if response.status_code == 401:
                print("🔒 Authentication issue - check Azure Portal permissions")
            return response  # Return response even if error for caller to handle
        
        return response
        
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return None

def handle_outlook_api_error(response):
    """
    Extract detailed error information from Microsoft Graph API responses for Outlook
    """
    print("=== OUTLOOK GRAPH API ERROR DETAILS ===")
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
    
    print("=============================================\n")


def create_outlook_category(access_token, category_name):
    """Create an Outlook category if it doesn't exist."""
    
    # Check if category exists
    url = "https://graph.microsoft.com/v1.0/me/outlook/masterCategories"
    response = make_graph_request(access_token, url, method='GET')
    
    if response and response.status_code == 200:
        categories = response.json().get('value', [])
        for category in categories:
            if category['displayName'] == category_name:
                return category['displayName']
    
    # Create new category
    category_data = {
        "displayName": category_name,
        "color": "preset2"  # Green color
    }
    
    create_response = make_graph_request(access_token, url, method='POST', data=category_data)
    if create_response and create_response.status_code == 201:
        return create_response.json()['displayName']
    else:
        print(f"Failed to create category: {category_name}")
        return None


def get_email_details(access_token, email_id):
    """Fetch email details including subject, sender, and content."""
    
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
    """
    Save fetched emails to a JSON file
    
    Args:
        user_id: The user ID to create a unique filename
        emails: List of email objects to save
    """
    try:
        # Create data directory if it doesn't exist
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'emails')
        os.makedirs(data_dir, exist_ok=True)
        
        # Create filename with timestamp and user ID
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"emails_{user_id}_{timestamp}.json"
        filepath = os.path.join(data_dir, filename)
        
        # Prepare data to save
        email_data = {
            'user_id': user_id,
            'fetch_timestamp': datetime.now().isoformat(),
            'email_count': len(emails),
            'emails': emails
        }
        
        # Save to JSON file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(email_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Emails saved to: {filepath}")
        return filepath
        
    except Exception as e:
        print(f"❌ Error saving emails to JSON: {str(e)}")
        return None


def load_emails_from_json(user_id, latest=True):
    """
    Load emails from JSON file
    
    Args:
        user_id: The user ID to load emails for
        latest: If True, loads the most recent file for the user
    
    Returns:
        Dictionary with email data or None if not found
    """
    try:
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'emails')
        
        if not os.path.exists(data_dir):
            print(f"📁 Email data directory not found: {data_dir}")
            return None
        
        # Find files for the user
        user_files = []
        for filename in os.listdir(data_dir):
            if filename.startswith(f"emails_{user_id}_") and filename.endswith('.json'):
                filepath = os.path.join(data_dir, filename)
                user_files.append(filepath)
        
        if not user_files:
            print(f"📧 No email files found for user: {user_id}")
            return None
        
        # Get the latest file if requested
        if latest:
            user_files.sort(key=os.path.getmtime, reverse=True)
            filepath = user_files[0]
        else:
            filepath = user_files[0]  # Just get the first one
        
        # Load and return the email data
        with open(filepath, 'r', encoding='utf-8') as f:
            email_data = json.load(f)
        
        print(f"📧 Loaded {email_data.get('email_count', 0)} emails from: {os.path.basename(filepath)}")
        return email_data
        
    except Exception as e:
        print(f"❌ Error loading emails from JSON: {str(e)}")
        return None


def get_stored_email_files(user_id=None):
    """
    Get list of stored email files
    
    Args:
        user_id: Optional user ID to filter files for specific user
        
    Returns:
        List of dictionaries with file information
    """
    try:
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'emails')
        
        if not os.path.exists(data_dir):
            return []
        
        files_info = []
        for filename in os.listdir(data_dir):
            if filename.endswith('.json'):
                # Filter by user if specified
                if user_id and not filename.startswith(f"emails_{user_id}_"):
                    continue
                
                filepath = os.path.join(data_dir, filename)
                try:
                    # Extract info from filename
                    parts = filename.replace('.json', '').split('_')
                    if len(parts) >= 4:
                        file_user_id = '_'.join(parts[1:-2])  # Handle UUIDs with dashes
                        date_part = parts[-2]
                        time_part = parts[-1]
                        
                        # Get file stats
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
                    print(f"Error parsing file {filename}: {e}")
        
        # Sort by modification time (newest first)
        files_info.sort(key=lambda x: x['modified_time'], reverse=True)
        return files_info
        
    except Exception as e:
        print(f"❌ Error getting stored email files: {str(e)}")
        return []





def mark_email_with_category(access_token, email_id, category_name):
    """Mark an email with a specific category."""
    
    # Get current email to preserve existing categories
    url = f"https://graph.microsoft.com/v1.0/me/messages/{email_id}"
    response = make_graph_request(access_token, url, method='GET')
    
    if response and response.status_code == 200:
        email_data = response.json()
        current_categories = email_data.get('categories', [])
        
        # Add the new category if not already present
        if category_name not in current_categories:
            current_categories.append(category_name)
        
        # Update the email with the new categories
        update_data = {
            "categories": current_categories
        }
        
        update_response = make_graph_request(access_token, url, method='PATCH', data=update_data)
        return update_response and update_response.status_code == 200
    
    return False


def extract_email_content(email_body, body_type):
    """Extract plain text content from email body."""
    if body_type == 'html':
        # Simple HTML tag removal (you might want to use a proper HTML parser)
        import re
        text = re.sub('<[^<]+?>', '', email_body)
        return text.strip()
    else:
        return email_body.strip()
def fetch_emails_with_mime(user_id, days=7):
    """
    Fetch emails from Outlook inbox, including raw MIME content.
    
    Args:
        user_id: The user ID to fetch emails for
        days: Number of days to look back for emails (default: 7)
    
    Returns:
        List of email objects with id, subject, content, date, and MIME content
    """
    print(f"\n📧 FETCHING EMAILS + MIME FOR USER: {user_id[:8]}...")
    access_token = get_token_from_cache(user_id)
    if not access_token:
        print("❌ No valid access token found")
        return []

    try:
        # Calculate the date range
        date_from = (datetime.now() - timedelta(days=days)).isoformat() + 'Z'
        
        # Query for emails from the specified time period
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

            print(f"✅ Found {len(emails_data)} emails from last {days} days")
            for email_data in emails_data:
                email_id = email_data['id']

                # Fetch MIME for each email
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
                
                # Display email info in terminal
                print(f"  📨 {email['subject'][:50]}...")
                print(f"     From: {email['sender']}")
                print(f"     Date: {email['receivedDateTime']}")
                print(f"     MIME: {'✅ Retrieved' if mime_content else '❌ Failed'}")
                print("")

            # Save emails to JSON file
            filepath = save_emails_to_json(user_id, emails)
            if filepath:
                print(f"💾 Emails (with MIME) saved to: {filepath}")

            return emails
            
        elif response and response.status_code == 401:
            print("⚠️ Authentication error - trying beta endpoint...")
            # Try beta endpoint
            beta_url = "https://graph.microsoft.com/beta/me/mailFolders/inbox/messages"
            beta_response = make_graph_request(access_token, beta_url, method='GET', params=params)
            
            if beta_response and beta_response.status_code == 200:
                emails_data = beta_response.json().get('value', [])
                emails = []
                
                print(f"✅ Found {len(emails_data)} emails via beta endpoint")
                for email_data in emails_data:
                    email_id = email_data['id']

                    # Fetch MIME for each email
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
                    
                    # Display email info in terminal
                    print(f"  📨 {email['subject'][:50]}...")
                    print(f"     From: {email['sender']}")
                    print(f"     Date: {email['receivedDateTime']}")
                    print(f"     MIME: {'✅ Retrieved' if mime_content else '❌ Failed'}")
                    print("")
                
                # Save emails to JSON file
                filepath = save_emails_to_json(user_id, emails)
                if filepath:
                    print(f"💾 Emails (with MIME) saved to: {filepath}")
                
                return emails
            else:
                print("❌ Both v1.0 and beta endpoints failed - Permission issue")
                print("🔧 SOLUTION: Configure application permissions in Azure Portal:")
                print("   1. Go to Azure Portal → App registrations → Rundown")
                print("   2. Add Application permissions for Mail.Read and Mail.ReadWrite")
                print("   3. Grant admin consent")
                return []
        else:
            print("❌ Email fetch failed - Permission issue")
            print("🔧 SOLUTION: Configure application permissions in Azure Portal")
            handle_outlook_api_error(response)
            return []

    except Exception as e:
        print(f"❌ Error fetching emails with MIME: {str(e)}")
        return []
