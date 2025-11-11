"""
Database models for AIezzy user authentication and management system.
Uses SQLite with SQLAlchemy ORM for user accounts, sessions, and metadata.
"""

import sqlite3
import os
import hashlib
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import json

# Database file path - use environment-specific path
if os.environ.get('RAILWAY_ENVIRONMENT'):
    # Production: Use Railway persistent volume
    DB_PATH = '/app/data/aiezzy_users.db'
    # Ensure data directory exists
    os.makedirs('/app/data', exist_ok=True)
else:
    # Development: Use local file
    DB_PATH = 'aiezzy_users.db'

class Database:
    """Simple database manager for user authentication"""
    
    def __init__(self):
        self.init_database()
    
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        return conn
    
    def init_database(self):
        """Initialize database tables"""
        conn = self.get_connection()
        try:
            # Users table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    full_name TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    is_admin BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    profile_image TEXT,
                    preferences TEXT  -- JSON string for user preferences
                )
            ''')
            
            # Sessions table for login sessions
            conn.execute('''
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    session_token TEXT UNIQUE NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ip_address TEXT,
                    user_agent TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            ''')
            
            # Password reset tokens
            conn.execute('''
                CREATE TABLE IF NOT EXISTS password_reset_tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    token TEXT UNIQUE NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    used BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            ''')
            
            # User activity log
            conn.execute('''
                CREATE TABLE IF NOT EXISTS user_activity (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    activity_type TEXT NOT NULL,  -- login, logout, conversation_created, etc.
                    activity_data TEXT,  -- JSON for additional data
                    ip_address TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            ''')
            
            conn.commit()
            print("Database initialized successfully")
            
        except Exception as e:
            print(f"Error initializing database: {e}")
            raise
        finally:
            conn.close()

class UserManager:
    """User management operations"""
    
    def __init__(self):
        self.db = Database()
    
    def hash_password(self, password: str) -> str:
        """Hash a password using SHA256 with salt"""
        salt = secrets.token_hex(32)
        pwd_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return f"{salt}${pwd_hash}"
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against its hash"""
        try:
            salt, pwd_hash = password_hash.split('$')
            return hashlib.sha256((password + salt).encode()).hexdigest() == pwd_hash
        except:
            return False
    
    def create_user(self, email: str, password: str, full_name: str = None) -> Dict:
        """Create a new user account"""
        conn = self.db.get_connection()
        try:
            # Check if email already exists
            existing = conn.execute(
                'SELECT id FROM users WHERE email = ?', 
                (email,)
            ).fetchone()
            
            if existing:
                return {'success': False, 'error': 'Email already exists'}
            
            # Validate input
            if '@' not in email:
                return {'success': False, 'error': 'Invalid email format'}
            
            if len(password) < 1:
                return {'success': False, 'error': 'Password is required'}
            
            # Generate username from email (part before @)
            username = email.split('@')[0]
            
            # Make sure username is unique by adding numbers if needed
            base_username = username
            counter = 1
            while True:
                existing_username = conn.execute(
                    'SELECT id FROM users WHERE username = ?', 
                    (username,)
                ).fetchone()
                
                if not existing_username:
                    break
                    
                username = f"{base_username}{counter}"
                counter += 1
            
            # Create user
            password_hash = self.hash_password(password)
            cursor = conn.execute('''
                INSERT INTO users (username, email, password_hash, full_name, preferences)
                VALUES (?, ?, ?, ?, ?)
            ''', (username, email, password_hash, full_name, '{}'))
            
            user_id = cursor.lastrowid
            conn.commit()
            
            # Log activity
            self.log_activity(user_id, 'account_created', {'username': username, 'email': email})
            
            return {
                'success': True, 
                'user_id': user_id,
                'username': username,
                'message': 'User created successfully'
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
        finally:
            conn.close()
    
    def authenticate_user(self, username: str, password: str, ip_address: str = None, user_agent: str = None) -> Dict:
        """Authenticate user and create session"""
        conn = self.db.get_connection()
        try:
            # Find user by username or email
            user = conn.execute('''
                SELECT id, username, email, password_hash, is_active, full_name, is_admin 
                FROM users 
                WHERE (username = ? OR email = ?) AND is_active = TRUE
            ''', (username, username)).fetchone()
            
            if not user:
                return {'success': False, 'error': 'Invalid username or password'}
            
            # Verify password
            if not self.verify_password(password, user['password_hash']):
                return {'success': False, 'error': 'Invalid username or password'}
            
            # Create session token
            session_token = secrets.token_urlsafe(48)
            expires_at = datetime.now() + timedelta(days=30)  # 30-day session
            
            # Store session
            conn.execute('''
                INSERT INTO user_sessions (user_id, session_token, expires_at, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?)
            ''', (user['id'], session_token, expires_at, ip_address, user_agent))
            
            # Update last login
            conn.execute('''
                UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?
            ''', (user['id'],))
            
            conn.commit()
            
            # Log activity
            self.log_activity(user['id'], 'login', {'ip_address': ip_address})
            
            return {
                'success': True,
                'user': {
                    'id': user['id'],
                    'username': user['username'],
                    'email': user['email'],
                    'full_name': user['full_name'],
                    'is_admin': bool(user['is_admin'])
                },
                'session_token': session_token,
                'expires_at': expires_at.isoformat()
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
        finally:
            conn.close()
    
    def get_user_by_session(self, session_token: str) -> Optional[Dict]:
        """Get user by session token"""
        conn = self.db.get_connection()
        try:
            result = conn.execute('''
                SELECT u.id, u.username, u.email, u.full_name, u.is_admin, s.expires_at
                FROM users u
                JOIN user_sessions s ON u.id = s.user_id
                WHERE s.session_token = ? AND s.is_active = TRUE AND u.is_active = TRUE
            ''', (session_token,)).fetchone()
            
            if not result:
                return None
            
            # Check if session expired
            expires_at = datetime.fromisoformat(result['expires_at'].replace('Z', '+00:00'))
            if expires_at < datetime.now():
                # Deactivate expired session
                conn.execute('UPDATE user_sessions SET is_active = FALSE WHERE session_token = ?', (session_token,))
                conn.commit()
                return None
            
            return {
                'id': result['id'],
                'username': result['username'], 
                'email': result['email'],
                'full_name': result['full_name'],
                'is_admin': bool(result['is_admin'])
            }
            
        except Exception as e:
            print(f"Error getting user by session: {e}")
            return None
        finally:
            conn.close()
    
    def logout_user(self, session_token: str) -> bool:
        """Logout user by deactivating session"""
        conn = self.db.get_connection()
        try:
            # Get user_id for logging
            result = conn.execute(
                'SELECT user_id FROM user_sessions WHERE session_token = ?', 
                (session_token,)
            ).fetchone()
            
            if result:
                user_id = result['user_id']
                
                # Deactivate session
                conn.execute('''
                    UPDATE user_sessions SET is_active = FALSE 
                    WHERE session_token = ?
                ''', (session_token,))
                conn.commit()
                
                # Log activity
                self.log_activity(user_id, 'logout')
                
                return True
            return False
            
        except Exception as e:
            print(f"Error logging out user: {e}")
            return False
        finally:
            conn.close()
    
    def update_user_profile(self, user_id: int, **kwargs) -> Dict:
        """Update user profile information"""
        conn = self.db.get_connection()
        try:
            allowed_fields = ['full_name', 'email', 'profile_image']
            update_fields = []
            values = []
            
            for field, value in kwargs.items():
                if field in allowed_fields and value is not None:
                    update_fields.append(f"{field} = ?")
                    values.append(value)
            
            if not update_fields:
                return {'success': False, 'error': 'No valid fields to update'}
            
            # Add updated_at
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            values.append(user_id)
            
            query = f"UPDATE users SET {', '.join(update_fields)} WHERE id = ?"
            conn.execute(query, values)
            conn.commit()
            
            # Log activity
            self.log_activity(user_id, 'profile_updated', kwargs)
            
            return {'success': True, 'message': 'Profile updated successfully'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
        finally:
            conn.close()
    
    def change_password(self, user_id: int, old_password: str, new_password: str) -> Dict:
        """Change user password"""
        conn = self.db.get_connection()
        try:
            # Get current password hash
            result = conn.execute(
                'SELECT password_hash FROM users WHERE id = ?', 
                (user_id,)
            ).fetchone()
            
            if not result:
                return {'success': False, 'error': 'User not found'}
            
            # Verify old password
            if not self.verify_password(old_password, result['password_hash']):
                return {'success': False, 'error': 'Current password is incorrect'}
            
            # Validate new password
            if len(new_password) < 6:
                return {'success': False, 'error': 'New password must be at least 6 characters'}
            
            # Update password
            new_hash = self.hash_password(new_password)
            conn.execute('''
                UPDATE users SET password_hash = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            ''', (new_hash, user_id))
            conn.commit()
            
            # Log activity
            self.log_activity(user_id, 'password_changed')
            
            return {'success': True, 'message': 'Password changed successfully'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
        finally:
            conn.close()
    
    def log_activity(self, user_id: int, activity_type: str, activity_data: Dict = None, ip_address: str = None):
        """Log user activity"""
        conn = self.db.get_connection()
        try:
            data_json = json.dumps(activity_data) if activity_data else None
            conn.execute('''
                INSERT INTO user_activity (user_id, activity_type, activity_data, ip_address)
                VALUES (?, ?, ?, ?)
            ''', (user_id, activity_type, data_json, ip_address))
            conn.commit()
        except Exception as e:
            print(f"Error logging activity: {e}")
        finally:
            conn.close()
    
    def get_user_stats(self, user_id: int) -> Dict:
        """Get user statistics"""
        conn = self.db.get_connection()
        try:
            # Get basic user info
            user = conn.execute('''
                SELECT username, full_name, email, created_at, last_login
                FROM users WHERE id = ?
            ''', (user_id,)).fetchone()
            
            if not user:
                return {'error': 'User not found'}
            
            # Count conversations
            import os
            conv_dir = f'conversations/{user_id}'
            conversation_count = 0
            if os.path.exists(conv_dir):
                conversation_count = len([f for f in os.listdir(conv_dir) if f.endswith('.json')])
            
            # Get recent activity count
            activity_count = conn.execute('''
                SELECT COUNT(*) as count FROM user_activity 
                WHERE user_id = ? AND created_at > date('now', '-30 days')
            ''', (user_id,)).fetchone()['count']
            
            return {
                'username': user['username'],
                'full_name': user['full_name'],
                'email': user['email'],
                'created_at': user['created_at'],
                'last_login': user['last_login'],
                'conversation_count': conversation_count,
                'recent_activity_count': activity_count
            }
            
        except Exception as e:
            return {'error': str(e)}
        finally:
            conn.close()

# Initialize database when module is imported
if __name__ == '__main__':
    # Test the database setup
    db = Database()
    user_manager = UserManager()
    print("Database setup completed successfully")