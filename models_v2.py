"""
Enhanced database models for AIezzy with PostgreSQL support.
Uses SQLAlchemy ORM for better database abstraction and migration support.
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import hashlib
import secrets
import json
from typing import Optional, Dict, List

db = SQLAlchemy()

class User(db.Model):
    """User account model"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120))

    # Status flags
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    email_verified = db.Column(db.Boolean, default=False)

    # Tier system for quotas
    tier = db.Column(db.String(20), default='free')  # free, pro, enterprise

    # Profile
    profile_image = db.Column(db.String(255))
    bio = db.Column(db.Text)
    preferences = db.Column(db.Text, default='{}')  # JSON

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    # Relationships
    sessions = db.relationship('UserSession', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    oauth_accounts = db.relationship('OAuthAccount', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    email_verifications = db.relationship('EmailVerification', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    password_resets = db.relationship('PasswordReset', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    activities = db.relationship('UserActivity', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    usage_logs = db.relationship('UsageLog', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User {self.username}>'

    def to_dict(self):
        """Convert user to dictionary"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'is_admin': self.is_admin,
            'email_verified': self.email_verified,
            'tier': self.tier,
            'profile_image': self.profile_image,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }

class UserSession(db.Model):
    """User login sessions"""
    __tablename__ = 'user_sessions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    session_token = db.Column(db.String(255), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Session metadata
    ip_address = db.Column(db.String(45))  # IPv6 compatible
    user_agent = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<UserSession {self.id} for user {self.user_id}>'

class OAuthAccount(db.Model):
    """OAuth provider accounts linked to users"""
    __tablename__ = 'oauth_accounts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    provider = db.Column(db.String(50), nullable=False)  # google, github, etc.
    provider_user_id = db.Column(db.String(255), nullable=False)

    # OAuth tokens (encrypted in production)
    access_token = db.Column(db.Text)
    refresh_token = db.Column(db.Text)
    token_expires_at = db.Column(db.DateTime)

    # Provider profile data
    profile_data = db.Column(db.Text)  # JSON

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Unique constraint: one provider account per user
    __table_args__ = (
        db.UniqueConstraint('user_id', 'provider', name='unique_user_provider'),
        db.Index('idx_provider_user', 'provider', 'provider_user_id'),
    )

    def __repr__(self):
        return f'<OAuthAccount {self.provider} for user {self.user_id}>'

class EmailVerification(db.Model):
    """Email verification tokens"""
    __tablename__ = 'email_verifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    token = db.Column(db.String(255), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), nullable=False)  # Email to verify
    expires_at = db.Column(db.DateTime, nullable=False)
    verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<EmailVerification {self.id} for user {self.user_id}>'

class PasswordReset(db.Model):
    """Password reset tokens"""
    __tablename__ = 'password_resets'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    token = db.Column(db.String(255), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    used_at = db.Column(db.DateTime)
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<PasswordReset {self.id} for user {self.user_id}>'

class UserActivity(db.Model):
    """User activity log"""
    __tablename__ = 'user_activity'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    activity_type = db.Column(db.String(50), nullable=False, index=True)
    activity_data = db.Column(db.Text)  # JSON
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f'<UserActivity {self.activity_type} by user {self.user_id}>'

class UsageLog(db.Model):
    """Track API usage for quotas"""
    __tablename__ = 'usage_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    resource_type = db.Column(db.String(50), nullable=False)  # image, video, message
    resource_count = db.Column(db.Integer, default=1)
    resource_metadata = db.Column(db.Text)  # JSON for additional data
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        db.Index('idx_user_resource_date', 'user_id', 'resource_type', 'created_at'),
    )

    def __repr__(self):
        return f'<UsageLog {self.resource_type} by user {self.user_id}>'

class DailyUsage(db.Model):
    """Aggregated daily usage stats"""
    __tablename__ = 'daily_usage'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)

    images_generated = db.Column(db.Integer, default=0)
    videos_created = db.Column(db.Integer, default=0)
    messages_sent = db.Column(db.Integer, default=0)

    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'date', name='unique_user_date'),
    )

    def __repr__(self):
        return f'<DailyUsage user {self.user_id} on {self.date}>'

class UploadedFile(db.Model):
    """Track uploaded files across workers using database (solves multi-worker issue)"""
    __tablename__ = 'uploaded_files'

    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.String(100), nullable=False, index=True)
    file_path = db.Column(db.String(500), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # image, document, video
    mime_type = db.Column(db.String(100))
    file_size = db.Column(db.Integer)

    # Metadata
    upload_order = db.Column(db.Integer, default=0)
    metadata = db.Column(db.Text)  # JSON for additional data

    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    expires_at = db.Column(db.DateTime)  # Optional expiry for cleanup

    __table_args__ = (
        db.Index('idx_thread_created', 'thread_id', 'created_at'),
    )

    def __repr__(self):
        return f'<UploadedFile {self.filename} in thread {self.thread_id}>'

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'thread_id': self.thread_id,
            'file_path': self.file_path,
            'filename': self.filename,
            'category': self.category,
            'mime_type': self.mime_type,
            'file_size': self.file_size,
            'upload_order': self.upload_order,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# Utility functions for password hashing
def hash_password(password: str) -> str:
    """Hash a password using SHA256 with salt"""
    salt = secrets.token_hex(32)
    pwd_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}${pwd_hash}"

def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash"""
    try:
        salt, pwd_hash = password_hash.split('$')
        return hashlib.sha256((password + salt).encode()).hexdigest() == pwd_hash
    except:
        return False

def init_db(app):
    """Initialize database with Flask app"""
    db.init_app(app)
    with app.app_context():
        db.create_all()
        print(f"Database initialized: {app.config['SQLALCHEMY_DATABASE_URI']}")
