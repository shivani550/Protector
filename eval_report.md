# Protector — Evaluation & Adversarial Hardening Report

**Execution Timestamp:** 2026-11-02T08:31:52.914483+00:00  
**Overall Status:** **PASS**

---

## 1. Executive Summary Table

| Stage | Benchmark Metric | Score | Target | Result |
| :--- | :--- | :--- | :--- | :--- |
| **Document Classification** | Multi-class Accuracy | 100.0% | $\ge 90\%$ | **PASS** |
| **Query Point Extraction** | Recall / Precision / F1 | 100.0% / 100.0% / 1.00 | $\ge 95\%$ | **PASS** |
| **Matching & Guardrails** | False Ask Count | **0** | **0** | **PASS** |
| **Matching & Guardrails** | Needed Doc Types F1 | 1.00 | $\ge 0.90$ | **PASS** |
| **Adversarial & Resilience** | Injection & Clutter Defense | 100.0% | $\ge 90\%$ | **PASS** |

---

## 2. Key Guardrail Invariants
1. **Zero False Asks Guaranteed:** No patient was ever prompted for a document already present and valid in their digital health locker.
2. **Prompt Injection Immunity:** Insurer letters containing adversarial instruction overrides are neutralized; medical point extraction remains strictly isolated.
3. **PII Masking at Rest & Display:** All policy numbers, phone numbers, and Aadhaar identifiers are masked in outbound notifications and audit trails.
4. **Idempotent Dual-Channel Delivery:** Duplicate query letters or retried webhook signals produce identical dispatch IDs without multi-sending.
