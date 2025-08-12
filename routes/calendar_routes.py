from flask import Blueprint, jsonify, session, redirect, request, current_app
from utils.calendar import fetch_calendar_events, delete_calendar_event
from utils.auth import require_auth
import traceback

calendar_bp = Blueprint('calendar', __name__)

@calendar_bp.route('/calendar', methods=['GET', 'OPTIONS'])
@require_auth
def calendar_events_route():
    # Handle CORS preflight requests
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        user_id = session.get('user_id')
        if not user_id:
            print("No user_id in session")
            return jsonify({"error": "Authentication required", "redirect": "/login"}), 401
            
        events = fetch_calendar_events(user_id)
        return jsonify({"events": events})
    except Exception as e:
        print(f"Unexpected error: {e}")
        print(traceback.format_exc())
        
        # Check if it's a permission error
        if "PERMISSION_ERROR" in str(e):
            return redirect('/permissions-error')
        
        return jsonify({"error": f"Server Error: {str(e)}"}), 500

@calendar_bp.route('/calendar/delete', methods=['POST', 'OPTIONS'])
@require_auth
def delete_calendar_event_route():
    """Delete a calendar event by ID."""
    # Handle CORS preflight requests
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        # Print the request details for debugging
        print(f"Delete request received: {request.json}")
        print(f"Request headers: {dict(request.headers)}")
        print(f"Session info: {dict(session)}")
        
        user_id = session.get('user_id')
        if not user_id:
            print("No user_id in session")
            return jsonify({"error": "Authentication required", "redirect": "/login"}), 401
            
        event_id = request.json.get('event_id')
        if not event_id:
            print("No event_id provided")
            return jsonify({"error": "Event ID is required"}), 400
            
        print(f"Attempting to delete calendar event {event_id} for user {user_id}")
        
        print("Calling delete_calendar_event function")
        result = delete_calendar_event(user_id, event_id)
        print(f"Delete result: {result}")
        return jsonify({"success": True, "message": "Event deleted successfully"})
    except Exception as e:
        print(f"Unexpected error in delete_calendar_event_route: {str(e)}")
        print(traceback.format_exc())
        
        if "404" in str(e):
            # If the event doesn't exist, consider it a success (already deleted)
            return jsonify({"success": True, "message": "Event already deleted"})
        return jsonify({"error": f"Server Error: {str(e)}"}), 500
