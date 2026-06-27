import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from app.core.config import settings

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.client = SendGridAPIClient(settings.SENDGRID_API_KEY) if settings.SENDGRID_API_KEY else None

    async def send_email(self, to_email: str, subject: str, html_content: str):
        if not self.client:
            logger.warning(f"SendGrid not configured. Skipping email to {to_email}")
            return False
        message = Mail(from_email=settings.SENDGRID_FROM_EMAIL, to_emails=to_email, subject=subject, html_content=html_content)
        try:
            response = self.client.send(message)
            logger.info(f"Email sent to {to_email}: {response.status_code}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    async def send_verification_email(self, to_email: str, token: str):
        link = f"{settings.FRONTEND_URL}/verify-email?token={token}"
        html = f"<p>مرحباً بك في منصة قانوني،</p><p>يرجى تأكيد بريدك الإلكتروني بالضغط على الرابط أدناه:</p><p><a href='{link}'>تأكيد البريد الإلكتروني</a></p>"
        await self.send_email(to_email, "تأكيد البريد الإلكتروني - منصة قانوني", html)

    async def send_password_reset(self, to_email: str, token: str):
        link = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        html = f"<p>لقد استلمنا طلباً لإعادة تعيين كلمة مرور حسابك في منصة قانوني.</p><p>اضغط على الرابط أدناه لإعادة تعيين كلمة المرور:</p><p><a href='{link}'>إعادة تعيين كلمة المرور</a></p><p>إذا لم تطلب ذلك، يرجى تجاهل هذا البريد.</p>"
        await self.send_email(to_email, "إعادة تعيين كلمة المرور - منصة قانوني", html)

email_service = EmailService()
