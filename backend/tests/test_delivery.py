import pytest
import httpx
from sqlalchemy import select
from backend.app.main import app
from backend.app.db import AsyncSessionLocal
from backend.app.models import Patient, QueryLetter, OutboundMessage
from backend.app.security import create_access_token


@pytest.mark.asyncio
async def test_messages_api_retrieval():
    admin_token = create_access_token({"sub": "admin-demo-uuid", "role": "admin"})
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Find PT-0001
        p_res = await client.get("/api/patients", headers={"Authorization": f"Bearer {admin_token}"})
        assert p_res.status_code == 200
        patients = p_res.json()
        pt1 = next(p for p in patients if p["patient_code"] == "PT-0001")

        # Get messages for PT-0001
        msgs_res = await client.get(f"/api/patients/{pt1['id']}/messages", headers={"Authorization": f"Bearer {admin_token}"})
        assert msgs_res.status_code == 200
        messages = msgs_res.json()

        assert len(messages) >= 2
        channels = {m["channel"] for m in messages}
        assert "whatsapp" in channels
        assert "email" in channels

        for m in messages:
            assert m["status"] in ("sent", "delivered")
            assert len(m["body_rendered"]) > 20
            assert m["idempotency_key"] is not None
