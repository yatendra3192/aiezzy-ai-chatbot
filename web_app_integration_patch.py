"""
INTEGRATION PATCH FOR web_app.py

This file shows EXACTLY what to change in your existing web_app.py.
Apply these changes to integrate the enhanced user management system.

CHANGES NEEDED:
1. Add imports at the top
2. Update configuration section
3. Initialize new database
4. Register new API routes
5. Add admin dashboard route
6. Add quota enforcement to AI endpoints
"""

# ==================== STEP 1: ADD THESE IMPORTS (around line 15) ====================
# Add AFTER the existing imports, BEFORE "# Initialize Flask app"

# Enhanced user management (ADD THESE)
from config import get_config
from models_v2 import db, init_db
from api_routes import api as api_v2
from quota_service import quota_service

# Keep existing imports too:
# from models import UserManager
# from auth import login_required, admin_required, optional_auth, get_current_user, get_user_id...


# ==================== STEP 2: UPDATE CONFIGURATION (around line 20-40) ====================
# REPLACE the existing configuration section with this:

# Get enhanced configuration
config = get_config()

# Initialize Flask app (keep this line)
web_app = Flask(__name__)

# Apply configuration
web_app.config.from_object(config)

# Configure persistent storage paths for Railway
if os.environ.get('RAILWAY_ENVIRONMENT'):
    # Production: Use Railway persistent volume
    DATA_DIR = '/app/data'
else:
    # Development: Use local directories
    DATA_DIR = '.'

# Set directories using config
web_app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER
ASSETS_DIR = config.ASSETS_DIR
VIDEOS_DIR = config.VIDEOS_DIR
DOCUMENTS_DIR = config.DOCUMENTS_DIR
CONVERSATIONS_DIR = config.CONVERSATIONS_DIR

web_app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# Create directories if they don't exist
os.makedirs(web_app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)
os.makedirs(VIDEOS_DIR, exist_ok=True)
os.makedirs(DOCUMENTS_DIR, exist_ok=True)
os.makedirs(CONVERSATIONS_DIR, exist_ok=True)
os.makedirs('shared', exist_ok=True)
os.makedirs('feature_requests', exist_ok=True)
os.makedirs('permanent_files', exist_ok=True)

# Initialize enhanced database with SQLAlchemy
init_db(web_app)

# Initialize authentication (keep this)
init_auth(web_app)

# Keep old user_manager for backward compatibility (optional)
user_manager = UserManager()


# ==================== STEP 3: REGISTER NEW API ROUTES (add after all imports and setup) ====================
# Add this RIGHT BEFORE your existing routes (before @web_app.route('/')  )

# Register enhanced API routes
web_app.register_blueprint(api_v2)

# Admin dashboard route
@web_app.route('/admin')
@admin_required
def admin_dashboard_page():
    """Admin dashboard for user management"""
    return render_template('admin_dashboard.html')


# ==================== STEP 4: ADD QUOTA ENFORCEMENT TO AI ENDPOINTS ====================

# EXAMPLE 1: Update /api/chat endpoint
# FIND your existing /api/chat route and ADD quota checking:

@web_app.route('/api/chat', methods=['POST'])
@optional_auth
def chat():
    """Enhanced chat endpoint with quota enforcement"""

    # Get current user
    user = get_current_user()
    user_id = user['id'] if user else None

    # CHECK QUOTA BEFORE PROCESSING (ADD THIS)
    quota_check = quota_service.check_quota(user_id, 'message')
    if not quota_check['allowed']:
        return jsonify({
            'error': quota_check['message'],
            'quota_exceeded': True,
            'remaining': quota_check['remaining'],
            'limit': quota_check['limit'],
            'tier': quota_check['tier']
        }), 429  # Too Many Requests

    # ... rest of your existing chat logic ...

    try:
        # Your existing chat processing code here
        # ...

        # LOG USAGE AFTER SUCCESSFUL COMPLETION (ADD THIS)
        quota_service.log_usage(user_id, 'message', 1)

        return jsonify(response)

    except Exception as e:
        # Your existing error handling
        return jsonify({'error': str(e)}), 500


# EXAMPLE 2: Update image generation endpoint
# FIND your image generation route and ADD:

@web_app.route('/api/generate-image', methods=['POST'])
@optional_auth
def generate_image():
    """Image generation with quota enforcement"""

    user = get_current_user()
    user_id = user['id'] if user else None

    # CHECK QUOTA (ADD THIS)
    quota_check = quota_service.check_quota(user_id, 'image')
    if not quota_check['allowed']:
        return jsonify({
            'error': quota_check['message'],
            'quota_exceeded': True
        }), 429

    try:
        # Your existing image generation code
        # ...

        # LOG USAGE (ADD THIS)
        quota_service.log_usage(user_id, 'image', 1)

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# EXAMPLE 3: Update video generation endpoint
# Similar pattern for video:

@web_app.route('/api/generate-video', methods=['POST'])
@optional_auth
def generate_video():
    """Video generation with quota enforcement"""

    user = get_current_user()
    user_id = user['id'] if user else None

    # CHECK QUOTA (ADD THIS)
    quota_check = quota_service.check_quota(user_id, 'video')
    if not quota_check['allowed']:
        return jsonify({
            'error': quota_check['message'],
            'quota_exceeded': True
        }), 429

    try:
        # Your existing video generation code
        # ...

        # LOG USAGE (ADD THIS)
        quota_service.log_usage(user_id, 'video', 1)

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== SUMMARY OF CHANGES ====================
"""
1. Added imports for config, models_v2, api_routes, quota_service
2. Updated configuration to use get_config()
3. Initialized SQLAlchemy database with init_db(web_app)
4. Registered api_v2 blueprint for new routes
5. Added /admin route for admin dashboard
6. Added quota checking before AI operations
7. Added usage logging after successful AI operations

KEY POINTS:
- All existing functionality preserved
- Quota enforcement is optional (returns 429 if exceeded)
- Guest users still work (user_id = None)
- Old auth system can coexist with new system
- Database auto-migrates on first run

TESTING:
1. Start app: python web_app.py
2. Test registration: http://localhost:5000/api/v2/register
3. Test quota: http://localhost:5000/api/v2/quota/status
4. Test admin: http://localhost:5000/admin
"""

# ==================== QUICK REFERENCE ====================
"""
QUOTA CHECK PATTERN:
    quota_check = quota_service.check_quota(user_id, 'image')  # or 'video', 'message'
    if not quota_check['allowed']:
        return jsonify({'error': quota_check['message']}), 429

USAGE LOGGING PATTERN:
    quota_service.log_usage(user_id, 'image', 1)  # or 'video', 'message'

TIER LIMITS (customizable in .env):
    Free:       20 images, 5 videos, 100 messages/day
    Pro:        200 images, 50 videos, 1000 messages/day
    Enterprise: Unlimited
"""
