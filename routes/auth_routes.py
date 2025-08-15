from flask import Blueprint, redirect, request, session, render_template, jsonify, make_response, url_for
from utils.auth import get_msal_app, get_auth_url, save_credentials, get_token_from_cache
from config import CLIENT_ID, SCOPES

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login')
def login():
    try:
        auth_url = get_auth_url()
        return redirect(auth_url)
    except Exception as e:
        return render_template('error.html', error=str(e))

@auth_bp.route('/force-reconsent')
def force_reconsent():
    try:
        session.clear()
        auth_url = get_auth_url()
        return redirect(auth_url)
    except Exception as e:
        return render_template('error.html', error=str(e))

@auth_bp.route('/callback')
def callback():
    try:
        auth_code = request.args.get('code')
        if not auth_code:
            return 'Authorization code not found', 400
        app = get_msal_app()
        from config import REDIRECT_URI
        result = app.acquire_token_by_authorization_code(
            auth_code,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
        if 'error' in result:
            return render_template('error.html', error=result.get('error_description'))
        user_id = result.get('id_token_claims', {}).get('oid')
        if not user_id:
            user_id = result.get('id_token_claims', {}).get('sub')
        if not user_id:
            return render_template('error.html', error="Could not get user ID from token")
        save_credentials(user_id, result)
        session['user_id'] = user_id
        session['user_email'] = result.get('id_token_claims', {}).get('preferred_username', '')
        session['user_name'] = result.get('id_token_claims', {}).get('name', '')
        session.permanent = True
        resp = make_response(redirect('/'))
        resp.set_cookie('auth_status', 'authenticated', max_age=3600)
        return resp
    except Exception as e:
        return render_template('error.html', error=str(e))

@auth_bp.route('/auth/status', methods=['GET'])
def auth_status():
    if 'user_id' in session:
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
    session.clear()
    return redirect('/login')

@auth_bp.route('/force-consent')
def force_consent():
    session.clear()
    try:
        if 'user_id' in session:
            user_id = session['user_id']
            import os
            from config import TOKENS_DIR
            token_path = os.path.join(TOKENS_DIR, f"{user_id}.json")
            if os.path.exists(token_path):
                os.remove(token_path)
        from utils.auth import get_msal_app
        from config import REDIRECT_URI, SCOPES
        app = get_msal_app()
        auth_url = app.get_authorization_request_url(
            SCOPES,
            redirect_uri=REDIRECT_URI,
            prompt="consent"
        )
        return redirect(auth_url)
    except Exception as e:
        return redirect('/login')

@auth_bp.route('/scope-changed')
def scope_changed():
    message = (
        "Our application has been updated with new features that require additional permissions. "
        "Specifically, we've added calendar event management capabilities. "
        "Please log in again to continue using RunDown with all features."
    )
    return render_template('error.html', error=message, retry_url=url_for('auth.login'))

@auth_bp.route('/permissions-error')
def permissions_error():
    return render_template('permissions_error.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    resp = make_response(redirect('/'))
    resp.set_cookie('auth_status', '', expires=0)
    resp.set_cookie('session_started', '', expires=0)
    return resp
