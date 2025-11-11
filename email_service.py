"""
Email service for AIezzy using SendGrid.
Handles email verification, password resets, and transactional emails.
"""

import os
import requests
from typing import Optional
from config import get_config

config = get_config()

class EmailService:
    """Email service using SendGrid API"""

    def __init__(self):
        self.api_key = config.SENDGRID_API_KEY
        self.from_email = config.SENDGRID_FROM_EMAIL
        self.from_name = config.SENDGRID_FROM_NAME
        self.base_url = config.BASE_URL

    def send_email(self, to_email: str, subject: str, html_content: str, text_content: Optional[str] = None) -> bool:
        """
        Send email via SendGrid API

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML email body
            text_content: Plain text email body (optional)

        Returns:
            bool: True if sent successfully, False otherwise
        """
        if not self.api_key:
            print("Warning: SENDGRID_API_KEY not configured. Email not sent.")
            print(f"Would send email to {to_email}: {subject}")
            return False

        url = "https://api.sendgrid.com/v3/mail/send"

        payload = {
            "personalizations": [{
                "to": [{"email": to_email}],
                "subject": subject
            }],
            "from": {
                "email": self.from_email,
                "name": self.from_name
            },
            "content": [{
                "type": "text/html",
                "value": html_content
            }]
        }

        # Add plain text version if provided
        if text_content:
            payload["content"].insert(0, {
                "type": "text/plain",
                "value": text_content
            })

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(url, json=payload, headers=headers)

            if response.status_code == 202:
                print(f"Email sent successfully to {to_email}")
                return True
            else:
                print(f"Failed to send email. Status: {response.status_code}")
                print(f"Response: {response.text}")
                return False

        except Exception as e:
            print(f"Error sending email: {e}")
            return False

    def send_verification_email(self, to_email: str, username: str, verification_token: str) -> bool:
        """
        Send email verification link to user

        Args:
            to_email: User's email address
            username: User's username
            verification_token: Unique verification token

        Returns:
            bool: True if sent successfully
        """
        verification_url = f"{self.base_url}/verify-email?token={verification_token}"

        subject = "Verify your AIezzy email address"

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ text-align: center; padding: 20px 0; }}
        .logo {{ font-size: 32px; font-weight: bold; color: #10a37f; }}
        .content {{ background: #f7f7f7; padding: 30px; border-radius: 8px; }}
        .button {{ display: inline-block; padding: 12px 24px; background: #10a37f; color: white; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
        .footer {{ text-align: center; margin-top: 30px; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">AIezzy</div>
        </div>
        <div class="content">
            <h2>Welcome to AIezzy, {username}!</h2>
            <p>Thanks for signing up! Please verify your email address to get started with your AI assistant.</p>
            <p>Click the button below to verify your email:</p>
            <p style="text-align: center;">
                <a href="{verification_url}" class="button">Verify Email Address</a>
            </p>
            <p>Or copy and paste this link into your browser:</p>
            <p style="word-break: break-all; font-size: 12px; color: #666;">{verification_url}</p>
            <p><strong>This link will expire in 24 hours.</strong></p>
            <p>If you didn't create an AIezzy account, you can safely ignore this email.</p>
        </div>
        <div class="footer">
            <p>&copy; 2025 AIezzy. All rights reserved.</p>
            <p>You're receiving this email because you signed up for AIezzy.</p>
        </div>
    </div>
</body>
</html>
"""

        text_content = f"""
Welcome to AIezzy, {username}!

Thanks for signing up! Please verify your email address to get started.

Verify your email by clicking this link:
{verification_url}

This link will expire in 24 hours.

If you didn't create an AIezzy account, you can safely ignore this email.

---
© 2025 AIezzy. All rights reserved.
"""

        return self.send_email(to_email, subject, html_content, text_content)

    def send_password_reset_email(self, to_email: str, username: str, reset_token: str) -> bool:
        """
        Send password reset link to user

        Args:
            to_email: User's email address
            username: User's username
            reset_token: Unique reset token

        Returns:
            bool: True if sent successfully
        """
        reset_url = f"{self.base_url}/reset-password?token={reset_token}"

        subject = "Reset your AIezzy password"

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ text-align: center; padding: 20px 0; }}
        .logo {{ font-size: 32px; font-weight: bold; color: #10a37f; }}
        .content {{ background: #f7f7f7; padding: 30px; border-radius: 8px; }}
        .button {{ display: inline-block; padding: 12px 24px; background: #10a37f; color: white; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
        .footer {{ text-align: center; margin-top: 30px; font-size: 12px; color: #666; }}
        .warning {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 12px; margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">AIezzy</div>
        </div>
        <div class="content">
            <h2>Password Reset Request</h2>
            <p>Hi {username},</p>
            <p>We received a request to reset your AIezzy password. Click the button below to create a new password:</p>
            <p style="text-align: center;">
                <a href="{reset_url}" class="button">Reset Password</a>
            </p>
            <p>Or copy and paste this link into your browser:</p>
            <p style="word-break: break-all; font-size: 12px; color: #666;">{reset_url}</p>
            <div class="warning">
                <strong>⚠️ Security Notice:</strong><br>
                This link will expire in 1 hour. If you didn't request this password reset, please ignore this email and your password will remain unchanged.
            </div>
        </div>
        <div class="footer">
            <p>&copy; 2025 AIezzy. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
"""

        text_content = f"""
Password Reset Request

Hi {username},

We received a request to reset your AIezzy password.

Reset your password by clicking this link:
{reset_url}

⚠️ SECURITY NOTICE:
This link will expire in 1 hour. If you didn't request this password reset, please ignore this email.

---
© 2025 AIezzy. All rights reserved.
"""

        return self.send_email(to_email, subject, html_content, text_content)

    def send_welcome_email(self, to_email: str, username: str) -> bool:
        """
        Send welcome email to new user (after verification)

        Args:
            to_email: User's email address
            username: User's username

        Returns:
            bool: True if sent successfully
        """
        subject = f"Welcome to AIezzy, {username}!"

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ text-align: center; padding: 20px 0; }}
        .logo {{ font-size: 32px; font-weight: bold; color: #10a37f; }}
        .content {{ background: #f7f7f7; padding: 30px; border-radius: 8px; }}
        .button {{ display: inline-block; padding: 12px 24px; background: #10a37f; color: white; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
        .feature {{ margin: 15px 0; padding: 15px; background: white; border-radius: 6px; }}
        .footer {{ text-align: center; margin-top: 30px; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">AIezzy</div>
        </div>
        <div class="content">
            <h2>You're all set, {username}! 🎉</h2>
            <p>Your email has been verified and your account is ready to use.</p>

            <h3>What you can do with AIezzy:</h3>

            <div class="feature">
                <strong>🎨 Generate Images</strong><br>
                Create stunning images from text descriptions
            </div>

            <div class="feature">
                <strong>🎬 Create Videos</strong><br>
                Generate videos from text or animate your images
            </div>

            <div class="feature">
                <strong>💬 AI Conversations</strong><br>
                Chat with GPT-4o for helpful, intelligent responses
            </div>

            <div class="feature">
                <strong>🖼️ Image Editing</strong><br>
                Edit and enhance your images with AI
            </div>

            <p style="text-align: center;">
                <a href="{self.base_url}" class="button">Start Creating</a>
            </p>

            <p><strong>Free Tier Limits (Daily):</strong></p>
            <ul>
                <li>20 images</li>
                <li>5 videos</li>
                <li>100 messages</li>
            </ul>

            <p>Need help? Just ask your AI assistant anything!</p>
        </div>
        <div class="footer">
            <p>&copy; 2025 AIezzy. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
"""

        text_content = f"""
Welcome to AIezzy, {username}! 🎉

Your email has been verified and your account is ready to use.

What you can do with AIezzy:
- 🎨 Generate stunning images from text
- 🎬 Create videos from text or animate images
- 💬 Chat with GPT-4o AI assistant
- 🖼️ Edit and enhance images with AI

Free Tier Limits (Daily):
- 20 images
- 5 videos
- 100 messages

Start creating: {self.base_url}

Need help? Just ask your AI assistant!

---
© 2025 AIezzy. All rights reserved.
"""

        return self.send_email(to_email, subject, html_content, text_content)

# Global email service instance
email_service = EmailService()
