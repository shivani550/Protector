import re
from typing import Tuple, List, Optional, Dict


class PIIRedactor:
    def __init__(self, patient_name: Optional[str] = None):
        self.patient_name = patient_name.strip() if patient_name else None

    def redact(self, text: str) -> Tuple[str, Dict[str, int]]:
        """
        Redacts PII from text before passing to third-party LLMs.
        Returns: (redacted_text, redaction_counts)
        """
        if not text:
            return "", {}

        counts: Dict[str, int] = {
            "aadhaar": 0,
            "pan": 0,
            "phone": 0,
            "email": 0,
            "policy_claim": 0,
            "patient_name": 0
        }

        redacted = text

        # 1. Patient Name Redaction (if provided)
        if self.patient_name and len(self.patient_name) >= 3:
            # Match whole name or individual significant parts (>= 3 chars)
            pattern = re.compile(rf"\b{re.escape(self.patient_name)}\b", re.IGNORECASE)
            matches = len(pattern.findall(redacted))
            if matches:
                counts["patient_name"] += matches
                redacted = pattern.sub("[PATIENT]", redacted)

            for token in self.patient_name.split():
                if len(token) >= 3 and token.lower() not in {"and", "the", "for", "with"}:
                    t_pattern = re.compile(rf"\b{re.escape(token)}\b", re.IGNORECASE)
                    m = len(t_pattern.findall(redacted))
                    if m:
                        counts["patient_name"] += m
                        redacted = t_pattern.sub("[PATIENT]", redacted)

        # 2. Email Address Redaction
        email_pattern = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
        matches = len(email_pattern.findall(redacted))
        if matches:
            counts["email"] += matches
            redacted = email_pattern.sub("[EMAIL]", redacted)

        # 3. Aadhaar Redaction (12 digits, optional space/hyphen after 4th and 8th digit)
        aadhaar_pattern = re.compile(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}\b")
        matches = len(aadhaar_pattern.findall(redacted))
        if matches:
            counts["aadhaar"] += matches
            redacted = aadhaar_pattern.sub("[AADHAAR]", redacted)

        # 4. PAN Redaction (5 uppercase letters, 4 digits, 1 uppercase letter)
        pan_pattern = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")
        matches = len(pan_pattern.findall(redacted))
        if matches:
            counts["pan"] += matches
            redacted = pan_pattern.sub("[PAN]", redacted)

        # 5. Phone Number Redaction (+91, 10-digit mobile numbers)
        phone_pattern = re.compile(r"(?:\+91[-.\s]?)?[6-9]\d{9}\b")
        matches = len(phone_pattern.findall(redacted))
        if matches:
            counts["phone"] += matches
            redacted = phone_pattern.sub("[PHONE]", redacted)

        # 6. Policy / Claim / Member / UHID numbers (runs of digits >= 8)
        policy_claim_pattern = re.compile(r"(?i)\b(?:policy|claim|member|uhid|reg(?:istration)?)\s*(?:no\.?|number|id|#)?\s*[:=-]?\s*([A-Za-z0-9-]{6,25})\b")
        
        def replace_claim_policy(m):
            counts["policy_claim"] += 1
            full_match = m.group(0)
            target = m.group(1)
            return full_match.replace(target, "[REF_NUMBER]")

        redacted = policy_claim_pattern.sub(replace_claim_policy, redacted)

        # 7. Any isolated digit run of 8 or more digits
        long_digit_pattern = re.compile(r"\b\d{8,16}\b")
        matches = len(long_digit_pattern.findall(redacted))
        if matches:
            counts["policy_claim"] += matches
            redacted = long_digit_pattern.sub("[ID_NUMBER]", redacted)

        return redacted, counts


def redact_text_for_llm(text: str, patient_name: Optional[str] = None) -> str:
    redactor = PIIRedactor(patient_name=patient_name)
    redacted, _ = redactor.redact(text)
    return redacted
