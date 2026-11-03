import re
from pathlib import Path
from typing import Tuple, Dict, Any, Optional
import yaml
from rapidfuzz import fuzz

from backend.app.config import settings
from backend.app.ingest.redact import redact_text_for_llm
from backend.app.llm.client import get_llm_client
from backend.app.llm.prompts import CLASSIFICATION_SYSTEM_PROMPT

# Load and cache document taxonomy
TAXONOMY_PATH = Path("backend/taxonomy/doc_types.yaml")
_TAXONOMY_CACHE: Optional[Dict[str, Any]] = None


def get_taxonomy() -> Dict[str, Any]:
    global _TAXONOMY_CACHE
    if _TAXONOMY_CACHE is None:
        if TAXONOMY_PATH.exists():
            with open(TAXONOMY_PATH, "r", encoding="utf-8") as f:
                _TAXONOMY_CACHE = yaml.safe_load(f)
        else:
            _TAXONOMY_CACHE = {"doc_types": []}
    return _TAXONOMY_CACHE


def keyword_classify_prepass(text: str, filename: str = "") -> Optional[Tuple[str, float]]:
    """
    Fast, deterministic keyword classifier.
    Returns: (doc_type, confidence) if a decisive match is found, else None.
    """
    taxonomy = get_taxonomy()
    combined_text = (filename + " " + text[:6000]).lower()

    best_match = None
    best_score = 0

    for dt in taxonomy.get("doc_types", []):
        key = dt["key"]
        label = dt["label"].lower()
        aliases = [a.lower() for a in dt.get("aliases", [])]

        matches = 0
        # Exact label hit
        if label in combined_text:
            matches += 3

        # Key hit in filename
        if key in filename.lower():
            matches += 3

        # Alias hits
        for a in aliases:
            if a in combined_text:
                matches += 2

        if matches > best_score:
            best_score = matches
            best_match = key

    if best_score >= 4:
        return best_match, min(0.98, 0.85 + (best_score * 0.02))
    elif best_score >= 2:
        return best_match, 0.88

    return None


def verify_patient_name_match(doc_name: Optional[str], patient_full_name: str) -> bool:
    """
    Fuzzy comparison in CODE (Rapidfuzz token_set_ratio >= 85) to prevent hallucinations.
    """
    if not doc_name or not patient_full_name:
        return False
    clean_doc = re.sub(r"[^a-zA-Z\s]", "", doc_name).strip().lower()
    clean_pt = re.sub(r"[^a-zA-Z\s]", "", patient_full_name).strip().lower()
    ratio = fuzz.token_set_ratio(clean_doc, clean_pt)
    return ratio >= 85


async def classify_document_text(
    text: str,
    patient_full_name: str,
    filename: str = ""
) -> Tuple[str, float, Dict[str, Any]]:
    """
    Classifies a document's extracted text and returns (doc_type, confidence, metadata).
    """
    # 1. Fast Keyword Prepass
    kw_result = keyword_classify_prepass(text, filename=filename)
    if kw_result and kw_result[1] >= 0.85:
        doc_type, confidence = kw_result
        meta = {
            "issue_date": None,
            "expiry_date": None,
            "period_from": None,
            "period_to": None,
            "issuer": "Extracted from text",
            "patient_name_on_doc": patient_full_name,
            "name_matches_patient": True,
            "amount": None,
            "claim_no_masked": None,
            "summary_redacted": f"Classified as {doc_type} via keyword matching"
        }
        return doc_type, confidence, meta

    # 2. Redact text before LLM inference
    redacted_sample = redact_text_for_llm(text[:6000], patient_name=patient_full_name)

    # 3. LLM Fast Model Call
    llm = get_llm_client()
    prompt = f"Filename: {filename}\nDocument Text (Redacted):\n{redacted_sample}"
    try:
        res = await llm.generate_json(
            prompt=prompt,
            system_prompt=CLASSIFICATION_SYSTEM_PROMPT,
            model_type="fast"
        )
        doc_type = res.get("doc_type", "other")
        confidence = float(res.get("confidence", 0.70))
        doc_name = res.get("patient_name_on_doc")
        name_matches = verify_patient_name_match(doc_name, patient_full_name)

        meta = {
            "issue_date": res.get("issue_date"),
            "expiry_date": res.get("expiry_date"),
            "period_from": res.get("period_from"),
            "period_to": res.get("period_to"),
            "issuer": res.get("issuer"),
            "patient_name_on_doc": doc_name,
            "name_matches_patient": name_matches,
            "amount": res.get("amount"),
            "claim_no_masked": res.get("claim_no"),
            "summary_redacted": res.get("one_line_summary", f"{doc_type} record")[:300]
        }
        return doc_type, confidence, meta
    except Exception:
        # Fallback to keyword match or other
        fallback_type = kw_result[0] if kw_result else "other"
        meta = {
            "name_matches_patient": True,
            "summary_redacted": "Fallback classification"
        }
        return fallback_type, 0.50, meta
