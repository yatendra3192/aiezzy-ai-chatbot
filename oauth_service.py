"""
OAuth authentication service for Google and GitHub.
Handles OAuth flow, token management, and user profile retrieval.
"""

import requests
import secrets
from typing import Optional, Dict, Tuple
from urllib.parse import urlencode
from config import get_config

config = get_config()

class OAuthProvider:
    """Base OAuth provider class"""

    def __init__(self, name: str, client_id: str, client_secret: str, authorize_url: str, token_url: str, user_info_url: str):
        self.name = name
        self.client_id = client_id
        self.client_secret = client_secret
        self.authorize_url = authorize_url
        self.token_url = token_url
        self.user_info_url = user_info_url
        self.redirect_uri = f"{config.BASE_URL}/api/oauth/callback/{name}"

    def get_authorization_url(self, state: str) -> str:
        """Generate OAuth authorization URL"""
        raise NotImplementedError

    def exchange_code_for_token(self, code: str) -> Optional[Dict]:
        """Exchange authorization code for access token"""
        raise NotImplementedError

    def get_user_info(self, access_token: str) -> Optional[Dict]:
        """Get user profile information"""
        raise NotImplementedError

class GoogleOAuth(OAuthProvider):
    """Google OAuth provider"""

    def __init__(self):
        super().__init__(
            name='google',
            client_id=config.GOOGLE_CLIENT_ID,
            client_secret=config.GOOGLE_CLIENT_SECRET,
            authorize_url='https://accounts.google.com/o/oauth2/v2/auth',
            token_url='https://oauth2.googleapis.com/token',
            user_info_url='https://www.googleapis.com/oauth2/v2/userinfo'
        )

    def get_authorization_url(self, state: str) -> str:
        """Generate Google OAuth authorization URL"""
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'scope': 'openid email profile',
            'state': state,
            'access_type': 'offline',
            'prompt': 'consent'
        }
        return f"{self.authorize_url}?{urlencode(params)}"

    def exchange_code_for_token(self, code: str) -> Optional[Dict]:
        """Exchange authorization code for access token"""
        data = {
            'code': code,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'redirect_uri': self.redirect_uri,
            'grant_type': 'authorization_code'
        }

        try:
            response = requests.post(self.token_url, data=data)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Token exchange failed: {response.text}")
                return None
        except Exception as e:
            print(f"Error exchanging code for token: {e}")
            return None

    def get_user_info(self, access_token: str) -> Optional[Dict]:
        """Get user profile from Google"""
        headers = {'Authorization': f'Bearer {access_token}'}

        try:
            response = requests.get(self.user_info_url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                return {
                    'provider': 'google',
                    'provider_user_id': data.get('id'),
                    'email': data.get('email'),
                    'email_verified': data.get('verified_email', False),
                    'name': data.get('name'),
                    'picture': data.get('picture'),
                    'raw_data': data
                }
            else:
                print(f"Failed to get user info: {response.text}")
                return None
        except Exception as e:
            print(f"Error getting user info: {e}")
            return None

class GitHubOAuth(OAuthProvider):
    """GitHub OAuth provider"""

    def __init__(self):
        super().__init__(
            name='github',
            client_id=config.GITHUB_CLIENT_ID,
            client_secret=config.GITHUB_CLIENT_SECRET,
            authorize_url='https://github.com/login/oauth/authorize',
            token_url='https://github.com/login/oauth/access_token',
            user_info_url='https://api.github.com/user'
        )

    def get_authorization_url(self, state: str) -> str:
        """Generate GitHub OAuth authorization URL"""
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': 'read:user user:email',
            'state': state
        }
        return f"{self.authorize_url}?{urlencode(params)}"

    def exchange_code_for_token(self, code: str) -> Optional[Dict]:
        """Exchange authorization code for access token"""
        data = {
            'code': code,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'redirect_uri': self.redirect_uri
        }

        headers = {'Accept': 'application/json'}

        try:
            response = requests.post(self.token_url, data=data, headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Token exchange failed: {response.text}")
                return None
        except Exception as e:
            print(f"Error exchanging code for token: {e}")
            return None

    def get_user_info(self, access_token: str) -> Optional[Dict]:
        """Get user profile from GitHub"""
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/vnd.github.v3+json'
        }

        try:
            # Get user profile
            response = requests.get(self.user_info_url, headers=headers)
            if response.status_code != 200:
                print(f"Failed to get user info: {response.text}")
                return None

            user_data = response.json()

            # Get user email (may be private)
            email_response = requests.get(f"{self.user_info_url}/emails", headers=headers)
            email = user_data.get('email')

            if email_response.status_code == 200:
                emails = email_response.json()
                # Find primary verified email
                for e in emails:
                    if e.get('primary') and e.get('verified'):
                        email = e.get('email')
                        break

            return {
                'provider': 'github',
                'provider_user_id': str(user_data.get('id')),
                'email': email,
                'email_verified': True,  # GitHub verifies emails
                'name': user_data.get('name') or user_data.get('login'),
                'username': user_data.get('login'),
                'picture': user_data.get('avatar_url'),
                'raw_data': user_data
            }
        except Exception as e:
            print(f"Error getting user info: {e}")
            return None

class OAuthService:
    """OAuth service manager"""

    def __init__(self):
        self.providers = {
            'google': GoogleOAuth() if config.GOOGLE_CLIENT_ID else None,
            'github': GitHubOAuth() if config.GITHUB_CLIENT_ID else None
        }

    def get_provider(self, provider_name: str) -> Optional[OAuthProvider]:
        """Get OAuth provider by name"""
        provider = self.providers.get(provider_name.lower())
        if not provider:
            print(f"OAuth provider '{provider_name}' not configured")
        return provider

    def generate_state_token(self) -> str:
        """Generate secure state token for OAuth flow"""
        return secrets.token_urlsafe(32)

    def is_provider_enabled(self, provider_name: str) -> bool:
        """Check if OAuth provider is configured and enabled"""
        return self.providers.get(provider_name.lower()) is not None

    def get_enabled_providers(self) -> list:
        """Get list of enabled OAuth providers"""
        return [name for name, provider in self.providers.items() if provider is not None]

# Global OAuth service instance
oauth_service = OAuthService()
