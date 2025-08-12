# backend/utils/outlook.py
import json
import requests
from datetime import datetime, timedelta
from utils.auth import get_token_from_cache


def create_outlook_category(access_token, category_name):
    """Create an Outlook category if it doesn't exist."""
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    # Check if category exists
    url = "https://graph.microsoft.com/v1.0/me/outlook/masterCategories"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        categories = response.json().get('value', [])
        for category in categories:
            if category['displayName'] == category_name:
                return category['displayName']
    
    # Create new category
    category_data = {
        "displayName": category_name,
        "color": "preset2"  # Green color
    }
    
    response = requests.post(url, headers=headers, json=category_data)
    if response.status_code == 201:
        return response.json()['displayName']
    else:
        print(f"Failed to create category: {response.status_code} - {response.text}")
        return None


def get_email_details(access_token, email_id):
    """Fetch email details including subject, sender, and content."""
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    url = f"https://graph.microsoft.com/v1.0/me/messages/{email_id}"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
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
        return {'error': f'Failed to fetch email: {response.status_code}'}


def fetch_emails(user_id, days=7):
    """
    Fetch emails from Outlook inbox
    
    Args:
        user_id: The user ID to fetch emails for
        days: Number of days to look back for emails (default: 7)
    
    Returns:
        List of email objects with id, subject, content, and date
    """
    print(f"\n===== FETCHING EMAILS FOR USER {user_id} =====")
    access_token = get_token_from_cache(user_id)
    if not access_token:
        print(f"No valid access token for user {user_id}")
        # Return error dictionary instead of None for better debugging
        return {'error': 'Authentication error', 'message': 'No valid access token available'}
    
    # Verify token format
    print(f"Access token obtained (first 10 chars): {access_token[:10]}...")
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    try:
        # Calculate the date range
        date_from = (datetime.now() - timedelta(days=days)).isoformat() + 'Z'
        print(f"Fetching emails since: {date_from}")
        
        # Query for emails from the specified time period
        url = "https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages"
        params = {
            '$filter': f"receivedDateTime ge {date_from}",
            '$top': 10,
            '$orderby': 'receivedDateTime desc',
            '$select': 'id,subject,from,receivedDateTime,body,categories'  # Specify fields to reduce response size
        }
        
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            emails_data = response.json().get('value', [])
            emails = []
            
            print(f"Found {len(emails_data)} emails")
            for email_data in emails_data:
                emails.append({
                    'id': email_data['id'],
                    'subject': email_data.get('subject', 'No Subject'),
                    'sender': email_data.get('from', {}).get('emailAddress', {}).get('address', 'Unknown Sender'),
                    'content': email_data.get('body', {}).get('content', 'No content available'),
                    'bodyType': email_data.get('body', {}).get('contentType', 'text'),
                    'receivedDateTime': email_data.get('receivedDateTime', ''),
                    'categories': email_data.get('categories', [])
                })
            
            return emails
        elif response.status_code == 401:
            print(f"Error fetching emails: {response.status_code} - {response.text}")
            return {'error': 'PERMISSION_ERROR', 'message': 'Microsoft Graph API access denied. Application permissions may need to be re-consented.'}
        else:
            print(f"Error fetching emails: {response.status_code} - {response.text}")
            return {'error': f'Failed to fetch emails: {response.status_code}'}
            
    except Exception as e:
        print(f"Error fetching emails: {str(e)}")
        return {'error': str(e)}


def mark_email_with_category(access_token, email_id, category_name):
    """Mark an email with a specific category."""
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    # Get current email to preserve existing categories
    url = f"https://graph.microsoft.com/v1.0/me/messages/{email_id}"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        email_data = response.json()
        current_categories = email_data.get('categories', [])
        
        # Add the new category if not already present
        if category_name not in current_categories:
            current_categories.append(category_name)
        
        # Update the email with the new categories
        update_data = {
            "categories": current_categories
        }
        
        response = requests.patch(url, headers=headers, json=update_data)
        return response.status_code == 200
    
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
