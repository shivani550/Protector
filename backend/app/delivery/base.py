from dataclasses import dataclass
from typing import Optional, Protocol, Dict, Any


@dataclass
class OutboundPayload:
    channel: str  # "whatsapp" or "email"
    recipient: str  # E.164 phone or email address
    body: str  # plain text rendered message
    subject: Optional[str] = None  # for email
    body_html: Optional[str] = None  # for email HTML
    idempotency_key: Optional[str] = None


@dataclass
class SendResult:
    accepted: bool
    provider_message_id: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None


class Provider(Protocol):
    name: str

    async def send(self, msg: OutboundPayload) -> SendResult:
        ...
