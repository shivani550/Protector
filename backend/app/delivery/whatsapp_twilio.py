import httpx
from typing import Optional
from backend.app.config import settings
from backend.app.delivery.base import Provider, OutboundPayload, SendResult


class TwilioProvider(Provider):
    name = "twilio_whatsapp"

    def __init__(self):
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token = settings.TWILIO_AUTH_TOKEN
        self.from_number = settings.TWILIO_WHATSAPP_FROM
        self.status_callback = f"{settings.PUBLIC_BASE_URL}/api/webhooks/twilio"

    async def send(self, msg: OutboundPayload) -> SendResult:
        if not self.account_sid or not self.auth_token:
            return SendResult(
                accepted=False,
                error_code="CREDENTIALS_MISSING",
                error_message="Twilio Account SID or Auth Token is not configured in environment"
            )

        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        
        # Ensure 'whatsapp:' prefix
        to_number = msg.recipient
        if not to_number.startswith("whatsapp:"):
            to_number = f"whatsapp:{to_number}"

        data = {
            "From": self.from_number,
            "To": to_number,
            "Body": msg.body,
            "StatusCallback": self.status_callback
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(
                    url,
                    data=data,
                    auth=(self.account_sid, self.auth_token)
                )
                
                resp_data = res.json()
                if res.status_code in (200, 201):
                    return SendResult(
                        accepted=True,
                        provider_message_id=resp_data.get("sid")
                    )
                else:
                    err_code = str(resp_data.get("code", res.status_code))
                    raw_msg = resp_data.get("message", "Twilio error")
                    # Map error codes
                    if err_code in ("63016", "63007", "63003"):
                        plain_err = "Recipient has not joined the Twilio Sandbox or 24h window is closed."
                    elif err_code == "21211":
                        plain_err = "Invalid phone number format."
                    else:
                        plain_err = f"Twilio rejected message: {raw_msg}"

                    return SendResult(
                        accepted=False,
                        error_code=err_code,
                        error_message=plain_err
                    )
        except Exception as e:
            return SendResult(
                accepted=False,
                error_code="NETWORK_ERROR",
                error_message=f"Failed to reach Twilio API: {str(e)}"
            )
