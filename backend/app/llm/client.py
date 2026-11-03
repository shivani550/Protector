import json
import re
from typing import Optional, Dict, Any, Protocol
import httpx
from backend.app.config import settings


class LLMClient(Protocol):
    async def generate_json(
        self,
        prompt: str,
        system_prompt: str,
        model_type: str = "fast",
        expected_schema: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        ...


class MockLLMClient:
    """Deterministic, robust mock LLM client for offline development, CI, and degraded mode."""

    async def generate_json(
        self,
        prompt: str,
        system_prompt: str,
        model_type: str = "fast",
        expected_schema: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        lower_prompt = prompt.lower()
        lower_system = system_prompt.lower()

        # 1. Document Classification
        if "medical record classifier" in lower_system or "classify" in lower_system:
            doc_type = "other"
            if any(k in lower_prompt for k in ["discharge summary", "discharge card", "discharge certificate", "ds"]):
                doc_type = "discharge_summary"
            elif any(k in lower_prompt for k in ["final bill", "hospital bill", "itemized bill", "invoice"]):
                doc_type = "final_hospital_bill"
            elif any(k in lower_prompt for k in ["pharmacy", "chemist", "medicine bill"]):
                doc_type = "pharmacy_bills"
            elif any(k in lower_prompt for k in ["payment receipt", "settlement receipt", "receipt"]):
                doc_type = "payment_receipts"
            elif any(k in lower_prompt for k in ["pathology", "blood test", "diagnostic", "lab report"]):
                doc_type = "lab_reports"
            elif any(k in lower_prompt for k in ["cheque", "passbook", "bank proof", "neft"]):
                doc_type = "bank_proof"
            elif any(k in lower_prompt for k in ["policy schedule", "policy certificate", "insurance card", "health card", "policy copy"]):
                doc_type = "policy_copy"
            elif any(k in lower_prompt for k in ["doctor", "physician certificate", "medical certificate", "necessity", "justification"]):
                doc_type = "doctor_note_treatment"
            elif any(k in lower_prompt for k in ["case papers", "admission note", "icp"]):
                doc_type = "consultation_papers"
            elif any(k in lower_prompt for k in ["fir", "mlc", "police report"]):
                doc_type = "fir_mlc"
            elif any(k in lower_prompt for k in ["deficiency", "query letter", "additional information request"]):
                doc_type = "insurer_query_letter"

            return {
                "doc_type": doc_type,
                "confidence": 0.95 if doc_type != "other" else 0.50,
                "issue_date": "2024-01-15",
                "expiry_date": None,
                "period_from": "2024-01-10",
                "period_to": "2024-01-15",
                "issuer": "City Care Hospital",
                "patient_name_on_doc": "Patient",
                "amount": 32700,
                "claim_no": "CLM-88190",
                "legibility_score": 0.95,
                "one_line_summary": f"Document classified as {doc_type}"
            }

        # 2. Query Point Extraction
        if "break them into separate points" in lower_system or "query points" in lower_system:
            # Extract only the actual letter text (strip out injected metadata)
            letter_text = prompt
            if "Letter Text:" in prompt:
                part = prompt.split("Letter Text:")[1]
                if "Structural Candidate Spans:" in part:
                    letter_text = part.split("Structural Candidate Spans:")[0]
                else:
                    letter_text = part

            points = []
            ordinal = 1

            # Find candidates line by line
            raw_lines = [l.strip() for l in letter_text.splitlines() if l.strip()]
            ask_lines = []

            numbered_lines = []
            other_lines = []

            for line in raw_lines:
                lower_l = line.lower()
                if any(b in lower_l for b in [
                    "without prejudice", "clause", "regulations", "yours faithfully",
                    "dear policyholder", "claims assessment dept", "subject:", "insurer:",
                    "date of notice:", "insured patient:", "please submit these requirements within 15 days",
                    "we acknowledge receipt", "medical team has reviewed"
                ]):
                    continue

                num_m = re.match(r"^\s*(?:\d+[.)]|[a-z][.)]|[-•*])\s*(.+)", line)
                if num_m:
                    numbered_lines.append(num_m.group(1).strip())
                elif any(v in lower_l for v in ["submit", "provide", "furnish", "explain", "attach", "kripya", "papers", "cheque"]):
                    if not lower_l.endswith(":") and not any(p in lower_l for p in ["following requirements", "following documents", "following points", "above mentioned"]):
                        if len(line) > 15:
                            other_lines.append(line)

            ask_lines = numbered_lines if numbered_lines else other_lines

            for raw_ask in ask_lines:
                lower_ask = raw_ask.lower()
                
                # Check for compound document requests ("discharge card along with complete payment receipts and cancelled cheque")
                doc_tags = []
                if "discharge" in lower_ask:
                    doc_tags.append("discharge_summary")
                if "final" in lower_ask or "hospital bill" in lower_ask or "itemized bill" in lower_ask:
                    doc_tags.append("final_hospital_bill")
                if "lab" in lower_ask or "pathology" in lower_ask:
                    doc_tags.append("lab_reports")
                if "prescript" in lower_ask:
                    doc_tags.append("prescriptions")
                elif "doctor" in lower_ask or "physician" in lower_ask or "necessity" in lower_ask or "treatment note" in lower_ask:
                    doc_tags.append("doctor_note_treatment")
                if "pharmacy" in lower_ask or "chemist" in lower_ask:
                    doc_tags.append("pharmacy_bills")
                elif "receipt" in lower_ask:
                    doc_tags.append("payment_receipts")
                if "cheque" in lower_ask or "bank" in lower_ask:
                    doc_tags.append("bank_proof")
                if "case papers" in lower_ask or "admission note" in lower_ask:
                    doc_tags.append("consultation_papers")
                if "operation" in lower_ask or "implant" in lower_ask:
                    doc_tags.append("operation_notes")
                if "fir" in lower_ask or "mlc" in lower_ask:
                    doc_tags.append("fir_mlc")
                if "claim form" in lower_ask:
                    doc_tags.append("claim_form")
                if "previous" in lower_ask and "policy" in lower_ask:
                    doc_tags.append("previous_policy")

                is_clarification = ("delay" in lower_ask or "explain" in lower_ask)

                pt_type = "clarification" if is_clarification else "document_request"

                # If single doc or clarification or compound
                points.append({
                    "ordinal": ordinal,
                    "verbatim_text": raw_ask,
                    "normalized_ask": raw_ask.split(".")[0],
                    "point_type": pt_type,
                    "requested_doc_types": doc_tags,
                    "period_constraint": None,
                    "needs_interpretation": "medical necessity" in lower_ask,
                    "confidence": 0.95
                })
                ordinal += 1

            return {
                "claim_ref": "CLM-REF-100",
                "insurer_name": "Insurer",
                "points": points
            }

        # 3. Completeness Critique
        if "completeness" in lower_system or "missed" in lower_prompt:
            return {"missed": [], "merged": []}

        # 4. Matcher & Decision
        if "match" in lower_system or "point_ordinal" in lower_system:
            decisions = []
            pts = []
            try:
                if "Query Points:\n" in prompt and "Patient Locker Documents Snapshot:" in prompt:
                    points_part = prompt.split("Query Points:\n")[1].split("\n\nPatient Locker Documents Snapshot:")[0].strip()
                    pts = json.loads(points_part)
                else:
                    pts = []
            except Exception:
                pts = []

            for p in pts:
                reqs = p.get("requested_doc_types", [])
                p_type = p.get("point_type", "document_request")
                ord_val = p.get("ordinal", 1)

                if p_type == "clarification":
                    decisions.append({
                        "point_ordinal": ord_val,
                        "decision": "needs_patient_clarification",
                        "covering_document_ids": [],
                        "needed_doc_types": [],
                        "reason_internal": "Insurer requires clarification on delay",
                        "reason_patient": "Please reply with a brief note explaining the delay.",
                        "confidence": 0.95
                    })
                elif not reqs:
                    decisions.append({
                        "point_ordinal": ord_val,
                        "decision": "no_patient_action",
                        "covering_document_ids": [],
                        "needed_doc_types": [],
                        "reason_internal": "No document requested",
                        "reason_patient": "No action needed from you for this point.",
                        "confidence": 0.95
                    })
                else:
                    decisions.append({
                        "point_ordinal": ord_val,
                        "decision": "needs_new_document",
                        "covering_document_ids": [],
                        "needed_doc_types": reqs,
                        "reason_internal": f"Insurer requested {reqs}",
                        "reason_patient": f"Insurer needs this document to verify claim.",
                        "confidence": 0.90
                    })

            return {"decisions": decisions}

        return {}


class AnthropicLLMClient:
    def __init__(self):
        self.api_key = settings.ANTHROPIC_API_KEY
        self.fast_model = settings.LLM_MODEL_FAST
        self.reasoning_model = settings.LLM_MODEL_REASONING

    async def generate_json(
        self,
        prompt: str,
        system_prompt: str,
        model_type: str = "fast",
        expected_schema: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        if not self.api_key:
            return await MockLLMClient().generate_json(prompt, system_prompt, model_type, expected_schema)

        model = self.reasoning_model if model_type == "reasoning" else self.fast_model
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        body = {
            "model": model,
            "max_tokens": 2048,
            "temperature": 0.0,
            "system": system_prompt + "\nYou must output VALID JSON ONLY. Do not wrap in markdown tags or backticks.",
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        async with httpx.AsyncClient(timeout=40.0) as client:
            resp = await client.post("https://api.anthropic.com/v1/messages", headers=headers, json=body)
            resp.raise_for_status()
            data = resp.json()
            raw_text = data["content"][0]["text"].strip()
            if raw_text.startswith("```"):
                raw_text = re.sub(r"^```(?:json)?\n?", "", raw_text)
                raw_text = re.sub(r"\n?```$", "", raw_text)
            return json.loads(raw_text)


def get_llm_client() -> LLMClient:
    if settings.LLM_PROVIDER == "anthropic" and settings.ANTHROPIC_API_KEY:
        return AnthropicLLMClient()
    return MockLLMClient()
