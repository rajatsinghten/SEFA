from flask import Blueprint, redirect, request, session, render_template, jsonify, make_response, url_for
import traceback
from utils.auth import get_msal_app, get_auth_url, save_credentials, get_token_from_cache
from config import CLIENT_ID, SCOPES

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login')
def login():
    try:
        auth_url = get_auth_url()
        return redirect(auth_url)
    except Exception as e:
        print(f"Error in login route: {str(e)}")
        print(traceback.format_exc())
        return render_template('error.html', error=str(e))

@auth_bp.route('/force-reconsent')
def force_reconsent():
    """Force a new consent flow to update permissions"""
    try:
        # Clear existing session
        session.clear()
        
        # Get auth URL with forced consent
        auth_url = get_auth_url()
        return redirect(auth_url)
    except Exception as e:
        print(f"Error in force-reconsent route: {str(e)}")
        print(traceback.format_exc())
        return render_template('error.html', error=str(e))

@auth_bp.route('/callback')
def callback():
    try:
        # Get the authorization code from the callback
        auth_code = request.args.get('code')
        if not auth_code:
            return 'Authorization code not found', 400
        
        # Exchange the code for tokens
        app = get_msal_app()
        # Use explicit redirect URI from config
        from config import REDIRECT_URI
        
        # Print debug information in the callback
        print("\n====== OAUTH CALLBACK DEBUG INFO ======")
        print(f"Received auth code: {auth_code[:5]}...")
        print(f"Using Redirect URI: {REDIRECT_URI}")
        print("=====================================\n")
        
        result = app.acquire_token_by_authorization_code(
            auth_code,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
        
        if 'error' in result:
            print(f"Error in token exchange: {result.get('error_description')}")
            return render_template('error.html', error=result.get('error_description'))
        
        # Get user information from the token
        user_id = result.get('id_token_claims', {}).get('oid')  # Object ID
        if not user_id:
            user_id = result.get('id_token_claims', {}).get('sub')  # Subject as fallback
        
        if not user_id:
            return render_template('error.html', error="Could not get user ID from token")
        
        # Save credentials and set session
        save_credentials(user_id, result)
        session['user_id'] = user_id
        session['user_email'] = result.get('id_token_claims', {}).get('preferred_username', '')
        session['user_name'] = result.get('id_token_claims', {}).get('name', '')
        session.permanent = True
        
        print(f"User authenticated: {user_id} ({session['user_email']})")
        
        # Show email endpoint information in terminal
        print("\n" + "="*60)
        print("🎉 USER SUCCESSFULLY AUTHENTICATED!")
        print(f"👤 User: {session['user_name']} ({session['user_email']})")
        print("="*60)
        print("📧 EMAIL ENDPOINTS AVAILABLE:")
        print(f"   GET http://localhost:5000/outlook")
        print(f"   🔗 Access directly: curl http://localhost:5000/outlook")
        print("="*60)
        print("💡 The application will now fetch and store emails in JSON format")
        print("📁 Email data will be saved to: data/emails/")
        print("="*60 + "\n")
        
        # Set a cookie to track successful authentication
        resp = make_response(redirect('/'))
        resp.set_cookie('auth_status', 'authenticated', max_age=3600)
        return resp
    except Exception as e:
        print(f"Error in OAuth callback: {str(e)}")
        print(traceback.format_exc())
        return render_template('error.html', error=str(e))

@auth_bp.route('/auth/status', methods=['GET'])
def auth_status():
    """Check authentication status and return user info if authenticated."""
    if 'user_id' in session:
        # Check if token is valid
        user_id = session['user_id']
        token = get_token_from_cache(user_id)
        if token:
            return jsonify({
                "authenticated": True,
                "user_id": user_id,
                "user_email": session.get('user_email', ''),
                "user_name": session.get('user_name', '')
            })
        else:
            # Token is invalid or expired
            print(f"Invalid token for user {user_id}")
            session.clear()
            return jsonify({
                "authenticated": False,
                "error": "Token expired",
                "message": "Your session has expired. Please log in again."
            }), 401
    
    return jsonify({
        "authenticated": False
    }), 401

@auth_bp.route('/refresh-auth')
def refresh_auth():
    """Force re-authentication when token is invalid."""
    session.clear()
    return redirect('/login')

@auth_bp.route('/force-consent')
def force_consent():
    """Force re-authentication with consent prompt to ensure all permissions are granted."""
    session.clear()
    try:
        # Clear any cached tokens
        if 'user_id' in session:
            user_id = session['user_id']
            # You might want to delete the token file here
            import os
            from config import TOKENS_DIR
            token_path = os.path.join(TOKENS_DIR, f"{user_id}.json")
            if os.path.exists(token_path):
                os.remove(token_path)
        
        # Generate auth URL with forced consent
        from utils.auth import get_msal_app
        from config import REDIRECT_URI, SCOPES
        
        app = get_msal_app()
        auth_url = app.get_authorization_request_url(
            SCOPES,
            redirect_uri=REDIRECT_URI,
            prompt="consent"  # Force consent screen
        )
        return redirect(auth_url)
    except Exception as e:
        print(f"Error in force consent: {str(e)}")
        return redirect('/login')

@auth_bp.route('/scope-changed')
def scope_changed():
    """Inform the user that application permissions have changed and they need to re-authenticate."""
    message = (
        "Our application has been updated with new features that require additional permissions. "
        "Specifically, we've added calendar event management capabilities. "
        "Please log in again to continue using RunDown with all features."
    )
    return render_template('error.html', error=message, retry_url=url_for('auth.login'))

@auth_bp.route('/permissions-error')
def permissions_error():
    """Show permissions error page with instructions to fix permission issues."""
    return render_template('permissions_error.html')

@auth_bp.route('/logout')
def logout():
    # Clear all session data
    session.clear()
    resp = make_response(redirect('/'))
    # Clear cookies
    resp.set_cookie('auth_status', '', expires=0)
    resp.set_cookie('session_started', '', expires=0)
    return resp
