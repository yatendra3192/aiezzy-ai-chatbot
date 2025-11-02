"""
Quick setup script for AIezzy enhanced user management.
Automates initial database setup and admin user creation.
"""

import os
import sys
import secrets
from getpass import getpass

def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70 + "\n")

def print_success(text):
    """Print success message"""
    print(f"✅ {text}")

def print_error(text):
    """Print error message"""
    print(f"❌ {text}")

def print_info(text):
    """Print info message"""
    print(f"ℹ️  {text}")

def check_env_file():
    """Check if .env file exists"""
    if not os.path.exists('.env'):
        print_info(".env file not found. Creating from template...")

        if not os.path.exists('.env.example'):
            print_error(".env.example not found!")
            return False

        # Copy example
        with open('.env.example', 'r') as src:
            content = src.read()

        # Generate secret key
        secret_key = secrets.token_hex(32)
        content = content.replace('your-secret-key-here-change-in-production', secret_key)

        with open('.env', 'w') as dst:
            dst.write(content)

        print_success(".env file created with generated SECRET_KEY")
        print_info("Please edit .env and add your API keys before continuing")
        return False

    print_success(".env file found")
    return True

def check_dependencies():
    """Check if required packages are installed"""
    print_info("Checking dependencies...")

    required_packages = [
        'flask',
        'flask_sqlalchemy',
        'psycopg2',
        'requests',
        'authlib'
    ]

    missing = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print_success(f"{package} installed")
        except ImportError:
            missing.append(package)
            print_error(f"{package} NOT installed")

    if missing:
        print_info("\nInstall missing packages with:")
        print(f"  pip install {' '.join(missing)}")
        return False

    return True

def setup_database():
    """Initialize database"""
    print_info("Initializing database...")

    try:
        from flask import Flask
        from config import get_config
        from models_v2 import init_db

        config = get_config()
        app = Flask(__name__)
        app.config.from_object(config)

        with app.app_context():
            init_db(app)

        print_success("Database initialized successfully")
        return True

    except Exception as e:
        print_error(f"Database initialization failed: {e}")
        return False

def create_admin_user():
    """Create admin user interactively"""
    print_info("Setting up admin user...")

    try:
        from flask import Flask
        from config import get_config
        from models_v2 import db, User, hash_password

        config = get_config()
        app = Flask(__name__)
        app.config.from_object(config)

        with app.app_context():
            # Check if admin exists
            existing_admin = User.query.filter_by(is_admin=True).first()
            if existing_admin:
                print_info(f"Admin user already exists: {existing_admin.email}")
                response = input("Create another admin user? (yes/no): ")
                if response.lower() != 'yes':
                    return True

            # Get admin details
            print("\nEnter admin user details:")
            email = input("Email: ").strip()
            username = input("Username (default: admin): ").strip() or "admin"
            password = getpass("Password: ")
            password_confirm = getpass("Confirm password: ")

            if password != password_confirm:
                print_error("Passwords don't match!")
                return False

            # Create admin
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

            print_success(f"Admin user created: {email}")
            print_info("Admin dashboard will be available at: /admin")
            return True

    except Exception as e:
        print_error(f"Admin user creation failed: {e}")
        return False

def run_migration():
    """Run database migration if needed"""
    old_db = 'aiezzy_users.db'

    if os.path.exists(old_db):
        print_info(f"Found existing database: {old_db}")
        response = input("Migrate existing data? (yes/no): ")

        if response.lower() == 'yes':
            try:
                from migrate_database import migrate_from_old_db
                from flask import Flask
                from config import get_config

                config = get_config()
                app = Flask(__name__)
                app.config.from_object(config)

                migrate_from_old_db(app)
                print_success("Migration completed successfully")
                return True

            except Exception as e:
                print_error(f"Migration failed: {e}")
                return False

    return True

def display_next_steps():
    """Display next steps after setup"""
    print_header("Setup Complete! 🎉")

    print("Next steps:\n")
    print("1. Configure API keys in .env file:")
    print("   - OPENAI_API_KEY")
    print("   - FAL_KEY")
    print("   - TAVILY_API_KEY")
    print("\n2. (Optional) Configure email:")
    print("   - SENDGRID_API_KEY")
    print("   - SENDGRID_FROM_EMAIL")
    print("\n3. (Optional) Configure OAuth:")
    print("   - GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET")
    print("   - GITHUB_CLIENT_ID / GITHUB_CLIENT_SECRET")
    print("\n4. Start the application:")
    print("   python web_app.py")
    print("\n5. Access the application:")
    print("   http://localhost:5000")
    print("\n6. Access admin dashboard:")
    print("   http://localhost:5000/admin")
    print("\nFor deployment to Railway, see DEPLOYMENT_GUIDE.md")
    print("\n" + "=" * 70)

def main():
    """Main setup flow"""
    print_header("AIezzy Enhanced User Management - Setup Wizard")

    # Step 1: Check environment file
    if not check_env_file():
        print("\nSetup paused. Please configure .env and run again.")
        return

    # Step 2: Check dependencies
    if not check_dependencies():
        print("\nSetup paused. Please install dependencies and run again.")
        return

    # Step 3: Run migration if needed
    if not run_migration():
        print("\nWarning: Migration had issues, but continuing...")

    # Step 4: Setup database
    if not setup_database():
        print("\nSetup failed at database initialization.")
        return

    # Step 5: Create admin user
    response = input("\nCreate admin user? (yes/no): ")
    if response.lower() == 'yes':
        if not create_admin_user():
            print("\nWarning: Admin user creation failed, but setup is complete.")

    # Done!
    display_next_steps()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print_error(f"Setup failed: {e}")
        sys.exit(1)
