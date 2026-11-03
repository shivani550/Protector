import uuid
from email.message import EmailMessage
from typing import Optional
import aiosmtplib

from backend.app.config import settings
from backend.app.delivery.base import Provider, OutboundPayload, SendResult


class SmtpProvider(Provider):
    name = "smtp_email"

    def __init__(self):
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.user = settings.SMTP_USER
        self.password = settings.SMTP_APP_PASSWORD
        self.from_email = settings.EMAIL_FROM
        self.from_name = settings.EMAIL_FROM_NAME

    async def send(self, msg: OutboundPayload) -> SendResult:
        if not self.user or not self.password:
            return SendResult(
                accepted=False,
                error_code="CREDENTIALS_MISSING",
                error_message="SMTP User or App Password is not configured in environment"
            )

        message_id = f"<{uuid.uuid4().hex}@{self.host}>"

        email = EmailMessage()
        email["Subject"] = msg.subject or "Claim Update Notification"
        email["From"] = f"{self.from_name} <{self.from_email}>"
        email["To"] = msg.recipient
        email["Message-ID"] = message_id

        # Plain text
        email.set_content(msg.body)

        # HTML alternative if provided
        if msg.body_html:
            email.add_alternative(msg.body_html, subtype="html")

        try:
            await aiosmtplib.send(
                email,
                hostname=self.host,
                port=self.port,
                username=self.user,
                password=self.password,
                start_tls=True,
                timeout=15.0
            )
            return SendResult(
                accepted=True,
                provider_message_id=message_id
            )
        except Exception as e:
            return SendResult(
                accepted=False,
                error_code="SMTP_ERROR",
                error_message=f"Failed to send email via SMTP: {str(e)}"
            )
