"""
Database migration script for AIezzy.
Migrates existing data from old SQLite schema to new enhanced schema.
Supports both SQLite and PostgreSQL.
"""

import os
import sys
import sqlite3
from datetime import datetime
from config import get_config
from models import UserManager as OldUserManager
from models_v2 import db, User, UserSession, UserActivity, init_db
import hashlib
import secrets

config = get_config()

def migrate_from_old_db(app):
    """
    Migrate data from old database to new schema

    Args:
        app: Flask application instance
    """
    print("=" * 60)
    print("DATABASE MIGRATION TOOL")
    print("=" * 60)

    # Check if old database exists
    old_db_path = 'aiezzy_users.db'
    if not os.path.exists(old_db_path):
        print("❌ Old database not found. Skipping migration.")
        print("✓ Initializing fresh database...")
        with app.app_context():
            init_db(app)
        return

    print(f"📦 Found old database: {old_db_path}")
    print(f"🎯 Target database: {config.SQLALCHEMY_DATABASE_URI}")

    # Ask for confirmation
    response = input("\n⚠️  This will migrate all data to the new schema. Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("Migration cancelled.")
        return

    print("\n🔄 Starting migration...")

    try:
        # Connect to old database
        old_conn = sqlite3.connect(old_db_path)
        old_conn.row_factory = sqlite3.Row
        old_cursor = old_conn.cursor()

        with app.app_context():
            # Initialize new database
            print("1️⃣  Initializing new database schema...")
            init_db(app)

            # Migrate users
            print("2️⃣  Migrating users...")
            old_cursor.execute('SELECT * FROM users')
            users = old_cursor.fetchall()
            user_mapping = {}  # Map old IDs to new IDs

            for old_user in users:
                new_user = User(
                    username=old_user['username'],
                    email=old_user['email'],
                    password_hash=old_user['password_hash'],
                    full_name=old_user['full_name'],
                    is_active=bool(old_user['is_active']),
                    is_admin=bool(old_user['is_admin']),
                    email_verified=True,  # Mark existing users as verified
                    tier='free',
                    profile_image=old_user['profile_image'],
                    preferences=old_user['preferences'] or '{}',
                    created_at=datetime.fromisoformat(old_user['created_at']) if old_user['created_at'] else datetime.utcnow(),
                    last_login=datetime.fromisoformat(old_user['last_login']) if old_user['last_login'] else None
                )
                db.session.add(new_user)
                db.session.flush()  # Get the new ID
                user_mapping[old_user['id']] = new_user.id
                print(f"   ✓ Migrated user: {old_user['username']}")

            db.session.commit()
            print(f"   ✅ Migrated {len(users)} users")

            # Migrate sessions
            print("3️⃣  Migrating active sessions...")
            old_cursor.execute('SELECT * FROM user_sessions WHERE is_active = 1')
            sessions = old_cursor.fetchall()

            for old_session in sessions:
                if old_session['user_id'] in user_mapping:
                    new_session = UserSession(
                        user_id=user_mapping[old_session['user_id']],
                        session_token=old_session['session_token'],
                        expires_at=datetime.fromisoformat(old_session['expires_at']),
                        created_at=datetime.fromisoformat(old_session['created_at']) if old_session['created_at'] else datetime.utcnow(),
                        ip_address=old_session['ip_address'],
                        user_agent=old_session['user_agent'],
                        is_active=bool(old_session['is_active'])
                    )
                    db.session.add(new_session)

            db.session.commit()
            print(f"   ✅ Migrated {len(sessions)} active sessions")

            # Migrate user activity
            print("4️⃣  Migrating user activity...")
            old_cursor.execute('SELECT * FROM user_activity ORDER BY created_at DESC LIMIT 1000')  # Last 1000 activities
            activities = old_cursor.fetchall()

            for old_activity in activities:
                if old_activity['user_id'] in user_mapping:
                    new_activity = UserActivity(
                        user_id=user_mapping[old_activity['user_id']],
                        activity_type=old_activity['activity_type'],
                        activity_data=old_activity['activity_data'],
                        ip_address=old_activity['ip_address'],
                        created_at=datetime.fromisoformat(old_activity['created_at']) if old_activity['created_at'] else datetime.utcnow()
                    )
                    db.session.add(new_activity)

            db.session.commit()
            print(f"   ✅ Migrated {len(activities)} activity records")

        old_conn.close()

        print("\n" + "=" * 60)
        print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print(f"📊 Summary:")
        print(f"   - Users: {len(users)}")
        print(f"   - Sessions: {len(sessions)}")
        print(f"   - Activities: {len(activities)}")
        print("\n💡 Note: The old database has been preserved.")
        print(f"   Location: {old_db_path}")
        print("\n🎉 Your application is now ready to use with enhanced features!")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        print("Rolling back changes...")
        if 'db' in locals():
            db.session.rollback()
        raise

def create_admin_user(app, username, email, password):
    """
    Create an admin user

    Args:
        app: Flask application
        username: Admin username
        email: Admin email
        password: Admin password
    """
    from models_v2 import hash_password

    with app.app_context():
        # Check if user exists
        existing = User.query.filter_by(email=email).first()
        if existing:
            print(f"✅ User {email} already exists")
            if not existing.is_admin:
                existing.is_admin = True
                db.session.commit()
                print(f"✅ Granted admin privileges to {email}")
            return

        # Create admin user
        admin = User(
            username=username,
            email=email,
            password_hash=hash_password(password),
            full_name='Administrator',
            is_admin=True,
            is_active=True,
            email_verified=True,
            tier='enterprise'
        )
        db.session.add(admin)
        db.session.commit()

        print(f"✅ Created admin user: {email}")
        print(f"   Username: {username}")
        print(f"   Password: {password}")
        print(f"   Tier: enterprise")

if __name__ == '__main__':
    # This can be run standalone for migration
    from flask import Flask
    from config import get_config

    config = get_config()
    app = Flask(__name__)
    app.config.from_object(config)

    if len(sys.argv) > 1 and sys.argv[1] == 'migrate':
        migrate_from_old_db(app)
    elif len(sys.argv) > 1 and sys.argv[1] == 'create-admin':
        if len(sys.argv) < 5:
            print("Usage: python migrate_database.py create-admin <username> <email> <password>")
        else:
            create_admin_user(app, sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        print("Usage:")
        print("  python migrate_database.py migrate")
        print("  python migrate_database.py create-admin <username> <email> <password>")
