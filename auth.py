"""
Authentication utilities and decorators for AIezzy web application.
Provides session management, authentication decorators, and utility functions.
"""

from functools import wraps
from flask import request, jsonify, session, g
from models import UserManager
import time

# Initialize user manager
user_manager = UserManager()

def get_client_ip():
    """Get client IP address considering proxy headers"""
    if request.environ.get('HTTP_X_FORWARDED_FOR'):
        return request.environ['HTTP_X_FORWARDED_FOR'].split(',')[0].strip()
    elif request.environ.get('HTTP_X_REAL_IP'):
        return request.environ['HTTP_X_REAL_IP']
    else:
        return request.environ.get('REMOTE_ADDR')

def get_user_agent():
    """Get client user agent"""
    return request.headers.get('User-Agent', '')

def get_current_user():
    """Get current authenticated user from session or token"""
    # Check session token in multiple places
    session_token = None
    
    # 1. Check Authorization header
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        session_token = auth_header[7:]  # Remove 'Bearer ' prefix
    
    # 2. Check session cookie
    if not session_token:
        session_token = session.get('session_token')
    
    # 3. Check form data or JSON for token
    if not session_token:
        if request.is_json:
            data = request.get_json(silent=True)
            session_token = data.get('session_token') if data else None
        else:
            session_token = request.form.get('session_token')
    
    # 4. Check query parameter (less secure, but useful for some cases)
    if not session_token:
        session_token = request.args.get('session_token')
    
    if session_token:
        user = user_manager.get_user_by_session(session_token)
        if user:
            # Store in g for easy access during request
            g.current_user = user
            g.session_token = session_token
            return user
    
    return None

def login_required(f):
    """Decorator that requires user authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'error': 'Authentication required'}), 401
            else:
                # For web pages, redirect to login
                from flask import redirect, url_for
                return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator that requires admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'error': 'Authentication required'}), 401
            else:
                from flask import redirect, url_for
                return redirect(url_for('login_page'))
        
        if not user.get('is_admin', False):
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'error': 'Admin privileges required'}), 403
            else:
                from flask import abort
                abort(403)
        
        return f(*args, **kwargs)
    return decorated_function

def optional_auth(f):
    """Decorator that allows optional authentication (user can be None)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        # User will be None if not authenticated, which is fine
        return f(*args, **kwargs)
    return decorated_function

def get_user_id():
    """Get current user ID or default to 'default_user' for backward compatibility"""
    user = get_current_user()
    if user:
        return str(user['id'])
    else:
        # For backward compatibility with existing conversations
        return 'default_user'

def create_session(user_data, session_token):
    """Helper to create session in Flask session"""
    session['session_token'] = session_token
    session['user_id'] = user_data['id']
    session['username'] = user_data['username']
    session['logged_in'] = True
    session.permanent = True  # Make session permanent (respects app.permanent_session_lifetime)

def clear_session():
    """Helper to clear session data"""
    session.pop('session_token', None)
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('logged_in', None)

def rate_limit_check(key, limit=5, window=300):
    """Simple rate limiting - returns True if allowed, False if rate limited"""
    # This is a simple in-memory rate limiter
    # In production, you'd want to use Redis or similar
    import time
    
    if not hasattr(rate_limit_check, 'attempts'):
        rate_limit_check.attempts = {}
    
    now = time.time()
    
    # Clean old entries
    rate_limit_check.attempts = {
        k: v for k, v in rate_limit_check.attempts.items() 
        if now - v[0] < window
    }
    
    if key in rate_limit_check.attempts:
        first_attempt, count = rate_limit_check.attempts[key]
        if now - first_attempt < window:
            if count >= limit:
                return False
            rate_limit_check.attempts[key] = (first_attempt, count + 1)
        else:
            rate_limit_check.attempts[key] = (now, 1)
    else:
        rate_limit_check.attempts[key] = (now, 1)
    
    return True

def validate_password_strength(password):
    """Validate password strength requirements - simplified"""
    errors = []
    
    if len(password) < 1:
        errors.append("Password is required")
    
    # No other requirements - users can use any password they like
    return errors

def sanitize_username(username):
    """Sanitize username input"""
    import re
    # Only allow alphanumeric, underscore, and hyphen
    username = re.sub(r'[^a-zA-Z0-9_-]', '', username.strip())
    return username.lower()

def is_valid_email(email):
    """Simple email validation"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

# Context processor to make current user available in templates
def inject_user():
    """Make current user available in all templates"""
    return dict(current_user=get_current_user())

def init_auth(app):
    """Initialize authentication for Flask app"""
    from datetime import timedelta
    
    # Set session lifetime
    app.permanent_session_lifetime = timedelta(days=30)
    
    # Add context processor
    app.context_processor(inject_user)
    
    # Make sure we have a secret key
    if not app.config.get('SECRET_KEY'):
        import os
        app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
        print("Warning: Using default secret key. Set SECRET_KEY environment variable for production.")

# Test function for development
def test_auth():
    """Test authentication system"""
    print("Testing authentication system...")
    
    # Test user creation
    result = user_manager.create_user('testuser', 'test@example.com', 'testpass123', 'Test User')
    print(f"Create user: {result}")
    
    if result['success']:
        # Test authentication
        auth_result = user_manager.authenticate_user('testuser', 'testpass123')
        print(f"Auth result: {auth_result}")
        
        if auth_result['success']:
            # Test session validation
            token = auth_result['session_token']
            user = user_manager.get_user_by_session(token)
            print(f"Session validation: {user}")

if __name__ == '__main__':
    test_auth()