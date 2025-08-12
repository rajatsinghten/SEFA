from flask import Blueprint, jsonify, session, redirect, current_app
from utils.outlook import fetch_emails
from utils.auth import require_auth

outlook_bp = Blueprint('outlook', __name__)

@outlook_bp.route('/outlook')
@require_auth
def get_emails():
    user_id = session['user_id']
    try:
        email_details = fetch_emails(user_id)
        if email_details is None:
            return redirect('/login')
        return jsonify({'emails': email_details})
    except Exception as e:
        current_app.logger.error(f"Failed to fetch emails: {str(e)}")
        return jsonify({"error": "Failed to fetch emails"}), 500
