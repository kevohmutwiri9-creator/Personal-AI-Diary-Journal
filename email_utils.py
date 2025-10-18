"""
Email utilities for the Diary application.
Handles sending emails for password reset, notifications, etc.
"""
from flask import render_template, current_app, url_for
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer
from datetime import datetime, timedelta
import os

def send_email(subject, recipients, template, **kwargs):
    """Send an email using Flask-Mail.
    
    Args:
        subject: Email subject
        recipients: List of email addresses or single email address
        template: Name of the template file (without .html)
        **kwargs: Additional variables to pass to the template
    """
    from app import mail
    
    # Ensure recipients is a list
    if isinstance(recipients, str):
        recipients = [recipients]
    
    # Render the email template
    html_body = render_template(f'emails/{template}.html', **kwargs)
    
    # Create and send the message
    msg = Message(
        subject=subject,
        recipients=recipients,
        html=html_body,
        sender=current_app.config['MAIL_DEFAULT_SENDER']
    )
    
    try:
        mail.send(msg)
        current_app.logger.info(f"Email sent to {', '.join(recipients)}")
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to send email to {', '.join(recipients)}: {str(e)}")
        return False

def generate_token(email, salt=None):
    """Generate a secure token for password reset.
    
    Args:
        email: User's email address
        salt: Optional salt for the token (default: 'password-reset-salt')
        
    Returns:
        str: A secure token
    """
    if salt is None:
        salt = 'password-reset-salt'
    
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps(email, salt=salt)

def verify_token(token, expiration=3600, salt=None):
    """Verify a token and return the email if valid.
    
    Args:
        token: The token to verify
        expiration: Token expiration time in seconds (default: 1 hour)
        salt: Optional salt for the token (default: 'password-reset-salt')
        
    Returns:
        str: Email address if token is valid, None otherwise
    """
    if salt is None:
        salt = 'password-reset-salt'
    
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email = serializer.loads(
            token,
            salt=salt,
            max_age=expiration
        )
    except:
        return None
    return email

def send_password_reset_email(user_email, username, token):
    """Send a password reset email to the user.
    
    Args:
        user_email: User's email address
        username: User's username
        token: Password reset token
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    reset_url = url_for('auth.reset_password', token=token, _external=True)
    return send_email(
        subject="Reset Your Password",
        recipients=[user_email],
        template='reset_password',
        username=username,
        reset_url=reset_url,
        expiration_hours=current_app.config.get('RESET_PASSWORD_TOKEN_EXPIRATION', 1) // 3600
    )

def send_welcome_email(user_email, username):
    """Send a welcome email to new users.
    
    Args:
        user_email: User's email address
        username: User's username
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    return send_email(
        subject="Welcome to Your Personal Diary App!",
        recipients=[user_email],
        template='welcome',
        username=username
    )
