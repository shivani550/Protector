import uuid
from datetime import datetime, timezone
from typing import Optional, List, Any
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text, JSON, ForeignKey, Index
)
from sqlalchemy.orm import relationship
from backend.app.db import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def gen_uuid() -> str:
    return str(uuid.uuid4())


class TimestampMixin:
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(32), nullable=False, default="patient")  # admin | case_worker | patient
    patient_id = Column(String(36), ForeignKey("patients.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    patient = relationship("Patient", back_populates="user", foreign_keys=[patient_id])
    case_assignments = relationship("CaseAssignment", back_populates="user", cascade="all, delete-orphan")


class CaseAssignment(Base, TimestampMixin):
    __tablename__ = "case_assignments"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    patient_id = Column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)

    user = relationship("User", back_populates="case_assignments")
    patient = relationship("Patient", back_populates="case_assignments")

    __table_args__ = (
        Index("ix_case_assignment_user_patient", "user_id", "patient_id", unique=True),
    )


class Patient(Base, TimestampMixin):
    __tablename__ = "patients"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    patient_code = Column(String(32), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    dob = Column(String(32), nullable=True)  # YYYY-MM-DD
    gender = Column(String(16), nullable=True)
    phone_e164 = Column(String(32), nullable=False)
    email = Column(String(255), nullable=False)
    preferred_language = Column(String(16), default="en", nullable=False)
    insurer_name = Column(String(255), nullable=False)

    policy_number_enc = Column(Text, nullable=False)
    policy_number_last4 = Column(String(8), nullable=False)
    aadhaar_enc = Column(Text, nullable=True)
    aadhaar_last4 = Column(String(8), nullable=True)

    consent_whatsapp = Column(Boolean, default=True, nullable=False)
    consent_email = Column(Boolean, default=True, nullable=False)

    user = relationship("User", back_populates="patient", uselist=False)
    case_assignments = relationship("CaseAssignment", back_populates="patient", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="patient", cascade="all, delete-orphan")
    query_letters = relationship("QueryLetter", back_populates="patient", cascade="all, delete-orphan")
    outbound_messages = relationship("OutboundMessage", back_populates="patient", cascade="all, delete-orphan")


class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    patient_id = Column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    mime = Column(String(128), nullable=False)
    size = Column(Integer, nullable=False)
    sha256 = Column(String(64), nullable=False, index=True)
    storage_path = Column(Text, nullable=False)
    uploaded_by = Column(String(64), nullable=False, default="patient")
    source = Column(String(32), nullable=False, default="patient")  # patient | staff | insurer | system
    doc_kind = Column(String(32), nullable=False, default="general")  # general | query_letter

    doc_type = Column(String(64), nullable=True)  # taxonomy key
    doc_type_confidence = Column(Float, nullable=True)
    classification_status = Column(String(32), nullable=False, default="pending")  # pending | done | failed

    extracted_text_enc = Column(Text, nullable=True)
    redacted_text = Column(Text, nullable=True)
    extraction_method = Column(String(32), nullable=True)  # text | ocr | vision | docx
    legibility_score = Column(Float, nullable=True)  # 0.0 - 1.0

    meta = Column(JSON, nullable=True, default=dict)
    is_superseded = Column(Boolean, default=False, nullable=False)
    claim_ref = Column(String(128), nullable=True)

    patient = relationship("Patient", back_populates="documents")
    query_letter = relationship("QueryLetter", back_populates="document", uselist=False)

    __table_args__ = (
        Index("ix_doc_patient_doctype", "patient_id", "doc_type"),
        Index("ix_doc_patient_sha", "patient_id", "sha256"),
    )


class QueryLetter(Base, TimestampMixin):
    __tablename__ = "query_letters"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    patient_id = Column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), unique=True, nullable=False)
    claim_ref = Column(String(128), nullable=True)
    insurer_name = Column(String(255), nullable=True)
    received_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    status = Column(String(32), nullable=False, default="received")  # received | extracting | matching | composing | sending | completed | failed | needs_review
    status_detail = Column(Text, nullable=True)
    prompt_version = Column(String(32), default="v1", nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    total_ms = Column(Integer, nullable=True)
    pipeline_trace = Column(JSON, nullable=True, default=dict)
    run_no = Column(Integer, default=1, nullable=False)

    patient = relationship("Patient", back_populates="query_letters")
    document = relationship("Document", back_populates="query_letter")
    points = relationship("QueryPoint", back_populates="query_letter", cascade="all, delete-orphan", order_by="QueryPoint.ordinal")
    messages = relationship("OutboundMessage", back_populates="query_letter", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_query_letter_patient_status", "patient_id", "status"),
    )


class QueryPoint(Base, TimestampMixin):
    __tablename__ = "query_points"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    query_letter_id = Column(String(36), ForeignKey("query_letters.id", ondelete="CASCADE"), nullable=False, index=True)
    ordinal = Column(Integer, nullable=False)
    verbatim_text = Column(Text, nullable=False)
    normalized_ask = Column(Text, nullable=False)
    point_type = Column(String(64), nullable=False)  # document_request | clarification | info_confirmation | policy_condition | insurer_internal | other
    requested_doc_types = Column(JSON, nullable=True, default=list)
    period_constraint = Column(String(255), nullable=True)
    confidence = Column(Float, default=1.0, nullable=False)

    query_letter = relationship("QueryLetter", back_populates="points")
    decision = relationship("PointDecision", back_populates="query_point", uselist=False, cascade="all, delete-orphan")


class PointDecision(Base, TimestampMixin):
    __tablename__ = "point_decisions"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    query_point_id = Column(String(36), ForeignKey("query_points.id", ondelete="CASCADE"), unique=True, nullable=False)
    decision = Column(String(64), nullable=False)  # covered | needs_new_document | needs_patient_clarification | no_patient_action
    covering_document_ids = Column(JSON, nullable=True, default=list)
    needed_doc_types = Column(JSON, nullable=True, default=list)
    reason_internal = Column(Text, nullable=True)
    reason_patient = Column(String(280), nullable=True)  # plain English, <=140 chars in final
    confidence = Column(Float, default=1.0, nullable=False)
    guardrail_flags = Column(JSON, nullable=True, default=list)
    llm_raw = Column(JSON, nullable=True, default=dict)

    query_point = relationship("QueryPoint", back_populates="decision")


class MessageTemplate(Base, TimestampMixin):
    __tablename__ = "message_templates"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(128), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    body_whatsapp = Column(Text, nullable=False)
    body_email_subject = Column(String(255), nullable=False)
    body_email_html = Column(Text, nullable=False)
    body_email_text = Column(Text, nullable=False)
    loaded_from_file_hash = Column(String(64), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)


class OutboundMessage(Base, TimestampMixin):
    __tablename__ = "outbound_messages"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    query_letter_id = Column(String(36), ForeignKey("query_letters.id", ondelete="CASCADE"), nullable=False, index=True)
    patient_id = Column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    channel = Column(String(32), nullable=False)  # whatsapp | email
    recipient_masked = Column(String(128), nullable=False)
    template_version = Column(Integer, default=1, nullable=False)
    body_rendered = Column(Text, nullable=False)

    status = Column(String(32), nullable=False, default="queued")  # queued | sending | sent | delivered | read | failed | skipped
    status_detail = Column(Text, nullable=True)
    provider = Column(String(64), nullable=True)
    provider_message_id = Column(String(255), nullable=True, index=True)
    attempts = Column(Integer, default=0, nullable=False)

    queued_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    idempotency_key = Column(String(128), unique=True, nullable=False, index=True)

    query_letter = relationship("QueryLetter", back_populates="messages")
    patient = relationship("Patient", back_populates="outbound_messages")

    __table_args__ = (
        Index("ix_outbound_letter_channel", "query_letter_id", "channel"),
    )


class Job(Base, TimestampMixin):
    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    type = Column(String(64), nullable=False)  # classify_document | process_letter | send_message
    payload = Column(JSON, nullable=False, default=dict)
    status = Column(String(32), nullable=False, default="pending")  # pending | running | done | failed | dead
    attempts = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=5, nullable=False)
    priority = Column(Integer, default=5, nullable=False)  # 0 highest (letters), 5 default
    run_after = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    locked_by = Column(String(128), nullable=True)
    locked_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)
    dedupe_key = Column(String(128), unique=True, nullable=False, index=True)

    __table_args__ = (
        Index("ix_jobs_status_run_after", "status", "run_after", "priority"),
    )


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    ts = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    actor_user_id = Column(String(36), nullable=True, index=True)
    actor_role = Column(String(32), nullable=True)
    action = Column(String(64), nullable=False)  # login | view_patient | view_document | download_document | upload_document | view_letter | view_messages | admin_view | export
    patient_id = Column(String(36), nullable=True, index=True)
    object_type = Column(String(64), nullable=True)
    object_id = Column(String(64), nullable=True)
    ip = Column(String(64), nullable=True)
    result = Column(String(32), nullable=False, default="allowed")  # allowed | denied
