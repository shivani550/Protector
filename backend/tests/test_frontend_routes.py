import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app

@pytest.mark.asyncio
async def test_health_check():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"
        assert data["service"] == "protector-api"

@pytest.mark.asyncio
async def test_spa_serving():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Root route
        res = await ac.get("/")
        assert res.status_code == 200
        assert "<div id=\"root\"></div>" in res.text

        # Deep SPA route
        res_patients = await ac.get("/patients")
        assert res_patients.status_code == 200
        assert "<div id=\"root\"></div>" in res_patients.text

        # Deep SPA route for upload
        res_upload = await ac.get("/upload/sample-token")
        assert res_upload.status_code == 200
        assert "<div id=\"root\"></div>" in res_upload.text
