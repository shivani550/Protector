export interface User {
  id: string;
  email: string;
  role: 'admin' | 'case_worker' | 'patient';
  patient_id?: string;
  is_active: boolean;
  created_at: string;
}

export interface Patient {
  id: string;
  patient_code: string;
  full_name: string;
  dob?: string;
  gender?: string;
  phone_e164: string;
  email: string;
  preferred_language: string;
  insurer_name: string;
  policy_number_masked: string;
  aadhaar_masked?: string;
  consent_whatsapp: boolean;
  consent_email: boolean;
  documents_count?: number;
  open_queries_count?: number;
  latest_query_status?: string;
  created_at: string;
  policy_number_full?: string;
  aadhaar_full?: string;
}

export interface Document {
  id: string;
  patient_id: string;
  filename: string;
  mime: string;
  size: number;
  sha256: string;
  source: string;
  doc_kind: string;
  doc_type?: string;
  doc_type_confidence?: number;
  classification_status: 'pending' | 'done' | 'failed';
  extraction_method?: string;
  legibility_score?: number;
  meta?: {
    issue_date?: string;
    expiry_date?: string;
    period_from?: string;
    period_to?: string;
    issuer?: string;
    patient_name_on_doc?: string;
    name_matches_patient?: boolean;
    amount?: number;
    claim_no_masked?: string;
    summary_redacted?: string;
  };
  is_superseded: boolean;
  claim_ref?: string;
  created_at: string;
}

export interface PointDecision {
  id: string;
  query_point_id: string;
  decision: 'covered' | 'needs_new_document' | 'needs_patient_clarification' | 'no_patient_action';
  covering_document_ids?: string[];
  needed_doc_types?: string[];
  reason_patient?: string;
  reason_internal?: string;
  confidence: number;
  guardrail_flags?: string[];
  created_at: string;
}

export interface QueryPoint {
  id: string;
  query_letter_id: string;
  ordinal: number;
  verbatim_text: string;
  normalized_ask: string;
  point_type: string;
  requested_doc_types?: string[];
  period_constraint?: string;
  confidence: number;
  decision?: PointDecision;
}

export interface QueryLetter {
  id: string;
  patient_id: string;
  document_id: string;
  claim_ref?: string;
  insurer_name?: string;
  received_at: string;
  status: 'received' | 'extracting' | 'matching' | 'composing' | 'sending' | 'completed' | 'failed' | 'needs_review';
  status_detail?: string;
  started_at?: string;
  completed_at?: string;
  total_ms?: number;
  run_no: number;
  points_count?: number;
  covered_points_count?: number;
  needed_points_count?: number;
  points?: QueryPoint[];
  pipeline_trace?: Record<string, number>;
}

export interface OutboundMessage {
  id: string;
  query_letter_id: string;
  patient_id: string;
  channel: 'whatsapp' | 'email';
  recipient_masked: string;
  template_version: number;
  body_rendered: string;
  status: 'queued' | 'sending' | 'sent' | 'delivered' | 'read' | 'failed' | 'skipped';
  status_detail?: string;
  provider?: string;
  provider_message_id?: string;
  attempts: number;
  queued_at: string;
  sent_at?: string;
  delivered_at?: string;
  failed_at?: string;
  idempotency_key?: string;
}

export interface AdminStats {
  total_patients: number;
  total_documents: number;
  total_letters: number;
  letters_completed: number;
  letters_in_progress: number;
  letters_needs_review: number;
  p50_total_ms?: number;
  p95_total_ms?: number;
  messages_sent: number;
  messages_failed: number;
  active_jobs: number;
  failed_jobs: number;
}

export interface PreflightStatus {
  overall_status: boolean;
  components: Record<string, { status: boolean; detail: string }>;
}

export interface Job {
  id: string;
  type: string;
  payload: Record<string, any>;
  status: string;
  attempts: number;
  max_attempts: number;
  priority: number;
  run_after: string;
  last_error?: string;
  created_at: string;
}

export interface AuditLog {
  id: string;
  ts: string;
  actor_user_id?: string;
  actor_role?: string;
  action: string;
  patient_id?: string;
  object_type?: string;
  object_id?: string;
  ip?: string;
  result: string;
}
