"""
Enhanced API routes for AIezzy user management.
Includes email verification, password reset, OAuth, quotas, and admin endpoints.
"""

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, session
from datetime import datetime, timedelta
import secrets
from models_v2 import db, User, UserSession, EmailVerification, PasswordReset, OAuthAccount, UserActivity, UsageLog, DailyUsage, hash_password, verify_password
from email_service import email_service
from oauth_service import oauth_service
from quota_service import quota_service
from auth import get_current_user, admin_required, optional_auth, get_client_ip, get_user_agent
from config import get_config
from sqlalchemy import func, desc
from datetime import date

config = get_config()
api = Blueprint('api_v2', __name__)

# ==================== Authentication Routes ====================

@api.route('/api/v2/register', methods=['POST'])
def register():
    """Enhanced user registration with email verification"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        full_name = data.get('full_name', '').strip()

        # Validation
        if not email or '@' not in email:
            return jsonify({'error': 'Valid email is required'}), 400

        if not password:
            return jsonify({'error': 'Password is required'}), 400

        # Check if email exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({'error': 'Email already registered'}), 400

        # Generate username from email
        username = email.split('@')[0]
        base_username = username
        counter = 1
        while User.query.filter_by(username=username).first():
            username = f"{base_username}{counter}"
            counter += 1

        # Create user
        password_hash = hash_password(password)
        new_user = User(
            username=username,
            email=email,
            password_hash=password_hash,
            full_name=full_name,
            email_verified=not config.EMAIL_VERIFICATION_REQUIRED,
            tier='free'
        )
        db.session.add(new_user)
        db.session.commit()

        # Log activity
        activity = UserActivity(
            user_id=new_user.id,
            activity_type='registration',
            ip_address=get_client_ip(),
            user_agent=get_user_agent()
        )
        db.session.add(activity)
        db.session.commit()

        # Send verification email if required
        if config.EMAIL_VERIFICATION_REQUIRED:
            verification_token = secrets.token_urlsafe(32)
            expires_at = datetime.utcnow() + timedelta(hours=config.EMAIL_TOKEN_EXPIRY_HOURS)

            verification = EmailVerification(
                user_id=new_user.id,
                token=verification_token,
                email=email,
                expires_at=expires_at
            )
            db.session.add(verification)
            db.session.commit()

            # Send email
            email_service.send_verification_email(email, username, verification_token)

            return jsonify({
                'success': True,
                'message': 'Registration successful. Please check your email to verify your account.',
                'email_verification_required': True
            }), 201
        else:
            # Auto-login if email verification not required
            session_token = secrets.token_urlsafe(48)
            expires_at = datetime.utcnow() + timedelta(days=30)

            user_session = UserSession(
                user_id=new_user.id,
                session_token=session_token,
                expires_at=expires_at,
                ip_address=get_client_ip(),
                user_agent=get_user_agent()
            )
            db.session.add(user_session)
            db.session.commit()

            return jsonify({
                'success': True,
                'user': new_user.to_dict(),
                'session_token': session_token,
                'message': 'Registration successful'
            }), 201

    except Exception as e:
        db.session.rollback()
        print(f"Registration error: {e}")
        return jsonify({'error': 'Registration failed'}), 500

@api.route('/api/v2/login', methods=['POST'])
def login():
    """Enhanced user login"""
    try:
        data = request.get_json()
        identifier = data.get('username', '').strip()  # Can be username or email
        password = data.get('password', '')

        if not identifier or not password:
            return jsonify({'error': 'Username/email and password are required'}), 400

        # Find user by username or email
        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier.lower())
        ).first()

        if not user:
            return jsonify({'error': 'Invalid credentials'}), 401

        # Verify password
        if not verify_password(password, user.password_hash):
            return jsonify({'error': 'Invalid credentials'}), 401

        # Check if user is active
        if not user.is_active:
            return jsonify({'error': 'Account is deactivated. Contact support.'}), 403

        # Check email verification if required
        if config.EMAIL_VERIFICATION_REQUIRED and not user.email_verified:
            return jsonify({'error': 'Please verify your email before logging in'}), 403

        # Create session
        session_token = secrets.token_urlsafe(48)
        expires_at = datetime.utcnow() + timedelta(days=30)

        user_session = UserSession(
            user_id=user.id,
            session_token=session_token,
            expires_at=expires_at,
            ip_address=get_client_ip(),
            user_agent=get_user_agent()
        )
        db.session.add(user_session)

        # Update last login
        user.last_login = datetime.utcnow()
        db.session.commit()

        # Log activity
        activity = UserActivity(
            user_id=user.id,
            activity_type='login',
            ip_address=get_client_ip(),
            user_agent=get_user_agent()
        )
        db.session.add(activity)
        db.session.commit()

        return jsonify({
            'success': True,
            'user': user.to_dict(),
            'session_token': session_token
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Login error: {e}")
        return jsonify({'error': 'Login failed'}), 500

@api.route('/api/v2/verify-email', methods=['GET', 'POST'])
def verify_email():
    """Verify email address"""
    try:
        token = request.args.get('token') or (request.get_json() or {}).get('token')

        if not token:
            return jsonify({'error': 'Verification token is required'}), 400

        # Find verification record
        verification = EmailVerification.query.filter_by(token=token, verified=False).first()

        if not verification:
            return jsonify({'error': 'Invalid or expired verification token'}), 400

        # Check if expired
        if verification.expires_at < datetime.utcnow():
            return jsonify({'error': 'Verification token has expired'}), 400

        # Mark as verified
        verification.verified = True
        user = User.query.get(verification.user_id)
        user.email_verified = True
        db.session.commit()

        # Log activity
        activity = UserActivity(
            user_id=user.id,
            activity_type='email_verified',
            ip_address=get_client_ip()
        )
        db.session.add(activity)
        db.session.commit()

        # Send welcome email
        email_service.send_welcome_email(user.email, user.username)

        return jsonify({
            'success': True,
            'message': 'Email verified successfully! You can now log in.'
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Email verification error: {e}")
        return jsonify({'error': 'Verification failed'}), 500

@api.route('/api/v2/forgot-password', methods=['POST'])
def forgot_password():
    """Request password reset"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()

        if not email:
            return jsonify({'error': 'Email is required'}), 400

        # Find user
        user = User.query.filter_by(email=email).first()

        # Always return success to prevent email enumeration
        if not user:
            return jsonify({
                'success': True,
                'message': 'If an account exists with this email, a password reset link has been sent.'
            }), 200

        # Create reset token
        reset_token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=config.PASSWORD_RESET_TOKEN_EXPIRY_HOURS)

        password_reset = PasswordReset(
            user_id=user.id,
            token=reset_token,
            expires_at=expires_at,
            ip_address=get_client_ip()
        )
        db.session.add(password_reset)
        db.session.commit()

        # Send reset email
        email_service.send_password_reset_email(user.email, user.username, reset_token)

        return jsonify({
            'success': True,
            'message': 'If an account exists with this email, a password reset link has been sent.'
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Forgot password error: {e}")
        return jsonify({'error': 'Request failed'}), 500

@api.route('/api/v2/reset-password', methods=['POST'])
def reset_password():
    """Reset password with token"""
    try:
        data = request.get_json()
        token = data.get('token', '')
        new_password = data.get('password', '')

        if not token or not new_password:
            return jsonify({'error': 'Token and new password are required'}), 400

        # Find reset record
        reset = PasswordReset.query.filter_by(token=token, used=False).first()

        if not reset:
            return jsonify({'error': 'Invalid or expired reset token'}), 400

        # Check if expired
        if reset.expires_at < datetime.utcnow():
            return jsonify({'error': 'Reset token has expired'}), 400

        # Update password
        user = User.query.get(reset.user_id)
        user.password_hash = hash_password(new_password)

        # Mark reset as used
        reset.used = True
        reset.used_at = datetime.utcnow()

        db.session.commit()

        # Log activity
        activity = UserActivity(
            user_id=user.id,
            activity_type='password_reset',
            ip_address=get_client_ip()
        )
        db.session.add(activity)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Password reset successfully. You can now log in with your new password.'
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Password reset error: {e}")
        return jsonify({'error': 'Reset failed'}), 500

# ==================== OAuth Routes ====================

@api.route('/api/oauth/login/<provider>')
def oauth_login(provider):
    """Initiate OAuth login flow"""
    try:
        oauth_provider = oauth_service.get_provider(provider)
        if not oauth_provider:
            return jsonify({'error': f'OAuth provider {provider} not configured'}), 400

        # Generate state token for CSRF protection
        state_token = oauth_service.generate_state_token()
        session['oauth_state'] = state_token

        # Get authorization URL
        auth_url = oauth_provider.get_authorization_url(state_token)

        return redirect(auth_url)

    except Exception as e:
        print(f"OAuth login error: {e}")
        return jsonify({'error': 'OAuth login failed'}), 500

@api.route('/api/oauth/callback/<provider>')
def oauth_callback(provider):
    """Handle OAuth callback"""
    try:
        # Verify state token
        state = request.args.get('state')
        if state != session.get('oauth_state'):
            return jsonify({'error': 'Invalid state token'}), 400

        # Get authorization code
        code = request.args.get('code')
        if not code:
            return jsonify({'error': 'No authorization code received'}), 400

        # Get OAuth provider
        oauth_provider = oauth_service.get_provider(provider)
        if not oauth_provider:
            return jsonify({'error': 'Invalid provider'}), 400

        # Exchange code for token
        token_data = oauth_provider.exchange_code_for_token(code)
        if not token_data:
            return jsonify({'error': 'Failed to get access token'}), 400

        access_token = token_data.get('access_token')

        # Get user info
        user_info = oauth_provider.get_user_info(access_token)
        if not user_info:
            return jsonify({'error': 'Failed to get user information'}), 400

        # Find or create user
        oauth_account = OAuthAccount.query.filter_by(
            provider=provider,
            provider_user_id=user_info['provider_user_id']
        ).first()

        if oauth_account:
            # Existing OAuth account - login
            user = User.query.get(oauth_account.user_id)
        else:
            # New OAuth account - check if email exists
            user = User.query.filter_by(email=user_info['email']).first()

            if not user:
                # Create new user
                username = user_info.get('username') or user_info['email'].split('@')[0]
                base_username = username
                counter = 1
                while User.query.filter_by(username=username).first():
                    username = f"{base_username}{counter}"
                    counter += 1

                user = User(
                    username=username,
                    email=user_info['email'],
                    password_hash=hash_password(secrets.token_urlsafe(32)),  # Random password
                    full_name=user_info.get('name'),
                    email_verified=user_info.get('email_verified', True),
                    profile_image=user_info.get('picture'),
                    tier='free'
                )
                db.session.add(user)
                db.session.flush()

            # Link OAuth account to user
            oauth_account = OAuthAccount(
                user_id=user.id,
                provider=provider,
                provider_user_id=user_info['provider_user_id'],
                access_token=access_token,
                profile_data=str(user_info.get('raw_data', {}))
            )
            db.session.add(oauth_account)

        # Create session
        session_token = secrets.token_urlsafe(48)
        expires_at = datetime.utcnow() + timedelta(days=30)

        user_session = UserSession(
            user_id=user.id,
            session_token=session_token,
            expires_at=expires_at,
            ip_address=get_client_ip(),
            user_agent=get_user_agent()
        )
        db.session.add(user_session)

        # Update last login
        user.last_login = datetime.utcnow()
        db.session.commit()

        # Log activity
        activity = UserActivity(
            user_id=user.id,
            activity_type=f'oauth_login_{provider}',
            ip_address=get_client_ip()
        )
        db.session.add(activity)
        db.session.commit()

        # Redirect to app with session token
        return redirect(f"/?session_token={session_token}")

    except Exception as e:
        db.session.rollback()
        print(f"OAuth callback error: {e}")
        return jsonify({'error': 'OAuth authentication failed'}), 500

# ==================== Quota & Usage Routes ====================

@api.route('/api/v2/quota/status')
@optional_auth
def get_quota_status():
    """Get user's current quota status"""
    user = get_current_user()
    user_id = user['id'] if user else None

    status = quota_service.get_user_quota_status(user_id)

    return jsonify(status), 200

@api.route('/api/v2/usage/log', methods=['POST'])
@optional_auth
def log_usage():
    """Log API usage (internal endpoint)"""
    user = get_current_user()
    user_id = user['id'] if user else None

    data = request.get_json()
    resource_type = data.get('resource_type')
    count = data.get('count', 1)

    if not resource_type:
        return jsonify({'error': 'resource_type is required'}), 400

    success = quota_service.log_usage(user_id, resource_type, count)

    return jsonify({'success': success}), 200 if success else 500

# ==================== Admin Routes ====================

@api.route('/api/admin/dashboard')
@admin_required
def admin_dashboard():
    """Get admin dashboard data"""
    try:
        today = date.today()
        yesterday = today - timedelta(days=1)

        # Total users
        total_users = User.query.count()

        # New users today
        new_users_today = User.query.filter(
            func.date(User.created_at) == today
        ).count()

        # Active sessions
        active_sessions = UserSession.query.filter(
            UserSession.is_active == True,
            UserSession.expires_at > datetime.utcnow()
        ).count()

        # Usage stats
        images_today = db.session.query(func.sum(DailyUsage.images_generated)).filter(
            DailyUsage.date == today
        ).scalar() or 0

        videos_today = db.session.query(func.sum(DailyUsage.videos_created)).filter(
            DailyUsage.date == today
        ).scalar() or 0

        # Recent users
        recent_users = User.query.order_by(desc(User.created_at)).limit(50).all()

        # Top users by usage (last 7 days)
        week_ago = today - timedelta(days=7)
        top_usage = db.session.query(
            User.username,
            func.sum(DailyUsage.images_generated).label('images'),
            func.sum(DailyUsage.videos_created).label('videos'),
            func.sum(DailyUsage.messages_sent).label('messages')
        ).join(DailyUsage).filter(
            DailyUsage.date >= week_ago
        ).group_by(User.id).order_by(
            desc(func.sum(DailyUsage.images_generated) + func.sum(DailyUsage.videos_created) + func.sum(DailyUsage.messages_sent))
        ).limit(10).all()

        return jsonify({
            'stats': {
                'total_users': total_users,
                'new_users_today': new_users_today,
                'active_sessions': active_sessions,
                'images_today': images_today,
                'videos_today': videos_today
            },
            'users': [u.to_dict() for u in recent_users],
            'usage': [{
                'username': u[0],
                'images': u[1] or 0,
                'videos': u[2] or 0,
                'messages': u[3] or 0
            } for u in top_usage]
        }), 200

    except Exception as e:
        print(f"Admin dashboard error: {e}")
        return jsonify({'error': 'Failed to load dashboard'}), 500

@api.route('/api/admin/users/<int:user_id>/tier', methods=['POST'])
@admin_required
def update_user_tier(user_id):
    """Update user tier"""
    try:
        data = request.get_json()
        new_tier = data.get('tier')

        success = quota_service.upgrade_user_tier(user_id, new_tier)

        if success:
            return jsonify({'success': True}), 200
        else:
            return jsonify({'error': 'Failed to update tier'}), 400

    except Exception as e:
        print(f"Update tier error: {e}")
        return jsonify({'error': 'Update failed'}), 500

@api.route('/api/admin/users/<int:user_id>/deactivate', methods=['POST'])
@admin_required
def deactivate_user(user_id):
    """Deactivate user account"""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        user.is_active = False
        db.session.commit()

        return jsonify({'success': True}), 200

    except Exception as e:
        db.session.rollback()
        print(f"Deactivate user error: {e}")
        return jsonify({'error': 'Deactivation failed'}), 500

@api.route('/api/admin/users/<int:user_id>/activate', methods=['POST'])
@admin_required
def activate_user(user_id):
    """Activate user account"""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        user.is_active = True
        db.session.commit()

        return jsonify({'success': True}), 200

    except Exception as e:
        db.session.rollback()
        print(f"Activate user error: {e}")
        return jsonify({'error': 'Activation failed'}), 500
