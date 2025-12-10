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
    # Use API endpoint for verification
    if FRONTEND_URL and not FRONTEND_URL.startswith("http://localhost:8000"):
        verification_link = f"{FRONTEND_URL}/auth/verify-email?token?token?token={verification_token}"
    else:
        # Fallback to API endpoint
        verification_link = f"http://localhost:8000/api/users/reset-password?token={verification_token}"


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
                margin: 0;
                padding: 0;
                background-color: #f4f4f4;
            }}
            .container {{
                max-width: 600px;
                margin: 20px auto;
                background-color: white;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }}
            .header {{
                background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
                color: white;
                padding: 30px 20px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 28px;
                font-weight: 600;
            }}
            .content {{
                padding: 40px 30px;
                background-color: #ffffff;
            }}
            .content h2 {{
                color: #333;
                font-size: 22px;
                margin-top: 0;
            }}
            .content p {{
                color: #555;
                font-size: 16px;
                line-height: 1.6;
                margin: 15px 0;
            }}
            .button {{
                display: inline-block;
                padding: 14px 35px;
                background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
                color: white !important;
                text-decoration: none;
                border-radius: 6px;
                margin: 25px 0;
                font-weight: 600;
                font-size: 16px;
                transition: transform 0.2s;
            }}
            .button:hover {{
                transform: translateY(-2px);
            }}
            .link-box {{
                background-color: #f8f9fa;
                padding: 15px;
                border-radius: 6px;
                border-left: 4px solid #4CAF50;
                margin: 20px 0;
            }}
            .link-text {{
                word-break: break-all;
                color: #4CAF50;
                font-size: 14px;
                font-family: monospace;
            }}
            .footer {{
                background-color: #f8f9fa;
                text-align: center;
                padding: 25px;
                border-top: 1px solid #e0e0e0;
            }}
            .footer p {{
                margin: 5px 0;
                font-size: 13px;
                color: #666;
            }}
            .warning {{
                background-color: #fff3cd;
                border-left: 4px solid #ffc107;
                padding: 12px;
                margin: 20px 0;
                border-radius: 4px;
            }}
            .warning p {{
                margin: 0;
                color: #856404;
                font-size: 14px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🏃 Welcome to KU RUN!</h1>
            </div>
            <div class="content">
                <h2>Hello {user_name}! 👋</h2>
                <p>Thank you for registering with KU RUN. We're excited to have you join our running community!</p>
                <p>To complete your registration and start participating in events, please verify your email address by clicking the button below:</p>

                <center>
                    <a href="{verification_link}" class="button">✓ Verify Email Address</a>
                </center>

                <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
                <div class="link-box">
                    <p class="link-text">{verification_link}</p>
                </div>

                <div class="warning">
                    <p><strong>⚠️ Important:</strong> This verification link will expire in 24 hours.</p>
                </div>

                <p>If you didn't create an account with KU RUN, please ignore this email.</p>
            </div>
            <div class="footer">
                <p><strong>KU RUN Check-in System</strong></p>
                <p>Kasetsart University Running Events</p>
                <p style="margin-top: 15px;">&copy; 2025 KU RUN. All rights reserved.</p>
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
    # If FRONTEND_URL is set, use frontend route, otherwise use API route
    if FRONTEND_URL and not FRONTEND_URL.startswith("http://localhost:8000"):
        reset_link = f"{FRONTEND_URL}/auth/reset-password?token={reset_token}"
    else:
        # Fallback to API endpoint
        reset_link = f"http://localhost:8000/api/users/reset-password?token={reset_token}"

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
                margin: 0;
                padding: 0;
                background-color: #f4f4f4;
            }}
            .container {{
                max-width: 600px;
                margin: 20px auto;
                background-color: white;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }}
            .header {{
                background: linear-gradient(135deg, #f44336 0%, #d32f2f 100%);
                color: white;
                padding: 30px 20px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 28px;
                font-weight: 600;
            }}
            .content {{
                padding: 40px 30px;
                background-color: #ffffff;
            }}
            .content h2 {{
                color: #333;
                font-size: 22px;
                margin-top: 0;
            }}
            .content p {{
                color: #555;
                font-size: 16px;
                line-height: 1.6;
                margin: 15px 0;
            }}
            .button {{
                display: inline-block;
                padding: 14px 35px;
                background: linear-gradient(135deg, #f44336 0%, #d32f2f 100%);
                color: white !important;
                text-decoration: none;
                border-radius: 6px;
                margin: 25px 0;
                font-weight: 600;
                font-size: 16px;
                transition: transform 0.2s;
            }}
            .button:hover {{
                transform: translateY(-2px);
            }}
            .link-box {{
                background-color: #f8f9fa;
                padding: 15px;
                border-radius: 6px;
                border-left: 4px solid #f44336;
                margin: 20px 0;
            }}
            .link-text {{
                word-break: break-all;
                color: #f44336;
                font-size: 14px;
                font-family: monospace;
            }}
            .footer {{
                background-color: #f8f9fa;
                text-align: center;
                padding: 25px;
                border-top: 1px solid #e0e0e0;
            }}
            .footer p {{
                margin: 5px 0;
                font-size: 13px;
                color: #666;
            }}
            .warning {{
                background-color: #fff3cd;
                border-left: 4px solid #ffc107;
                padding: 12px;
                margin: 20px 0;
                border-radius: 4px;
            }}
            .warning p {{
                margin: 0;
                color: #856404;
                font-size: 14px;
            }}
            .info-box {{
                background-color: #e3f2fd;
                border-left: 4px solid #2196F3;
                padding: 12px;
                margin: 20px 0;
                border-radius: 4px;
            }}
            .info-box p {{
                margin: 0;
                color: #0d47a1;
                font-size: 14px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔐 Password Reset Request</h1>
            </div>
            <div class="content">
                <h2>Hello {user_name}!</h2>
                <p>We received a request to reset the password for your KU RUN account.</p>
                <p>Click the button below to create a new password:</p>

                <center>
                    <a href="{reset_link}" class="button">🔑 Reset Password</a>
                </center>

                <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
                <div class="link-box">
                    <p class="link-text">{reset_link}</p>
                </div>

                <div class="warning">
                    <p><strong>⚠️ Important:</strong> This password reset link will expire in 1 hour for security reasons.</p>
                </div>

                <div class="info-box">
                    <p><strong>ℹ️ Didn't request this?</strong> If you didn't request a password reset, please ignore this email. Your password will remain unchanged and your account is secure.</p>
                </div>

                <p>If you're having trouble or have concerns about your account security, please contact our support team.</p>
            </div>
            <div class="footer">
                <p><strong>KU RUN Check-in System</strong></p>
                <p>Kasetsart University Running Events</p>
                <p style="margin-top: 15px;">&copy; 2025 KU RUN. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """

    return send_email(to_email, subject, html_content)