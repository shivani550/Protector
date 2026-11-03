import re
import hashlib
from typing import Dict, Any, List, Tuple
from pathlib import Path
import yaml
import textstat

from backend.app.config import settings
from backend.app.ingest.classify import get_taxonomy
from backend.app.security import mask_claim_ref, create_magic_upload_token

TEMPLATE_PATH = Path("backend/templates/message_template.yaml")
ALLOWED_PLACEHOLDERS = {
    "patient_first_name",
    "sender_name",
    "claim_ref_masked",
    "insurer_name",
    "needed_list",
    "covered_line",
    "portal_link",
    "helpline",
    "doc_label",
    "reason",
    "n",
    "covered_labels"
}


def load_message_template() -> Dict[str, Any]:
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"Template not found at {TEMPLATE_PATH}")
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data


def get_taxonomy_labels() -> Dict[str, str]:
    tax = get_taxonomy()
    labels = {}
    for dt in tax.get("doc_types", []):
        labels[dt["key"]] = dt["label"]
    return labels


def sanitize_patient_reason(reason: str) -> str:
    """Strips jargon and keeps text plain and under 140 chars."""
    if not reason:
        return "Required for claim assessment."
    # Strip medical jargon
    clean = re.sub(r"(?i)\b(tpa|pre-auth|icd|cpt|drg|copay|deductible)\b", "insurance verification", reason)
    clean = re.sub(r"(?i)\byou failed to\b", "please provide", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean[:140]


def compose_messages(
    patient: Dict[str, Any],
    query_letter: Dict[str, Any],
    decisions: List[Dict[str, Any]]
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Renders WhatsApp and Email messages deterministically from message_template.yaml.
    Returns: (whatsapp_payload, email_payload)
    """
    tmpl = load_message_template()
    tax_labels = get_taxonomy_labels()

    full_name = patient.get("full_name", "Policyholder")
    first_name = full_name.split()[0]
    claim_ref = mask_claim_ref(query_letter.get("claim_ref", "CLAIM"))
    insurer = query_letter.get("insurer_name", patient.get("insurer_name", "your insurer"))

    # Generate patient upload magic link
    magic_token = create_magic_upload_token(
        patient_id=patient["id"],
        query_letter_id=query_letter["id"],
        ttl_hours=settings.LINK_TTL_HOURS
    )
    portal_link = f"{settings.PUBLIC_BASE_URL}/upload/{magic_token}"

    # Group needed and covered items
    needed_types = []
    needed_reasons = {}
    covered_types = []

    for d in decisions:
        dec_type = d.get("decision")
        if dec_type == "needs_new_document":
            for n in d.get("needed_doc_types", []):
                if n not in needed_types:
                    needed_types.append(n)
                    reason = d.get("reason_patient") or "Required by insurer for claim review."
                    needed_reasons[n] = sanitize_patient_reason(reason)
        elif dec_type == "covered":
            for c in d.get("needed_doc_types", []):
                if c not in covered_types:
                    covered_types.append(c)
        elif dec_type == "needs_patient_clarification":
            n_key = "patient_clarification"
            if n_key not in needed_types:
                needed_types.append(n_key)
                needed_reasons[n_key] = sanitize_patient_reason(d.get("reason_patient") or "Please provide a brief explanation.")

    is_all_clear = (len(needed_types) == 0)

    # Format needed_list
    needed_lines = []
    item_tmpl = tmpl.get("needed_item", "{n}. {doc_label} - {reason}")
    for idx, nt in enumerate(needed_types, start=1):
        label = tax_labels.get(nt, "Clarification Note" if nt == "patient_clarification" else nt.replace("_", " ").title())
        reason = needed_reasons.get(nt, "Required for verification.")
        line = item_tmpl.format(n=idx, doc_label=label, reason=reason)
        needed_lines.append(line)

    needed_list_str = "\n".join(needed_lines) if needed_lines else "None."

    # Format covered_line
    covered_labels = [tax_labels.get(ct, ct.replace("_", " ").title()) for ct in covered_types]
    covered_labels_str = ", ".join(covered_labels) if covered_labels else ""
    covered_line_tmpl = tmpl.get("covered_line", "Already with us: {covered_labels}.")
    covered_line_str = covered_line_tmpl.format(covered_labels=covered_labels_str) if covered_labels else ""

    context = {
        "patient_first_name": first_name,
        "sender_name": settings.SENDER_NAME,
        "claim_ref_masked": claim_ref,
        "insurer_name": insurer,
        "needed_list": needed_list_str,
        "covered_line": covered_line_str,
        "portal_link": portal_link,
        "helpline": settings.HELPLINE,
    }

    # 1. Compose WhatsApp
    if is_all_clear:
        wa_text = tmpl.get("whatsapp_all_clear", "").format(**context).strip()
    else:
        wa_text = tmpl.get("whatsapp", "").format(**context).strip()

    # Enforce WhatsApp length limit of 900 chars
    if len(wa_text) > 900:
        # Keep top 4 items + portal link
        if len(needed_lines) > 4:
            truncated_lines = needed_lines[:4] + [f"...and {len(needed_lines) - 4} more items."]
            context["needed_list"] = "\n".join(truncated_lines)
            wa_text = tmpl.get("whatsapp", "").format(**context).strip()
            if len(wa_text) > 900:
                wa_text = wa_text[:880] + "...\nCheck your portal for details."

    # 2. Compose Email
    if is_all_clear:
        email_subj = tmpl.get("email_subject_all_clear", "Update on your claim {claim_ref_masked}: nothing needed").format(**context)[:70]
    else:
        email_subj = tmpl.get("email_subject", "Action needed: documents for your claim {claim_ref_masked}").format(**context)[:70]

    email_text = tmpl.get("email_text", "").format(**context).strip()
    email_html = tmpl.get("email_html", "").format(**context).strip()

    # Compute idempotency hashes
    wa_hash = hashlib.sha256(wa_text.encode("utf-8")).hexdigest()
    em_hash = hashlib.sha256(email_text.encode("utf-8")).hexdigest()

    tmpl_version = tmpl.get("version", 1)
    wa_idempotency = hashlib.sha256(f"{query_letter['id']}|whatsapp|{tmpl_version}|{wa_hash}".encode("utf-8")).hexdigest()
    em_idempotency = hashlib.sha256(f"{query_letter['id']}|email|{tmpl_version}|{em_hash}".encode("utf-8")).hexdigest()

    whatsapp_payload = {
        "channel": "whatsapp",
        "recipient": patient.get("phone_e164"),
        "body": wa_text,
        "template_version": tmpl_version,
        "content_hash": wa_hash,
        "idempotency_key": wa_idempotency
    }

    email_payload = {
        "channel": "email",
        "recipient": patient.get("email"),
        "subject": email_subj,
        "body_text": email_text,
        "body_html": email_html,
        "template_version": tmpl_version,
        "content_hash": em_hash,
        "idempotency_key": em_idempotency
    }

    return whatsapp_payload, email_payload
