import re
import json
from typing import List, Dict, Any, Optional, Tuple
from rapidfuzz import fuzz

from backend.app.ingest.redact import redact_text_for_llm
from backend.app.llm.client import get_llm_client
from backend.app.llm.prompts import (
    POINT_EXTRACTION_SYSTEM_PROMPT,
    COMPLETENESS_CRITIQUE_PROMPT,
    PROMPT_VERSION
)


def detect_structural_hints(letter_text: str) -> List[str]:
    """
    Deterministic structural hint pass: finds numbered lists, bullet points,
    and sentences with mandatory insurance request verbs.
    """
    hints = []
    lines = letter_text.splitlines()

    # 1. Numbered or bulleted lines
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if re.match(r"^\s*(?:\d+[.)]|[a-z][.)]|[-•*])\s+.+", stripped, re.IGNORECASE):
            hints.append(stripped)

    # 2. Sentences with request verbs if not already captured
    action_verbs = [
        "submit", "provide", "furnish", "clarify", "explain", "confirm",
        "require", "forward", "send", "kripya", "attach"
    ]
    sentences = re.split(r"(?<=[.!?])\s+", letter_text)
    for s in sentences:
        s_clean = s.strip()
        lower_s = s_clean.lower()
        if any(v in lower_s for v in action_verbs) and len(s_clean) > 15:
            # Avoid boilerplate / disclaimer noise
            if not any(b in lower_s for b in ["without prejudice", "clause", "regulations", "yours faithfully", "dear policyholder"]):
                if s_clean not in hints:
                    hints.append(s_clean)

    return hints


def verify_hallucination_guard(verbatim_text: str, original_letter_text: str) -> bool:
    """
    Asserts that verbatim_text is a genuine substring of original_letter_text
    (case/whitespace-insensitive, fuzzy ratio >= 85).
    """
    if not verbatim_text or not original_letter_text:
        return False

    clean_verbatim = " ".join(verbatim_text.split()).lower()
    clean_letter = " ".join(original_letter_text.split()).lower()

    # Exact substring
    if clean_verbatim in clean_letter:
        return True

    # Fuzzy partial ratio
    ratio = fuzz.partial_ratio(clean_verbatim, clean_letter)
    return ratio >= 85


async def extract_query_points(
    letter_text: str,
    patient_name: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Two-pass extraction:
    1. Structural hints + Reasoning Model
    2. Completeness Critique + Fast Model
    3. Code-level Hallucination Guard
    Returns: (validated_points, extraction_metadata)
    """
    llm = get_llm_client()

    # 1. PII Redaction
    redacted_letter = redact_text_for_llm(letter_text, patient_name=patient_name)

    # 2. Deterministic Structural Hints Pre-pass
    candidate_spans = detect_structural_hints(letter_text)

    prompt = (
        f"Letter Text:\n{redacted_letter}\n\n"
        f"Structural Candidate Spans:\n{json.dumps(candidate_spans, indent=2)}\n"
    )

    # Pass 1: Extraction
    res = await llm.generate_json(
        prompt=prompt,
        system_prompt=POINT_EXTRACTION_SYSTEM_PROMPT,
        model_type="reasoning"
    )
    points = res.get("points", [])

    # Pass 2: Completeness Critique
    critique_prompt = (
        f"Original Redacted Letter:\n{redacted_letter}\n\n"
        f"Extracted Points:\n{json.dumps(points, indent=2)}\n"
    )
    critique_res = await llm.generate_json(
        prompt=critique_prompt,
        system_prompt=COMPLETENESS_CRITIQUE_PROMPT,
        model_type="fast"
    )

    missed = critique_res.get("missed", [])
    merged = critique_res.get("merged", [])

    # If missed or merged items identified, perform one revision pass
    if missed or merged:
        revision_prompt = (
            f"{prompt}\n\n"
            f"Critique Feedback:\n"
            f"Missed items to include: {json.dumps(missed)}\n"
            f"Merged items to split: {json.dumps(merged)}\n"
            f"Please revise the points list accordingly."
        )
        revised_res = await llm.generate_json(
            prompt=revision_prompt,
            system_prompt=POINT_EXTRACTION_SYSTEM_PROMPT,
            model_type="reasoning"
        )
        revised_points = revised_res.get("points", [])
        if revised_points:
            points = revised_points

    # 3. Hallucination Guard
    valid_points = []
    dropped_count = 0

    for pt in points:
        verbatim = pt.get("verbatim_text", "")
        if verify_hallucination_guard(verbatim, letter_text):
            valid_points.append(pt)
        else:
            dropped_count += 1

    metadata = {
        "prompt_version": PROMPT_VERSION,
        "structural_hints_count": len(candidate_spans),
        "raw_points_count": len(points),
        "valid_points_count": len(valid_points),
        "dropped_hallucinations": dropped_count,
        "critique_missed_count": len(missed),
        "critique_merged_count": len(merged)
    }

    return valid_points, metadata
