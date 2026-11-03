import json
from typing import List, Dict, Any, Tuple
from datetime import datetime, date

from backend.app.ingest.classify import get_taxonomy
from backend.app.llm.client import get_llm_client
from backend.app.llm.prompts import MATCHER_SYSTEM_PROMPT


def get_satisfies_map() -> Dict[str, List[str]]:
    """Returns mapping from doc_type to list of doc_types it satisfies."""
    tax = get_taxonomy()
    sat_map = {}
    for dt in tax.get("doc_types", []):
        sat_map[dt["key"]] = dt.get("satisfies", [])
    return sat_map


def is_doc_valid_for_ask(doc: Dict[str, Any], requested_type: str) -> Tuple[bool, str]:
    """
    Evaluates validity of a locker document for a specific requested type.
    Returns: (is_valid, invalid_reason)
    """
    # 1. Superseded check
    if doc.get("is_superseded"):
        return False, "document is superseded"

    # 2. Name match check (check both top-level and inside meta)
    meta = doc.get("meta") or {}
    name_matches = doc.get("name_matches_patient")
    if name_matches is None:
        name_matches = meta.get("name_matches_patient", True)
    if name_matches is False:
        return False, "name on document does not match patient"

    # 3. Legibility check
    legibility = doc.get("legibility_score", 1.0)
    if legibility is not None and legibility < 0.50:
        return False, "document is unclear or illegible"

    # 4. Expiry check
    exp_str = doc.get("expiry_date") or meta.get("expiry_date")
    if exp_str:
        try:
            exp_date = datetime.strptime(exp_str, "%Y-%m-%d").date()
            if exp_date < date.today():
                return False, "document has expired"
        except Exception:
            pass

    return True, "valid"


def apply_guardrails(
    decisions: List[Dict[str, Any]],
    points: List[Dict[str, Any]],
    locker_docs: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Deterministic Guardrails: Code wins over the LLM.
    Guarantees: False-Ask Count == 0.
    """
    tax = get_taxonomy()
    known_keys = {dt["key"] for dt in tax.get("doc_types", [])}
    satisfies_map = get_satisfies_map()

    # Build lookup of locker documents
    # Map doc_type -> list of docs
    docs_by_type: Dict[str, List[Dict[str, Any]]] = {}
    for d in locker_docs:
        dtype = d.get("doc_type")
        if dtype:
            docs_by_type.setdefault(dtype, []).append(d)

    refined_decisions = []

    for dec in decisions:
        ord_val = dec.get("point_ordinal")
        needed = list(dec.get("needed_doc_types", []))
        covering_ids = list(dec.get("covering_document_ids", []))
        current_decision = dec.get("decision", "needs_new_document")
        reason_pat = dec.get("reason_patient", "")
        reason_int = dec.get("reason_internal", "")
        flags = list(dec.get("guardrail_flags", []))
        confidence = float(dec.get("confidence", 0.90))

        # Guardrail 4: Unknown type guard
        cleaned_needed = []
        for n_type in needed:
            if n_type in known_keys:
                cleaned_needed.append(n_type)
            else:
                cleaned_needed.append("other")
                flags.append("unknown_type_mapped_to_other")
                confidence = min(confidence, 0.40)
        needed = cleaned_needed

        # Guardrail 6: Requested type sanity (e.g. insurer internal reports)
        if any(n in ["insurer_internal", "internal_review"] for n in needed):
            current_decision = "no_patient_action"
            needed = []
            reason_pat = "No action needed from you for internal insurer verification."
            flags.append("insurer_internal_no_action")

        # Guardrail 1: Already-present override (False-Ask Count MUST be 0)
        still_needed = []
        for n_type in needed:
            # Find candidate documents in locker matching n_type directly or via satisfies
            candidates = list(docs_by_type.get(n_type, []))
            for other_type, satisfies_list in satisfies_map.items():
                if n_type in satisfies_list:
                    candidates.extend(docs_by_type.get(other_type, []))

            # Evaluate each candidate document
            found_valid_covering = False
            invalid_reasons = []

            for cand in candidates:
                valid, why_invalid = is_doc_valid_for_ask(cand, n_type)
                if valid:
                    found_valid_covering = True
                    if cand["id"] not in covering_ids:
                        covering_ids.append(cand["id"])
                    break
                else:
                    invalid_reasons.append(why_invalid)

            if found_valid_covering:
                # Document already exists valid in locker! DO NOT ASK!
                flags.append("override_already_present")
            else:
                # Document is truly needed or existing copy is invalid
                still_needed.append(n_type)
                if invalid_reasons:
                    # Guardrail 3: Invalid doc handling
                    primary_why = invalid_reasons[0]
                    flags.append(f"existing_invalid:{primary_why}")
                    if "unclear" in primary_why or "illegible" in primary_why:
                        reason_pat = "The copy we have is unclear. Please provide a clearer copy."
                    elif "expired" in primary_why:
                        reason_pat = "The policy document on file has expired. Please provide the current renewed copy."
                    elif "name" in primary_why:
                        reason_pat = "The bill on file does not match your name. Please submit the itemized bill in your name."

        needed = still_needed

        # If all needs were satisfied by locker documents, flip to covered
        if not needed and current_decision == "needs_new_document":
            current_decision = "covered"
            reason_pat = "We already have this document in your locker."
            flags.append("override_flipped_to_covered")

        dec["decision"] = current_decision
        dec["needed_doc_types"] = needed
        dec["covering_document_ids"] = covering_ids
        dec["reason_patient"] = reason_pat[:140]
        dec["reason_internal"] = reason_int
        dec["guardrail_flags"] = flags
        dec["confidence"] = confidence

        refined_decisions.append(dec)

    return refined_decisions


async def match_points_with_locker(
    points: List[Dict[str, Any]],
    locker_docs: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Orchestrates matching points against locker snapshot and runs deterministic guardrails.
    """
    llm = get_llm_client()

    # Build privacy-preserving locker snapshot (metadata only, NO raw text)
    locker_snapshot = []
    for d in locker_docs:
        meta = d.get("meta") or {}
        locker_snapshot.append({
            "id": d["id"],
            "doc_type": d.get("doc_type"),
            "filename": d.get("filename"),
            "issue_date": meta.get("issue_date"),
            "expiry_date": meta.get("expiry_date"),
            "issuer": meta.get("issuer"),
            "name_matches_patient": meta.get("name_matches_patient", True),
            "legibility_score": d.get("legibility_score", 1.0),
            "is_superseded": d.get("is_superseded", False),
            "summary_redacted": meta.get("summary_redacted", "")[:200]
        })

    prompt = (
        f"Query Points:\n{json.dumps(points, indent=2)}\n\n"
        f"Patient Locker Documents Snapshot:\n{json.dumps(locker_snapshot, indent=2)}\n"
    )

    llm_res = await llm.generate_json(
        prompt=prompt,
        system_prompt=MATCHER_SYSTEM_PROMPT,
        model_type="reasoning"
    )
    raw_decisions = llm_res.get("decisions", [])
    if not raw_decisions:
        for p in points:
            ord_val = p.get("ordinal", 1)
            p_type = p.get("point_type", "document_request")
            reqs = list(p.get("requested_doc_types", []))
            if p_type == "clarification":
                raw_decisions.append({
                    "point_ordinal": ord_val,
                    "decision": "needs_patient_clarification",
                    "covering_document_ids": [],
                    "needed_doc_types": [],
                    "reason_internal": "Clarification requested",
                    "reason_patient": "Please reply with a brief explanation.",
                    "confidence": 0.90
                })
            elif not reqs:
                raw_decisions.append({
                    "point_ordinal": ord_val,
                    "decision": "no_patient_action",
                    "covering_document_ids": [],
                    "needed_doc_types": [],
                    "reason_internal": "No document requested",
                    "reason_patient": "No action needed from you for this point.",
                    "confidence": 0.90
                })
            else:
                raw_decisions.append({
                    "point_ordinal": ord_val,
                    "decision": "needs_new_document",
                    "covering_document_ids": [],
                    "needed_doc_types": reqs,
                    "reason_internal": f"Requested {reqs}",
                    "reason_patient": "Please provide the requested document to verify your claim.",
                    "confidence": 0.90
                })

    # Apply Deterministic Guardrails
    final_decisions = apply_guardrails(raw_decisions, points, locker_snapshot)
    return final_decisions
