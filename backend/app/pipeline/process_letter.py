import time
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from backend.app.db import AsyncSessionLocal
from backend.app.models import (
    QueryLetter, Document, Patient, QueryPoint, PointDecision, OutboundMessage, Job
)
from backend.app.ingest.extract import extract_document_text
from backend.app.storage import read_decrypted_file
from backend.app.llm.point_extractor import extract_query_points
from backend.app.llm.matcher import match_points_with_locker
from backend.app.pipeline.compose import compose_messages
from backend.app.security import mask_phone, mask_email
from backend.app.delivery.base import OutboundPayload
from backend.app.delivery.factory import get_whatsapp_provider, get_email_provider


async def run_process_letter_pipeline(query_letter_id: str):
    """
    Executes the 8-step Query Letter pipeline end-to-end.
    Persists timings in pipeline_trace. Idempotent and crash-resilient.
    """
    start_total_time = time.time()
    trace: Dict[str, Any] = {}

    async with AsyncSessionLocal() as session:
        # Load QueryLetter
        ql_res = await session.execute(
            select(QueryLetter).where(QueryLetter.id == query_letter_id)
        )
        ql = ql_res.scalar_one_or_none()
        if not ql:
            return

        # Load Patient and Document
        p_res = await session.execute(select(Patient).where(Patient.id == ql.patient_id))
        patient = p_res.scalar_one_or_none()

        d_res = await session.execute(select(Document).where(Document.id == ql.document_id))
        doc = d_res.scalar_one_or_none()

        if not patient or not doc:
            ql.status = "failed"
            ql.status_detail = "Missing patient or letter document"
            await session.commit()
            return

        ql.started_at = datetime.now(timezone.utc)
        ql.status = "extracting"
        await session.commit()

        try:
            # Step 1: Load and extract text
            t0 = time.time()
            letter_text = doc.redacted_text
            if not letter_text:
                file_bytes = await read_decrypted_file(doc.storage_path)
                raw_text, method, legibility = extract_document_text(file_bytes, doc.mime, doc.filename)
                letter_text = raw_text
                doc.extracted_text_enc = raw_text
                doc.legibility_score = legibility
            trace["step1_extract_ms"] = int((time.time() - t0) * 1000)

            # Check legibility
            if (doc.legibility_score or 1.0) < 0.40 and len(letter_text.strip()) < 50:
                ql.status = "needs_review"
                ql.status_detail = "Query letter legibility too low to parse automatically"
                ql.pipeline_trace = trace
                await session.commit()
                return

            # Step 2 & 3: Extract points
            t0 = time.time()
            ql.status = "extracting"
            extracted_pts, pt_meta = await extract_query_points(letter_text, patient_name=patient.full_name)
            trace["step3_points_ms"] = int((time.time() - t0) * 1000)

            # Atomic replace of QueryPoint rows
            await session.execute(delete(QueryPoint).where(QueryPoint.query_letter_id == ql.id))
            created_points = []
            for p_idx, pt in enumerate(extracted_pts, start=1):
                qp = QueryPoint(
                    query_letter_id=ql.id,
                    ordinal=p_idx,
                    verbatim_text=pt.get("verbatim_text", "")[:1000],
                    normalized_ask=pt.get("normalized_ask", "")[:500],
                    point_type=pt.get("point_type", "document_request"),
                    requested_doc_types=pt.get("requested_doc_types", []),
                    period_constraint=pt.get("period_constraint"),
                    confidence=float(pt.get("confidence", 0.90))
                )
                session.add(qp)
                created_points.append(qp)

            await session.flush()

            # Step 4: Snapshot Locker
            t0 = time.time()
            ql.status = "matching"
            locker_res = await session.execute(
                select(Document).where(
                    Document.patient_id == patient.id,
                    Document.doc_kind == "general",
                    Document.is_superseded == False
                )
            )
            raw_locker_docs = locker_res.scalars().all()
            locker_snapshot = [
                {
                    "id": d.id,
                    "doc_type": d.doc_type,
                    "filename": d.filename,
                    "legibility_score": d.legibility_score,
                    "is_superseded": d.is_superseded,
                    "meta": d.meta or {}
                }
                for d in raw_locker_docs
            ]
            trace["step4_snapshot_ms"] = int((time.time() - t0) * 1000)

            # Step 5: Decide per point + Guardrails
            t0 = time.time()
            point_payloads = [
                {
                    "ordinal": qp.ordinal,
                    "verbatim_text": qp.verbatim_text,
                    "normalized_ask": qp.normalized_ask,
                    "point_type": qp.point_type,
                    "requested_doc_types": qp.requested_doc_types
                }
                for qp in created_points
            ]
            decisions = await match_points_with_locker(point_payloads, locker_snapshot)
            trace["step5_matching_ms"] = int((time.time() - t0) * 1000)

            # Save PointDecision rows
            for i, dec in enumerate(decisions):
                if i < len(created_points):
                    parent_point = created_points[i]
                    pd = PointDecision(
                        query_point_id=parent_point.id,
                        decision=dec.get("decision", "needs_new_document"),
                        covering_document_ids=dec.get("covering_document_ids", []),
                        needed_doc_types=dec.get("needed_doc_types", []),
                        reason_internal=dec.get("reason_internal"),
                        reason_patient=dec.get("reason_patient"),
                        confidence=float(dec.get("confidence", 0.90)),
                        guardrail_flags=dec.get("guardrail_flags", [])
                    )
                    session.add(pd)

            await session.flush()

            # Step 6: Compose WhatsApp and Email messages
            t0 = time.time()
            ql.status = "composing"
            patient_dict = {
                "id": patient.id,
                "full_name": patient.full_name,
                "phone_e164": patient.phone_e164,
                "email": patient.email,
                "insurer_name": patient.insurer_name
            }
            query_letter_dict = {
                "id": ql.id,
                "claim_ref": ql.claim_ref,
                "insurer_name": ql.insurer_name
            }
            wa_msg_data, em_msg_data = compose_messages(patient_dict, query_letter_dict, decisions)
            trace["step6_compose_ms"] = int((time.time() - t0) * 1000)

            # Step 7: Enqueue / execute parallel sends
            t0 = time.time()
            ql.status = "sending"

            # Check existing messages for idempotency
            existing_msgs_res = await session.execute(
                select(OutboundMessage).where(OutboundMessage.query_letter_id == ql.id)
            )
            existing_msgs = {m.channel: m for m in existing_msgs_res.scalars().all()}

            # Setup WhatsApp OutboundMessage row
            wa_msg = existing_msgs.get("whatsapp")
            if not wa_msg:
                wa_msg = OutboundMessage(
                    query_letter_id=ql.id,
                    patient_id=patient.id,
                    channel="whatsapp",
                    recipient_masked=mask_phone(patient.phone_e164),
                    template_version=wa_msg_data["template_version"],
                    body_rendered=wa_msg_data["body"],
                    status="queued",
                    idempotency_key=wa_msg_data["idempotency_key"]
                )
                session.add(wa_msg)

            # Setup Email OutboundMessage row
            em_msg = existing_msgs.get("email")
            if not em_msg:
                em_msg = OutboundMessage(
                    query_letter_id=ql.id,
                    patient_id=patient.id,
                    channel="email",
                    recipient_masked=mask_email(patient.email),
                    template_version=em_msg_data["template_version"],
                    body_rendered=em_msg_data["body_text"],
                    status="queued",
                    idempotency_key=em_msg_data["idempotency_key"]
                )
                session.add(em_msg)

            await session.commit()

            # Send both channels in PARALLEL via asyncio.gather
            wa_provider = get_whatsapp_provider()
            em_provider = get_email_provider()

            wa_payload = OutboundPayload(
                channel="whatsapp",
                recipient=patient.phone_e164,
                body=wa_msg_data["body"],
                idempotency_key=wa_msg_data["idempotency_key"]
            )

            em_payload = OutboundPayload(
                channel="email",
                recipient=patient.email,
                body=em_msg_data["body_text"],
                subject=em_msg_data["subject"],
                body_html=em_msg_data["body_html"],
                idempotency_key=em_msg_data["idempotency_key"]
            )

            # Execute parallel sends
            wa_res, em_res = await asyncio.gather(
                wa_provider.send(wa_payload),
                em_provider.send(em_payload),
                return_exceptions=True
            )

            trace["step7_send_ms"] = int((time.time() - t0) * 1000)

            # Update WhatsApp message status
            now = datetime.now(timezone.utc)
            if isinstance(wa_res, Exception):
                wa_msg.status = "failed"
                wa_msg.status_detail = str(wa_res)
                wa_msg.failed_at = now
            elif wa_res.accepted:
                wa_msg.status = "sent"
                wa_msg.provider = wa_provider.name
                wa_msg.provider_message_id = wa_res.provider_message_id
                wa_msg.sent_at = now
            else:
                wa_msg.status = "failed"
                wa_msg.status_detail = wa_res.error_message
                wa_msg.failed_at = now

            # Update Email message status
            if isinstance(em_res, Exception):
                em_msg.status = "failed"
                em_msg.status_detail = str(em_res)
                em_msg.failed_at = now
            elif em_res.accepted:
                em_msg.status = "sent"
                em_msg.provider = em_provider.name
                em_msg.provider_message_id = em_res.provider_message_id
                em_msg.sent_at = now
            else:
                em_msg.status = "failed"
                em_msg.status_detail = em_res.error_message
                em_msg.failed_at = now

            # Step 8: Finalize QueryLetter
            total_ms = int((time.time() - start_total_time) * 1000)
            trace["total_ms"] = total_ms

            ql.completed_at = now
            ql.total_ms = total_ms
            ql.pipeline_trace = trace

            # Set final status
            if any(d.get("confidence", 1.0) < 0.45 for d in decisions):
                ql.status = "needs_review"
            else:
                ql.status = "completed"

            await session.commit()

        except Exception as exc:
            total_ms = int((time.time() - start_total_time) * 1000)
            trace["total_ms"] = total_ms
            ql.status = "needs_review"
            ql.status_detail = f"Degraded execution: {str(exc)[:200]}"
            ql.completed_at = datetime.now(timezone.utc)
            ql.total_ms = total_ms
            ql.pipeline_trace = trace
            await session.commit()
