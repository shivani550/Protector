from typing import Optional, List, Any, Dict
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, ConfigDict


# Base Config
class SchemaBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# Auth Schemas
class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: str
    patient_id: Optional[str] = None


class UserOut(SchemaBase):
    id: str
    email: str
    role: str
    patient_id: Optional[str] = None
    is_active: bool
    created_at: datetime


# Patient Schemas
class PatientBase(BaseModel):
    patient_code: str
    full_name: str
    dob: Optional[str] = None
    gender: Optional[str] = None
    phone_e164: str
    email: EmailStr
    preferred_language: str = "en"
    insurer_name: str
    consent_whatsapp: bool = True
    consent_email: bool = True


class PatientCreate(PatientBase):
    policy_number: str
    aadhaar: Optional[str] = None


class PatientOut(SchemaBase):
    id: str
    patient_code: str
    full_name: str
    dob: Optional[str] = None
    gender: Optional[str] = None
    phone_e164: str
    email: str
    preferred_language: str
    insurer_name: str
    policy_number_masked: str
    aadhaar_masked: Optional[str] = None
    consent_whatsapp: bool
    consent_email: bool
    documents_count: Optional[int] = 0
    open_queries_count: Optional[int] = 0
    latest_query_status: Optional[str] = None
    created_at: datetime


class PatientDetailOut(PatientOut):
    policy_number_full: Optional[str] = None
    aadhaar_full: Optional[str] = None


# Document Schemas
class DocumentOut(SchemaBase):
    id: str
    patient_id: str
    filename: str
    mime: str
    size: int
    sha256: str
    source: str
    doc_kind: str
    doc_type: Optional[str] = None
    doc_type_confidence: Optional[float] = None
    classification_status: str
    extraction_method: Optional[str] = None
    legibility_score: Optional[float] = None
    meta: Optional[Dict[str, Any]] = None
    is_superseded: bool
    claim_ref: Optional[str] = None
    created_at: Optional[datetime] = None


class DocumentUploadResponse(SchemaBase):
    document: DocumentOut
    duplicate: bool = False
    message: str = "Document uploaded successfully"


class SignedUrlResponse(SchemaBase):
    url: str
    expires_at: Optional[datetime] = None


# Query Points & Decisions Schemas
class PointDecisionOut(SchemaBase):
    id: str
    query_point_id: str
    decision: str
    covering_document_ids: Optional[List[str]] = []
    needed_doc_types: Optional[List[str]] = []
    reason_patient: Optional[str] = None
    reason_internal: Optional[str] = None
    confidence: float
    guardrail_flags: Optional[List[str]] = []
    created_at: datetime


class QueryPointOut(SchemaBase):
    id: str
    query_letter_id: str
    ordinal: int
    verbatim_text: str
    normalized_ask: str
    point_type: str
    requested_doc_types: Optional[List[str]] = []
    period_constraint: Optional[str] = None
    confidence: float
    decision: Optional[PointDecisionOut] = None


class QueryLetterOut(SchemaBase):
    id: str
    patient_id: str
    document_id: str
    claim_ref: Optional[str] = None
    insurer_name: Optional[str] = None
    received_at: datetime
    status: str
    status_detail: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_ms: Optional[int] = None
    run_no: int
    points_count: Optional[int] = 0
    covered_points_count: Optional[int] = 0
    needed_points_count: Optional[int] = 0


class QueryLetterDetailOut(QueryLetterOut):
    points: List[QueryPointOut] = []
    pipeline_trace: Optional[Dict[str, Any]] = None


# Outbound Message Schemas
class OutboundMessageOut(SchemaBase):
    id: str
    query_letter_id: str
    patient_id: str
    channel: str
    recipient_masked: str
    template_version: int
    body_rendered: str
    status: str
    status_detail: Optional[str] = None
    provider: Optional[str] = None
    provider_message_id: Optional[str] = None
    attempts: int
    queued_at: datetime
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    idempotency_key: Optional[str] = None


# Admin & Audit Schemas
class JobOut(SchemaBase):
    id: str
    type: str
    payload: Dict[str, Any]
    status: str
    attempts: int
    max_attempts: int
    priority: int
    run_after: datetime
    last_error: Optional[str] = None
    created_at: datetime


class AuditLogOut(SchemaBase):
    id: str
    ts: datetime
    actor_user_id: Optional[str] = None
    actor_role: Optional[str] = None
    action: str
    patient_id: Optional[str] = None
    object_type: Optional[str] = None
    object_id: Optional[str] = None
    ip: Optional[str] = None
    result: str


class AdminStatsOut(BaseModel):
    total_patients: int
    total_documents: int
    total_letters: int
    letters_completed: int
    letters_in_progress: int
    letters_needs_review: int
    p50_total_ms: Optional[float] = None
    p95_total_ms: Optional[float] = None
    messages_sent: int
    messages_failed: int
    active_jobs: int
    failed_jobs: int


class PreflightStatusOut(BaseModel):
    overall_status: bool
    components: Dict[str, Dict[str, Any]]
