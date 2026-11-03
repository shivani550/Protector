import uuid
import asyncio
from backend.app.delivery.base import Provider, OutboundPayload, SendResult


class MockProvider(Provider):
    def __init__(self, name: str = "mock_provider"):
        self.name = name

    async def send(self, msg: OutboundPayload) -> SendResult:
        # Simulate tiny network latency
        await asyncio.sleep(0.05)
        fake_msg_id = f"mock_{msg.channel}_{uuid.uuid4().hex[:12]}"
        return SendResult(
            accepted=True,
            provider_message_id=fake_msg_id,
            error_code=None,
            error_message=None
        )
