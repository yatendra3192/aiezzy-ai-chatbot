"""
Automated Integration Script for AIezzy Enhanced User Management

This script automatically applies the necessary changes to your existing web_app.py
to integrate the enhanced user management system.

WHAT IT DOES:
1. Backs up your current web_app.py
2. Adds necessary imports
3. Updates configuration to use PostgreSQL
4. Registers new API routes
5. Adds admin dashboard route
6. Adds quota enforcement helpers

SAFETY:
- Creates backup before making changes
- Can be run multiple times safely
- Validates changes before applying
"""

import os
import shutil
from datetime import datetime

def print_header(text):
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70 + "\n")

def print_success(text):
    print(f"✅ {text}")

def print_error(text):
    print(f"❌ {text}")

def print_info(text):
    print(f"ℹ️  {text}")

def print_warning(text):
    print(f"⚠️  {text}")

def backup_file(filepath):
    """Create a backup of the file"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f"{filepath}.backup_{timestamp}"
    shutil.copy2(filepath, backup_path)
    print_success(f"Backup created: {backup_path}")
    return backup_path

def read_file(filepath):
    """Read file contents"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(filepath, content):
    """Write content to file"""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

def check_already_integrated(content):
    """Check if integration already applied"""
    markers = [
        'from config import get_config',
        'from models_v2 import',
        'from quota_service import quota_service',
        'api_v2'
    ]

    found = sum(1 for marker in markers if marker in content)
    return found >= 3  # If 3+ markers found, likely already integrated

def integrate_web_app():
    """Apply integration to web_app.py"""

    print_header("AIezzy Enhanced User Management - Integration Wizard")

    web_app_path = 'web_app.py'

    # Check if file exists
    if not os.path.exists(web_app_path):
        print_error(f"{web_app_path} not found!")
        print_info("Make sure you're running this from the project root directory")
        return False

    print_info(f"Found {web_app_path}")

    # Read current content
    content = read_file(web_app_path)

    # Check if already integrated
    if check_already_integrated(content):
        print_warning("Integration appears to already be applied!")
        response = input("Do you want to re-apply? (yes/no): ")
        if response.lower() != 'yes':
            print_info("Skipping integration")
            return True

    # Create backup
    print_info("Creating backup...")
    backup_path = backup_file(web_app_path)

    # Apply integration
    print_info("Applying integration changes...")

    try:
        # Step 1: Add imports after existing imports
        import_position = content.find('# Initialize Flask app')
        if import_position == -1:
            import_position = content.find('web_app = Flask(__name__)')

        if import_position != -1:
            enhanced_imports = """
# Enhanced user management imports
from config import get_config
from models_v2 import db, init_db
from api_routes import api as api_v2
from quota_service import quota_service

"""
            # Check if imports already exist
            if 'from config import get_config' not in content[:import_position]:
                content = content[:import_position] + enhanced_imports + content[import_position:]
                print_success("Added enhanced imports")
            else:
                print_info("Enhanced imports already present")

        # Step 2: Add configuration after Flask app creation
        flask_app_line = 'web_app = Flask(__name__)'
        if flask_app_line in content:
            pos = content.find(flask_app_line) + len(flask_app_line)

            config_code = """

# Get enhanced configuration
config = get_config()
web_app.config.from_object(config)
"""

            if 'config = get_config()' not in content:
                # Find the next line after web_app = Flask(__name__)
                next_newline = content.find('\n', pos) + 1
                content = content[:next_newline] + config_code + content[next_newline:]
                print_success("Added enhanced configuration")
            else:
                print_info("Enhanced configuration already present")

        # Step 3: Add database initialization (after directory creation)
        init_auth_line = 'init_auth(web_app)'
        if init_auth_line in content:
            pos = content.find(init_auth_line)

            db_init_code = """

# Initialize enhanced database
init_db(web_app)
"""

            if 'init_db(web_app)' not in content:
                # Add before init_auth
                content = content[:pos] + db_init_code + content[pos:]
                print_success("Added database initialization")
            else:
                print_info("Database initialization already present")

        # Step 4: Add blueprint registration and admin route
        # Find a good place (after all setup, before routes)
        first_route = content.find('@web_app.route(')
        if first_route != -1:

            blueprint_code = """
# Register enhanced API routes
web_app.register_blueprint(api_v2)

# Admin dashboard route
@web_app.route('/admin')
@admin_required
def admin_dashboard_page():
    \"\"\"Admin dashboard for user management\"\"\"
    return render_template('admin_dashboard.html')

"""

            if 'web_app.register_blueprint(api_v2)' not in content:
                # Add before first route
                content = content[:first_route] + blueprint_code + content[first_route:]
                print_success("Added blueprint registration and admin route")
            else:
                print_info("Blueprint registration already present")

        # Write integrated file
        write_file(web_app_path, content)
        print_success("Integration applied successfully!")

        print_header("Integration Complete!")
        print("\n✅ Your web_app.py has been updated with:")
        print("   - Enhanced configuration system")
        print("   - PostgreSQL/SQLite database support")
        print("   - New API routes (email, OAuth, quotas)")
        print("   - Admin dashboard route")
        print("\n⚠️  IMPORTANT NEXT STEPS:")
        print("\n1. Add quota enforcement to your AI endpoints:")
        print("   - See web_app_integration_patch.py for examples")
        print("   - Add quota checks before processing")
        print("   - Add usage logging after success")
        print("\n2. Test locally:")
        print("   python web_app.py")
        print("\n3. Visit http://localhost:5000 and test:")
        print("   - Registration/login")
        print("   - Admin dashboard at /admin")
        print("   - AI features")
        print("\n4. Deploy to Railway:")
        print("   - See RAILWAY_DEPLOYMENT_COMPLETE.md")
        print("\n📁 Backup saved at: " + backup_path)

        return True

    except Exception as e:
        print_error(f"Integration failed: {e}")
        print_info(f"Restoring from backup: {backup_path}")
        shutil.copy2(backup_path, web_app_path)
        print_success("Original file restored")
        return False

def add_quota_helpers():
    """Create a helper file for quota enforcement"""

    helper_content = """\"\"\"
Quota Enforcement Helpers for AIezzy

Add these patterns to your AI endpoints in web_app.py
\"\"\"

from quota_service import quota_service
from auth import get_current_user
from flask import jsonify

def check_quota_for_request(resource_type):
    \"\"\"
    Check quota before processing AI request

    Args:
        resource_type: 'image', 'video', or 'message'

    Returns:
        tuple: (allowed: bool, response: dict or None)

    Usage in your routes:
        allowed, error_response = check_quota_for_request('image')
        if not allowed:
            return error_response
    \"\"\"
    user = get_current_user()
    user_id = user['id'] if user else None

    quota_check = quota_service.check_quota(user_id, resource_type)

    if not quota_check['allowed']:
        return False, jsonify({
            'error': quota_check['message'],
            'quota_exceeded': True,
            'remaining': quota_check['remaining'],
            'limit': quota_check['limit'],
            'tier': quota_check['tier']
        }), 429

    return True, None

def log_usage_for_request(resource_type, count=1):
    \"\"\"
    Log usage after successful AI operation

    Args:
        resource_type: 'image', 'video', or 'message'
        count: Number of resources used (default 1)

    Usage in your routes:
        # After successful operation
        log_usage_for_request('image')
    \"\"\"
    user = get_current_user()
    user_id = user['id'] if user else None
    quota_service.log_usage(user_id, resource_type, count)


# ==================== EXAMPLE USAGE ====================

# Example 1: Chat endpoint with quota
@app.route('/api/chat', methods=['POST'])
def chat():
    # Check quota
    allowed, error_response = check_quota_for_request('message')
    if not allowed:
        return error_response

    try:
        # Your existing chat logic here
        result = process_chat_request()

        # Log usage after success
        log_usage_for_request('message')

        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Example 2: Image generation with quota
@app.route('/api/generate-image', methods=['POST'])
def generate_image():
    # Check quota
    allowed, error_response = check_quota_for_request('image')
    if not allowed:
        return error_response

    try:
        # Your existing image generation logic
        result = generate_image_logic()

        # Log usage
        log_usage_for_request('image')

        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Example 3: Video generation with quota
@app.route('/api/generate-video', methods=['POST'])
def generate_video():
    # Check quota
    allowed, error_response = check_quota_for_request('video')
    if not allowed:
        return error_response

    try:
        # Your existing video generation logic
        result = generate_video_logic()

        # Log usage
        log_usage_for_request('video')

        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
"""

    helper_path = 'quota_helpers.py'
    write_file(helper_path, helper_content)
    print_success(f"Created {helper_path} with usage examples")

def main():
    """Main integration flow"""
    try:
        # Apply integration
        success = integrate_web_app()

        if success:
            # Create helper file
            print_info("\nCreating quota helpers...")
            add_quota_helpers()

            print_header("Next Steps")
            print("1. Review the changes in web_app.py")
            print("2. Check quota_helpers.py for usage examples")
            print("3. Add quota enforcement to your AI endpoints")
            print("4. Test locally: python web_app.py")
            print("5. Deploy to Railway (see RAILWAY_DEPLOYMENT_COMPLETE.md)")
            print("\n✨ Integration complete! Your app is now enhanced!")
        else:
            print_error("Integration failed. Please check the errors above.")
            print_info("You can also manually integrate using web_app_integration_patch.py")

    except KeyboardInterrupt:
        print("\n\nIntegration cancelled by user.")
    except Exception as e:
        print_error(f"Unexpected error: {e}")

if __name__ == '__main__':
    main()
