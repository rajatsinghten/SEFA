from flask import Blueprint, jsonify, session, redirect, request, current_app
from utils.calendar import fetch_calendar_events, delete_calendar_event
from utils.auth import require_auth

calendar_bp = Blueprint('calendar', __name__)

@calendar_bp.route('/calendar', methods=['GET', 'OPTIONS'])
@require_auth
def calendar_events_route():
    if request.method == 'OPTIONS':
        return '', 200
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "Authentication required", "redirect": "/login"}), 401
        events = fetch_calendar_events(user_id)
        return jsonify({"events": events})
    except Exception as e:
        if "PERMISSION_ERROR" in str(e):
            return redirect('/permissions-error')
        return jsonify({"error": f"Server Error: {str(e)}"}), 500

@calendar_bp.route('/calendar/delete', methods=['POST', 'OPTIONS'])
@require_auth
def delete_calendar_event_route():
    if request.method == 'OPTIONS':
        return '', 200
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "Authentication required", "redirect": "/login"}), 401
        event_id = request.json.get('event_id')
        if not event_id:
            return jsonify({"error": "Event ID is required"}), 400
        result = delete_calendar_event(user_id, event_id)
        return jsonify({"success": True, "message": "Event deleted successfully"})
    except Exception as e:
        if "404" in str(e):
            return jsonify({"success": True, "message": "Event already deleted"})
        return jsonify({"error": f"Server Error: {str(e)}"}), 500
