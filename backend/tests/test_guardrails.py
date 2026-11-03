import pytest
from backend.app.llm.matcher import apply_guardrails, is_doc_valid_for_ask


def test_guardrail_already_present_override():
    """Asserts that a valid document in the locker flips a decision to covered (False Ask = 0)."""
    locker = [
        {
            "id": "doc-ds-1",
            "doc_type": "discharge_summary",
            "filename": "discharge_summary.pdf",
            "is_superseded": False,
            "legibility_score": 0.95,
            "meta": {"name_matches_patient": True, "expiry_date": None}
        }
    ]
    # Simulated flawed LLM decision that erroneously asks for discharge summary
    flawed_decisions = [
        {
            "point_ordinal": 1,
            "decision": "needs_new_document",
            "needed_doc_types": ["discharge_summary"],
            "covering_document_ids": [],
            "reason_patient": "Please send discharge summary.",
            "guardrail_flags": []
        }
    ]
    points = [{"ordinal": 1, "requested_doc_types": ["discharge_summary"]}]

    guarded = apply_guardrails(flawed_decisions, points, locker)
    dec = guarded[0]

    assert dec["decision"] == "covered"
    assert "doc-ds-1" in dec["covering_document_ids"]
    assert "discharge_summary" not in dec["needed_doc_types"]
    assert "override_already_present" in dec["guardrail_flags"]


def test_guardrail_satisfies_hierarchy():
    """Aadhaar (kyc_id) satisfies kyc_address proof."""
    locker = [
        {
            "id": "doc-aadhaar",
            "doc_type": "kyc_id",
            "filename": "aadhaar.pdf",
            "is_superseded": False,
            "legibility_score": 0.95,
            "meta": {"name_matches_patient": True, "expiry_date": None}
        }
    ]
    decisions = [
        {
            "point_ordinal": 1,
            "decision": "needs_new_document",
            "needed_doc_types": ["kyc_address"],
            "covering_document_ids": []
        }
    ]
    points = [{"ordinal": 1, "requested_doc_types": ["kyc_address"]}]

    guarded = apply_guardrails(decisions, points, locker)
    assert guarded[0]["decision"] == "covered"
    assert "doc-aadhaar" in guarded[0]["covering_document_ids"]


def test_guardrail_name_mismatch_invalidates():
    """Document with another person's name cannot cover a claim ask."""
    locker = [
        {
            "id": "doc-wrong-name",
            "doc_type": "final_hospital_bill",
            "filename": "bill.pdf",
            "is_superseded": False,
            "legibility_score": 0.95,
            "meta": {"name_matches_patient": False, "expiry_date": None}
        }
    ]
    decisions = [
        {
            "point_ordinal": 1,
            "decision": "needs_new_document",
            "needed_doc_types": ["final_hospital_bill"],
            "covering_document_ids": []
        }
    ]
    points = [{"ordinal": 1, "requested_doc_types": ["final_hospital_bill"]}]

    guarded = apply_guardrails(decisions, points, locker)
    dec = guarded[0]
    # Decision must REMAIN needs_new_document
    assert dec["decision"] == "needs_new_document"
    assert "final_hospital_bill" in dec["needed_doc_types"]
    assert any("name on document does not match patient" in f for f in dec["guardrail_flags"])


def test_guardrail_illegible_requires_clearer_copy():
    """Illegible document (score < 0.5) cannot satisfy an ask."""
    locker = [
        {
            "id": "doc-blurry",
            "doc_type": "lab_reports",
            "filename": "blurry_lab.pdf",
            "is_superseded": False,
            "legibility_score": 0.35,
            "meta": {"name_matches_patient": True, "expiry_date": None}
        }
    ]
    decisions = [
        {
            "point_ordinal": 1,
            "decision": "needs_new_document",
            "needed_doc_types": ["lab_reports"],
            "covering_document_ids": []
        }
    ]
    points = [{"ordinal": 1, "requested_doc_types": ["lab_reports"]}]

    guarded = apply_guardrails(decisions, points, locker)
    dec = guarded[0]
    assert dec["decision"] == "needs_new_document"
    assert "lab_reports" in dec["needed_doc_types"]
    assert any("unclear" in f or "illegible" in f for f in dec["guardrail_flags"])
    assert "clearer copy" in dec["reason_patient"].lower()


def test_guardrail_unknown_type_mapped_to_other():
    decisions = [
        {
            "point_ordinal": 1,
            "decision": "needs_new_document",
            "needed_doc_types": ["alien_unknown_form_xyz"],
            "covering_document_ids": []
        }
    ]
    points = [{"ordinal": 1, "requested_doc_types": ["alien_unknown_form_xyz"]}]
    guarded = apply_guardrails(decisions, points, [])
    assert "other" in guarded[0]["needed_doc_types"]
    assert "alien_unknown_form_xyz" not in guarded[0]["needed_doc_types"]
    assert "unknown_type_mapped_to_other" in guarded[0]["guardrail_flags"]
