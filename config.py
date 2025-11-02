"""
Configuration management for AIezzy application.
Supports both SQLite (dev) and PostgreSQL (production) databases.
"""

import os
from datetime import timedelta

class Config:
    """Base configuration"""

    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production-please')
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max file size

    # Database settings
    # If DATABASE_URL is provided (Railway PostgreSQL), use it
    # Otherwise, fall back to SQLite
    if os.environ.get('DATABASE_URL'):
        # Railway provides DATABASE_URL starting with postgres://
        # SQLAlchemy requires postgresql://
        db_url = os.environ.get('DATABASE_URL')
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
        SQLALCHEMY_DATABASE_URI = db_url
        DB_TYPE = 'postgresql'
    else:
        # Development: Use SQLite
        SQLALCHEMY_DATABASE_URI = 'sqlite:///aiezzy_users.db'
        DB_TYPE = 'sqlite'

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
    }

    # Email settings (SendGrid)
    SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
    SENDGRID_FROM_EMAIL = os.environ.get('SENDGRID_FROM_EMAIL', 'noreply@aiezzy.com')
    SENDGRID_FROM_NAME = os.environ.get('SENDGRID_FROM_NAME', 'AIezzy')

    # Email verification
    EMAIL_VERIFICATION_REQUIRED = os.environ.get('EMAIL_VERIFICATION_REQUIRED', 'false').lower() == 'true'
    EMAIL_TOKEN_EXPIRY_HOURS = 24

    # Password reset
    PASSWORD_RESET_TOKEN_EXPIRY_HOURS = 1

    # OAuth settings
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
    GITHUB_CLIENT_ID = os.environ.get('GITHUB_CLIENT_ID')
    GITHUB_CLIENT_SECRET = os.environ.get('GITHUB_CLIENT_SECRET')

    # Base URL for OAuth callbacks
    BASE_URL = os.environ.get('BASE_URL', 'http://localhost:5000')

    # Usage quotas (per day)
    QUOTA_FREE_IMAGES = int(os.environ.get('QUOTA_FREE_IMAGES', '20'))
    QUOTA_FREE_VIDEOS = int(os.environ.get('QUOTA_FREE_VIDEOS', '5'))
    QUOTA_FREE_MESSAGES = int(os.environ.get('QUOTA_FREE_MESSAGES', '100'))

    QUOTA_PRO_IMAGES = int(os.environ.get('QUOTA_PRO_IMAGES', '200'))
    QUOTA_PRO_VIDEOS = int(os.environ.get('QUOTA_PRO_VIDEOS', '50'))
    QUOTA_PRO_MESSAGES = int(os.environ.get('QUOTA_PRO_MESSAGES', '1000'))

    # Rate limiting
    RATE_LIMIT_ENABLED = True
    RATE_LIMIT_PER_MINUTE = 20
    RATE_LIMIT_PER_HOUR = 200

    # File storage paths
    if os.environ.get('RAILWAY_ENVIRONMENT'):
        # Production: Use Railway persistent volume
        DATA_DIR = '/app/data'
    else:
        # Development: Use local directories
        DATA_DIR = '.'

    UPLOAD_FOLDER = f'{DATA_DIR}/uploads'
    ASSETS_DIR = f'{DATA_DIR}/assets'
    VIDEOS_DIR = f'{DATA_DIR}/videos'
    DOCUMENTS_DIR = f'{DATA_DIR}/documents'
    CONVERSATIONS_DIR = f'{DATA_DIR}/conversations'

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False
    EMAIL_VERIFICATION_REQUIRED = False  # Disable in dev

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    # Production-specific settings
    SESSION_COOKIE_SECURE = True  # HTTPS only
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    EMAIL_VERIFICATION_REQUIRED = False

# Config dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Get current configuration based on environment"""
    env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])
