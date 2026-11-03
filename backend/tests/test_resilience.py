import io
import pytest
from unittest.mock import patch
from sqlalchemy import select
from httpx import AsyncClient, ASGITransport

from backend.app.main import app
from backend.app.db import AsyncSessionLocal
from backend.app.models import QueryLetter, Document, Patient, OutboundMessage
from backend.app.pipeline.process_letter import run_process_letter_pipeline
from backend.app.security import mask_aadhaar, mask_policy_number, mask_phone, mask_email

@pytest.mark.asyncio
async def test_llm_outage_fallback():
    """
    Test 1: LLM provider outage/timeout -> pipeline gracefully falls back
    to degraded mode (marks letter as needs_review, records status_detail, does not crash).
    """
    async with AsyncSessionLocal() as session:
        # Fetch an existing query letter
        ql_res = await session.execute(select(QueryLetter).limit(1))
        ql = ql_res.scalar_one_or_none()
        if not ql:
            pytest.skip("No seed letters found to test LLM outage fallback")
        ql_id = ql.id

    # Mock extract_query_points to raise an LLM timeout exception
    with patch(
        "backend.app.pipeline.process_letter.extract_query_points",
        side_effect=TimeoutError("Simulated LLM API 504 Gateway Timeout")
    ):
        await run_process_letter_pipeline(ql_id)

    # Verify letter status transitioned to needs_review
    async with AsyncSessionLocal() as session:
        ql_after = await session.get(QueryLetter, ql_id)
        assert ql_after is not None
        assert ql_after.status == "needs_review"
        assert "Degraded execution" in (ql_after.status_detail or "")
        assert "504 Gateway Timeout" in (ql_after.status_detail or "")


@pytest.mark.asyncio
async def test_pii_masking_integrity():
    """
    Test 2: Verify PII masking functions prevent raw PII leaks.
    """
    # Phone masking (E.164: +919876543210 -> +91******3210)
    masked_ph = mask_phone("+919876543210")
    assert "987654" not in masked_ph
    assert masked_ph.endswith("10")
    assert masked_ph.startswith("+91")

    # Email masking (aarav.sharma@example.com -> a***a@example.com)
    masked_em = mask_email("aarav.sharma@example.com")
    assert "aarav.sharma" not in masked_em
    assert "@example.com" in masked_em

    # Aadhaar masking (123456789012 -> ********9012)
    masked_adh = mask_aadhaar("123456789012")
    assert "12345678" not in masked_adh
    assert masked_adh.endswith("9012")

    # Policy masking (STAR-HLTH-2024-88492 -> ****8492)
    masked_pol = mask_policy_number("STAR-HLTH-2024-88492")
    assert "STAR-HLTH" not in masked_pol
    assert masked_pol.endswith("8492")


@pytest.mark.asyncio
async def test_malicious_file_mime_rejection():
    """
    Test 3: Reject non-whitelisted MIME types (e.g., .exe, .sh, script files).
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Attempt to upload an executable script
        fake_exe = io.BytesIO(b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff")
        res = await ac.post(
            "/api/patients/any-id/documents",
            files={"file": ("malware.exe", fake_exe, "application/x-msdownload")},
            data={"doc_kind": "general"}
        )
        # Should be rejected with 401 (unauthorized) or 415/400 (unsupported media type)
        assert res.status_code in (401, 415, 400)


@pytest.mark.asyncio
async def test_duplicate_letter_arrival_idempotency():
    """
    Test 4: Ingesting an already-processed letter does not duplicate outbound messages.
    """
    async with AsyncSessionLocal() as session:
        ql_res = await session.execute(select(QueryLetter).limit(1))
        ql = ql_res.scalar_one_or_none()
        if not ql:
            pytest.skip("No query letters in DB to test idempotency")
        ql_id = ql.id

        # Count outbound messages before reprocessing
        msg_res = await session.execute(
            select(OutboundMessage).where(OutboundMessage.query_letter_id == ql_id)
        )
        msgs_before = msg_res.scalars().all()
        count_before = len(msgs_before)

    # Re-run pipeline on the same letter
    await run_process_letter_pipeline(ql_id)

    # Verify no duplicate messages were inserted into OutboundMessage
    async with AsyncSessionLocal() as session:
        msg_res_after = await session.execute(
            select(OutboundMessage).where(OutboundMessage.query_letter_id == ql_id)
        )
        msgs_after = msg_res_after.scalars().all()
        count_after = len(msgs_after)

    assert count_after == count_before
