from flask import Blueprint, jsonify, session, request, render_template
from utils.auth import require_auth
from utils.models import UserPreferences

preferences_bp = Blueprint('preferences', __name__)

AVAILABLE_CATEGORIES = [
    # Professional & Academic
    "Academics",
    "Internship",
    "Hackathon",
    "Meetings",
    "Workshops",
    "Conferences",
    "Webinars",
    "Networking Events",
    "Career Fairs",
    "Project Deadlines",
    "Professional Development",
    "Research Opportunities",

    # Social & Community
    "Cultural Events",
    "Sports Events",
    "Social Events",
    "Charity Events",
    "Volunteer Opportunities",
    "Clubs & Organizations",
    
    # Personal & Wellness
    "Health & Wellness",
    "Fitness",
    "Doctor Appointments",
    "Family & Friends",
    "Birthdays",
    "Anniversaries",
    
    # Errands & Finance
    "Personal Errands",
    "Groceries",
    "Bill Payments",
    "Personal Finance",
    
    # Leisure & Travel
    "Hobbies",
    "Travel",
    "Bookings"
]

@preferences_bp.route('/preferences')
@require_auth
def preferences_page():
    user_id = session.get('user_id')
    user_preferences = UserPreferences.load_preferences(user_id)
    return render_template('preferences.html', 
                          categories=AVAILABLE_CATEGORIES,
                          user_preferences=user_preferences)

@preferences_bp.route('/api/preferences', methods=['GET'])
@require_auth
def get_preferences():
    user_id = session.get('user_id')
    try:
        preferences = UserPreferences.load_preferences(user_id)
        return jsonify(preferences)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@preferences_bp.route('/api/preferences', methods=['POST'])
@require_auth
def update_preferences():
    user_id = session.get('user_id')
    try:
        data = request.json
        interests = data.get('interests', [])
        custom_interests = data.get('custom_interests', [])
        
        for interest in interests:
            if interest not in AVAILABLE_CATEGORIES and interest not in custom_interests:
                return jsonify({"error": f"Invalid interest: {interest}"}), 400
                
        all_interests = list(set(interests + custom_interests))
        
        preferences = {
            "interests": all_interests,
            "custom_interests": custom_interests,
            "enabled": data.get('enabled', True)
        }
        
        UserPreferences.update_preferences(user_id, preferences)
        return jsonify({"success": True, "preferences": preferences})
    except Exception as e:
        return jsonify({"error": str(e)}), 500