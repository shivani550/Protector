import pytest
import httpx
from backend.app.main import app
from backend.app.security import create_access_token


@pytest.mark.asyncio
async def test_admin_endpoints():
    admin_token = create_access_token({"sub": "admin-demo-uuid", "role": "admin"})
    worker_token = create_access_token({"sub": "worker-demo-uuid", "role": "case_worker"})
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Non-admin forbidden
        res = await client.get("/api/admin/stats", headers={"Authorization": f"Bearer {worker_token}"})
        assert res.status_code == 403

        # 2. Admin stats
        res = await client.get("/api/admin/stats", headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 200
        data = res.json()
        assert "total_patients" in data
        assert "letters_completed" in data

        # 3. Preflight status
        res = await client.get("/api/admin/preflight", headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 200
        pf = res.json()
        assert "overall_status" in pf
        assert "components" in pf

        # 4. Audit logs
        res = await client.get("/api/admin/audit", headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 200
        logs = res.json()
        assert isinstance(logs, list)
