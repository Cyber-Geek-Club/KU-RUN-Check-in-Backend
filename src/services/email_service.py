import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv
import traceback

load_dotenv()

# Email configuration
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USER)
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


def send_email(to_email: str, subject: str, html_content: str) -> bool:
    """
    Send email using SMTP
    Returns True if successful, False otherwise
    """
    # Check if email configuration exists
    if not SMTP_USER or not SMTP_PASSWORD:
        print("ERROR: Email configuration missing!")
        print(f"SMTP_USER: {SMTP_USER}")
        print(f"SMTP_PASSWORD: {'*' * len(SMTP_PASSWORD) if SMTP_PASSWORD else 'None'}")
        return False

    try:
        print(f"Attempting to send email to: {to_email}")
        print(f"Using SMTP: {SMTP_HOST}:{SMTP_PORT}")
        print(f"From: {FROM_EMAIL}")

        # Create message
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = FROM_EMAIL
        message["To"] = to_email

        # Add HTML content
        html_part = MIMEText(html_content, "html")
        message.attach(html_part)

        # Connect to SMTP server and send
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            print("Connected to SMTP server")
            server.starttls()
            print("TLS enabled")
            server.login(SMTP_USER, SMTP_PASSWORD)
            print("Login successful")
            server.send_message(message)
            print(f"Email sent successfully to {to_email}")

        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"SMTP Authentication Error: {e}")
        print("Please check your email and password/app password")
        return False
    except smtplib.SMTPException as e:
        print(f"SMTP Error: {e}")
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"Error sending email: {e}")
        traceback.print_exc()
        return False


def send_verification_email(to_email: str, verification_token: str, user_name: str) -> bool:
    """
    Send email verification link
    """
    # If FRONTEND_URL is set, use frontend route, otherwise use API route
    if FRONTEND_URL and not FRONTEND_URL.startswith("http://localhost:8000"):
        verification_link = f"{FRONTEND_URL}/verify-email?token={verification_token}"
    else:
        # Use API endpoint directly
        verification_link = f"http://localhost:8000/api/users/verify-email?token={verification_token}"

    subject = "KU RUN - Verify Your Email"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background-color: #4CAF50;
                color: white;
                padding: 20px;
                text-align: center;
                border-radius: 5px 5px 0 0;
            }}
            .content {{
                background-color: #f9f9f9;
                padding: 30px;
                border-radius: 0 0 5px 5px;
            }}
            .button {{
                display: inline-block;
                padding: 12px 30px;
                background-color: #4CAF50;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                margin: 20px 0;
            }}
            .footer {{
                text-align: center;
                margin-top: 20px;
                font-size: 12px;
                color: #666;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Welcome to KU RUN!</h1>
            </div>
            <div class="content">
                <h2>Hello {user_name}!</h2>
                <p>Thank you for registering with KU RUN. Please verify your email address to complete your registration.</p>
                <p>Click the button below to verify your email:</p>
                <center>
                    <a href="{verification_link}" class="button">Verify Email</a>
                </center>
                <p>Or copy and paste this link into your browser:</p>
                <p style="word-break: break-all; color: #4CAF50;">{verification_link}</p>
                <p><strong>This link will expire in 24 hours.</strong></p>
                <p>If you didn't create an account, please ignore this email.</p>
            </div>
            <div class="footer">
                <p>&copy; 2025 KU RUN. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """

    return send_email(to_email, subject, html_content)


def send_password_reset_email(to_email: str, reset_token: str, user_name: str) -> bool:
    """
    Send password reset link
    """
    reset_link = f"{FRONTEND_URL}/reset-password?token={reset_token}"

    subject = "KU RUN - Password Reset Request"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background-color: #f44336;
                color: white;
                padding: 20px;
                text-align: center;
                border-radius: 5px 5px 0 0;
            }}
            .content {{
                background-color: #f9f9f9;
                padding: 30px;
                border-radius: 0 0 5px 5px;
            }}
            .button {{
                display: inline-block;
                padding: 12px 30px;
                background-color: #f44336;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                margin: 20px 0;
            }}
            .footer {{
                text-align: center;
                margin-top: 20px;
                font-size: 12px;
                color: #666;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Password Reset Request</h1>
            </div>
            <div class="content">
                <h2>Hello {user_name}!</h2>
                <p>We received a request to reset your password. Click the button below to reset it:</p>
                <center>
                    <a href="{reset_link}" class="button">Reset Password</a>
                </center>
                <p>Or copy and paste this link into your browser:</p>
                <p style="word-break: break-all; color: #f44336;">{reset_link}</p>
                <p><strong>This link will expire in 1 hour.</strong></p>
                <p>If you didn't request a password reset, please ignore this email or contact support if you're concerned.</p>
            </div>
            <div class="footer">
                <p>&copy; 2025 KU RUN. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """

    return send_email(to_email, subject, html_content)