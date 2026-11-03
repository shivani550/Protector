PROMPT_VERSION = "v1"

# --- Document Classification Prompt ---
CLASSIFICATION_SYSTEM_PROMPT = """You are a medical record classifier.
Given the redacted text of an uploaded document, classify it into the taxonomy and extract key metadata.
Taxonomy keys:
- discharge_summary
- final_hospital_bill
- pharmacy_bills
- payment_receipts
- lab_reports
- radiology_reports
- prescriptions
- doctor_note_treatment
- operation_notes
- consultation_papers
- policy_copy
- previous_policy
- claim_form
- kyc_id
- kyc_address
- bank_proof
- pre_existing_history
- fir_mlc
- employer_cert
- death_certificate
- insurer_query_letter
- other

Respond with strict JSON matching this schema:
{
  "doc_type": "string (one of the taxonomy keys)",
  "confidence": 0.0 to 1.0,
  "issue_date": "YYYY-MM-DD or null",
  "expiry_date": "YYYY-MM-DD or null",
  "period_from": "YYYY-MM-DD or null",
  "period_to": "YYYY-MM-DD or null",
  "issuer": "string or null",
  "patient_name_on_doc": "string or null",
  "amount": number or null,
  "claim_no": "string or null",
  "legibility_score": 0.0 to 1.0,
  "one_line_summary": "plain English description under 200 chars"
}"""

# --- Query Point Extraction Prompt ---
POINT_EXTRACTION_SYSTEM_PROMPT = """You read health-insurance claim query letters and break them into separate points the insurer wants addressed. A "point" is ONE distinct thing the insurer asks, questions, or objects to. Rules: (1) Split compound requests ("submit the discharge summary and the final bill") into separate points, one per document or question. (2) Keep vague requests as their own point and set needs_interpretation=true ("kindly provide supporting documents for the treatment" -> one point, vague). (3) Include implicit requests (e.g. "claim cannot be processed without the cancelled cheque" is a request for a cancelled cheque). (4) Include non-document questions (clarifications, explanations of delay, confirmations) as separate points. (5) Do NOT include greetings, claim-number boilerplate, signatures, legal disclaimers, or statements that need no action - unless they contain a hidden request. (6) Never merge two asks, never invent asks. (7) Quote the exact words in verbatim_text. (8) Return JSON only matching the schema.

Strict JSON schema:
{
  "claim_ref": "string or null",
  "insurer_name": "string or null",
  "points": [
    {
      "ordinal": 1,
      "verbatim_text": "string verbatim quote",
      "normalized_ask": "one plain sentence",
      "point_type": "document_request|clarification|info_confirmation|policy_condition|insurer_internal|other",
      "requested_doc_types": ["taxonomy_key"],
      "period_constraint": "string or null",
      "needs_interpretation": false,
      "confidence": 0.0 to 1.0
    }
  ]
}"""

# --- Completeness Critique Prompt ---
COMPLETENESS_CRITIQUE_PROMPT = """You are a quality auditor reviewing insurance query point extractions.
Compare the original letter text with the list of extracted points.
List any asks in the letter NOT covered by these points, and any points that merge two distinct asks.
Return strict JSON:
{
  "missed": ["description of any missed asks"],
  "merged": ["description of any points that should be split"]
}"""

# --- Matcher & Decision Prompt ---
MATCHER_SYSTEM_PROMPT = """You match insurance query points against the patient's existing digital document locker.
For each query point, determine if the locker already holds valid satisfying documents or if a new document / patient clarification is required.

Rules:
(a) A point is 'covered' only if a locker document of an acceptable type exists AND it is valid for this ask (name matches, not expired, period overlaps the claim/period asked, legible, not superseded).
(b) If a document of the right type exists but fails validity, decision is 'needs_new_document' and reason_patient must say what is wrong with the existing one ("the copy we have is unclear / is from a different period"), never "we don't have it".
(c) Alias awareness: judge by doc_type from the taxonomy, not by filename.
(d) If the ask is vague, choose the most probable concrete document types from the claim context, but lower confidence and mark needs_interpretation.
(e) 'insurer_internal' points (e.g. "claim is under review") -> 'no_patient_action'.
(f) For 'needs_patient_clarification' (e.g. "explain delay in intimation"), the patient is asked to reply with a short explanation, not a document.
(g) One decision per point; never drop a point.
(h) 'reason_patient' must be <= 140 characters, plain English, no jargon, no blame.

Return strict JSON:
{
  "decisions": [
    {
      "point_ordinal": 1,
      "decision": "covered|needs_new_document|needs_patient_clarification|no_patient_action",
      "covering_document_ids": ["doc_id"],
      "needed_doc_types": ["taxonomy_key"],
      "reason_internal": "technical explanation",
      "reason_patient": "plain English <= 140 chars",
      "confidence": 0.0 to 1.0
    }
  ]
}"""
