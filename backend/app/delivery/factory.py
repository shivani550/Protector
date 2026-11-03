from backend.app.config import settings
from backend.app.delivery.base import Provider
from backend.app.delivery.mock import MockProvider
from backend.app.delivery.whatsapp_twilio import TwilioProvider
from backend.app.delivery.email_smtp import SmtpProvider


def get_whatsapp_provider() -> Provider:
    if settings.DELIVERY_MODE == "mock" or settings.WHATSAPP_PROVIDER == "mock":
        return MockProvider("mock_whatsapp")
    elif settings.WHATSAPP_PROVIDER == "twilio":
        return TwilioProvider()
    return MockProvider("mock_whatsapp")


def get_email_provider() -> Provider:
    if settings.DELIVERY_MODE == "mock" or settings.EMAIL_PROVIDER == "mock":
        return MockProvider("mock_email")
    elif settings.EMAIL_PROVIDER == "smtp":
        return SmtpProvider()
    return MockProvider("mock_email")
