"""
Notification Service - Handles sending notifications through various channels
Save as: src/services/notification_service.py
"""
import asyncio
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.notification import Notification, NotificationChannel
from src.crud import notification_crud
from src.services.email_service import send_email
import logging

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending notifications through various channels"""

    def __init__(self):
        self.max_retries = 3

    async def send_notification(
            self,
            db: AsyncSession,
            notification: Notification
    ) -> bool:
        """
        Send a single notification through its designated channel

        Returns:
            bool: True if sent successfully, False otherwise
        """
        try:
            if notification.channel == NotificationChannel.IN_APP:
                # In-app notifications are instantly "sent" when created
                success = True

            elif notification.channel == NotificationChannel.EMAIL:
                success = await self._send_email_notification(notification)

            elif notification.channel == NotificationChannel.PUSH:
                success = await self._send_push_notification(notification)

            elif notification.channel == NotificationChannel.SMS:
                success = await self._send_sms_notification(notification)

            else:
                logger.error(f"Unknown notification channel: {notification.channel}")
                success = False

            # Mark as sent or failed
            await notification_crud.mark_as_sent(
                db,
                [notification.id],
                success=success,
                error_message=None if success else f"Failed to send via {notification.channel}"
            )

            return success

        except Exception as e:
            logger.error(f"Error sending notification {notification.id}: {e}")
            await notification_crud.mark_as_sent(
                db,
                [notification.id],
                success=False,
                error_message=str(e)
            )
            return False

    async def _send_email_notification(self, notification: Notification) -> bool:
        """Send notification via email"""
        try:
            # Get user email from notification.user relationship
            if not notification.user or not notification.user.email:
                logger.error(f"No email found for user {notification.user_id}")
                return False

            user_email = notification.user.email
            subject = f"KU RUN - {notification.title}"

            # Build HTML email content
            html_content = self._build_email_html(notification)

            # Send email
            success = send_email(user_email, subject, html_content)

            if success:
                logger.info(f"Email sent successfully to {user_email}")
            else:
                logger.error(f"Failed to send email to {user_email}")

            return success

        except Exception as e:
            logger.error(f"Error sending email notification: {e}")
            return False

    def _build_email_html(self, notification: Notification) -> str:
        """Build HTML content for email notification"""
        return f"""
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
                    background-color: #f9f9f9;
                }}
                .header {{
                    background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 8px 8px 0 0;
                }}
                .content {{
                    background: white;
                    padding: 30px;
                    border-radius: 0 0 8px 8px;
                }}
                .message {{
                    font-size: 16px;
                    line-height: 1.8;
                }}
                .footer {{
                    margin-top: 20px;
                    padding-top: 20px;
                    border-top: 1px solid #e0e0e0;
                    text-align: center;
                    color: #666;
                    font-size: 14px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>{notification.title}</h2>
                </div>
                <div class="content">
                    <div class="message">
                        {notification.message}
                    </div>
                    <div class="footer">
                        <p><strong>KU RUN Check-in System</strong></p>
                        <p>Kasetsart University Running Events</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

    async def _send_push_notification(self, notification: Notification) -> bool:
        """Send notification via push (placeholder)"""
        # TODO: Implement push notification (e.g., Firebase Cloud Messaging)
        logger.info(f"Push notification not implemented yet for notification {notification.id}")
        return False

    async def _send_sms_notification(self, notification: Notification) -> bool:
        """Send notification via SMS (placeholder)"""
        # TODO: Implement SMS notification (e.g., Twilio)
        logger.info(f"SMS notification not implemented yet for notification {notification.id}")
        return False

    async def send_pending_notifications(
            self,
            db: AsyncSession,
            limit: int = 100
    ) -> dict:
        """
        Send all pending notifications (batch processing)

        Returns:
            dict: Statistics about sent notifications
        """
        # Get pending notifications
        pending = await notification_crud.get_pending_notifications(db, limit=limit)

        if not pending:
            return {
                "total": 0,
                "sent": 0,
                "failed": 0
            }

        sent_count = 0
        failed_count = 0

        for notification in pending:
            success = await self.send_notification(db, notification)
            if success:
                sent_count += 1
            else:
                failed_count += 1

        return {
            "total": len(pending),
            "sent": sent_count,
            "failed": failed_count
        }

    async def retry_failed_notifications(
            self,
            db: AsyncSession,
            max_attempts: int = 3
    ) -> dict:
        """
        Retry sending failed notifications that haven't exceeded max attempts

        Returns:
            dict: Statistics about retry results
        """
        from src.models.notification import NotificationStatus
        from sqlalchemy.future import select

        # Get failed notifications that haven't exceeded max attempts
        result = await db.execute(
            select(Notification).where(
                Notification.status == NotificationStatus.FAILED,
                Notification.send_attempts < max_attempts
            ).limit(50)
        )
        failed_notifications = result.scalars().all()

        if not failed_notifications:
            return {
                "total": 0,
                "sent": 0,
                "failed": 0
            }

        sent_count = 0
        failed_count = 0

        for notification in failed_notifications:
            success = await self.send_notification(db, notification)
            if success:
                sent_count += 1
            else:
                failed_count += 1

        return {
            "total": len(failed_notifications),
            "sent": sent_count,
            "failed": failed_count
        }


# Global instance
notification_service = NotificationService()


# Background task runner (optional - for scheduled sending)
async def notification_worker(db: AsyncSession):
    """
    Background worker to send pending notifications
    Run this as a background task or scheduled job
    """
    while True:
        try:
            stats = await notification_service.send_pending_notifications(db, limit=50)
            logger.info(f"Notification batch sent: {stats}")

            # Wait before next batch
            await asyncio.sleep(60)  # Check every minute

        except Exception as e:
            logger.error(f"Error in notification worker: {e}")
            await asyncio.sleep(60)