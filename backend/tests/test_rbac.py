import pytest
import pytest_asyncio
import httpx
from sqlalchemy import select
from backend.app.main import app
from backend.app.db import AsyncSessionLocal, Base, engine
from backend.app.models import User, Patient, CaseAssignment, AuditLog
from backend.app.security import hash_password, encrypt_text, create_access_token


async def init_test_data():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # Check if already seeded
        chk = await session.execute(select(Patient).where(Patient.id == "pt-a-uuid"))
        if chk.scalar_one_or_none():
            return

        # Create Patient A
        patient_a = Patient(
            id="pt-a-uuid",
            patient_code="TEST-RBAC-001",
            full_name="Rajesh Sharma",
            dob="1982-05-14",
            gender="male",
            phone_e164="+919876543210",
            email="rajesh@test.com",
            insurer_name="Star Health",
            policy_number_enc=encrypt_text("SH-99221100"),
            policy_number_last4="1100",
            aadhaar_enc=encrypt_text("123456789012"),
            aadhaar_last4="9012"
        )
        # Create Patient B
        patient_b = Patient(
            id="pt-b-uuid",
            patient_code="TEST-RBAC-002",
            full_name="Priya Patel",
            dob="1990-11-22",
            gender="female",
            phone_e164="+919876543211",
            email="priya@test.com",
            insurer_name="HDFC ERGO",
            policy_number_enc=encrypt_text("HE-88776655"),
            policy_number_last4="6655",
            aadhaar_enc=encrypt_text("987654321098"),
            aadhaar_last4="1098"
        )
        session.add(patient_a)
        session.add(patient_b)
        await session.flush()

        # Users
        admin_user = User(
            id="usr-admin",
            email="admin@test.com",
            password_hash=hash_password("adminpass"),
            role="admin",
            is_active=True
        )
        worker_user = User(
            id="usr-worker",
            email="worker@test.com",
            password_hash=hash_password("workerpass"),
            role="case_worker",
            is_active=True
        )
        patient_a_user = User(
            id="usr-patient-a",
            email="patient_a@test.com",
            password_hash=hash_password("patientpass"),
            role="patient",
            patient_id="pt-a-uuid",
            is_active=True
        )
        patient_b_user = User(
            id="usr-patient-b",
            email="patient_b@test.com",
            password_hash=hash_password("patientpass"),
            role="patient",
            patient_id="pt-b-uuid",
            is_active=True
        )

        session.add(admin_user)
        session.add(worker_user)
        session.add(patient_a_user)
        session.add(patient_b_user)
        await session.flush()

        # Assign worker to Patient A ONLY
        assignment = CaseAssignment(
            user_id="usr-worker",
            patient_id="pt-a-uuid"
        )
        session.add(assignment)
        await session.commit()


@pytest.mark.asyncio
async def test_rbac_access_matrix():
    await init_test_data()

    admin_token = create_access_token({"sub": "usr-admin", "role": "admin"})
    worker_token = create_access_token({"sub": "usr-worker", "role": "case_worker"})
    patient_a_token = create_access_token({"sub": "usr-patient-a", "role": "patient", "patient_id": "pt-a-uuid"})
    patient_b_token = create_access_token({"sub": "usr-patient-b", "role": "patient", "patient_id": "pt-b-uuid"})

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Unauthenticated -> 401
        res = await client.get("/api/patients/pt-a-uuid")
        assert res.status_code == 401

        # 2. Admin -> Allowed on both patients
        res = await client.get("/api/patients/pt-a-uuid", headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 200
        assert res.json()["patient_code"] == "TEST-RBAC-001"

        res = await client.get("/api/patients/pt-b-uuid", headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 200
        assert res.json()["patient_code"] == "TEST-RBAC-002"

        # 3. Case Worker -> Allowed on assigned Patient A
        res = await client.get("/api/patients/pt-a-uuid", headers={"Authorization": f"Bearer {worker_token}"})
        assert res.status_code == 200
        assert res.json()["patient_code"] == "TEST-RBAC-001"

        # 4. Case Worker -> Denied on unassigned Patient B (403)
        res = await client.get("/api/patients/pt-b-uuid", headers={"Authorization": f"Bearer {worker_token}"})
        assert res.status_code == 403

        # 5. Patient A -> Allowed on self (pt-a-uuid)
        res = await client.get("/api/patients/pt-a-uuid", headers={"Authorization": f"Bearer {patient_a_token}"})
        assert res.status_code == 200
        assert res.json()["patient_code"] == "TEST-RBAC-001"

        # 6. Patient A -> Denied on foreign patient B (404 to avoid enumeration)
        res = await client.get("/api/patients/pt-b-uuid", headers={"Authorization": f"Bearer {patient_a_token}"})
        assert res.status_code == 404

        # 7. Patient List Scoping
        # Admin sees seeded + test patients
        res = await client.get("/api/patients", headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 200
        assert len(res.json()) >= 2

        # Worker sees assigned Patient A
        res = await client.get("/api/patients", headers={"Authorization": f"Bearer {worker_token}"})
        assert res.status_code == 200
        worker_patients = res.json()
        assert any(p["patient_code"] == "TEST-RBAC-001" for p in worker_patients)

        # Patient A sees 1 patient (self)
        res = await client.get("/api/patients", headers={"Authorization": f"Bearer {patient_a_token}"})
        assert res.status_code == 200
        assert len(res.json()) == 1
        assert res.json()[0]["patient_code"] == "TEST-RBAC-001"


@pytest.mark.asyncio
async def test_audit_logs_recorded():
    await init_test_data()

    async with AsyncSessionLocal() as session:
        # Check that denials are recorded with result='denied'
        denials = await session.execute(
            select(AuditLog).where(AuditLog.result == "denied")
        )
        denied_rows = denials.scalars().all()
        assert len(denied_rows) >= 2
        denied_actors = [d.actor_role for d in denied_rows]
        assert "case_worker" in denied_actors or "patient" in denied_actors

        # Check allowed entries exist
        allowed = await session.execute(
            select(AuditLog).where(AuditLog.result == "allowed")
        )
        allowed_rows = allowed.scalars().all()
        assert len(allowed_rows) >= 2
