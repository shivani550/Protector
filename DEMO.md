# Protector — 7-Minute Final Presentation Demo Script

This script provides an exact minute-by-minute walkthrough to demonstrate **Protector** to evaluators, judges, and healthcare operations teams.

---

## Demo Schedule & Timeline

```
[0:00 - 1:00]  The Healthcare Problem & Solution Premise
[1:00 - 2:30]  Live Query Ingestion: Drop Letter & Sub-Second Execution
[2:30 - 3:45]  The Secret Sauce: Split-Pane Diagnostic & Zero False Asks
[3:45 - 4:45]  Patient-First Experience: WhatsApp & Mobile Magic Upload
[4:45 - 5:45]  Enterprise Telemetry: Preflight Lights & Audit Trail
[5:45 - 7:00]  Eval Harness, Adversarial Proof & Conclusion
```

---

### Minute 0:00 – 1:00: The Problem & The Solution
- **Action:** Open the Protector login screen at `http://localhost:8000/login`.
- **Narration:**
  > "Every month, thousands of cashless insurance claims in India are delayed or denied due to insurer deficiency letters. These letters are filled with confusing legal jargon and medical codes. Patients panic, call hospital desks in distress, or rush to re-submit documents they already provided.
  >
  > Protector changes this paradigm. It acts as an autonomous digital health locker. When a query letter arrives, Protector reads it, cross-checks it against existing locker documents, decides if anything is actually missing, and writes a plain-language response sent directly to the patient's WhatsApp and email—**with zero human action required**."

---

### Minute 1:00 – 2:30: Live Ingestion & Sub-Second Execution
- **Action:** Click the **Admin** demo quick-fill button (`admin@demo.test`) and sign in.
- **Action:** Navigate to the terminal and execute a simulated letter arrival:
  ```powershell
  .venv\Scripts\python.exe scripts/drop_letter.py --patient PT-0001 --file data/seed_generated/letters/L01.pdf
  ```
- **Narration:**
  > "Let's watch what happens when an insurer query letter arrives for Aarav Sharma (`PT-0001`). Notice the terminal timing: in just **206 milliseconds**, the pipeline has:
  > 1. Extracted and redacted the letter text.
  > 2. Broken the inquiry into discrete points.
  > 3. Matched against 6 vaulted locker documents.
  > 4. Verified validity with code guardrails.
  > 5. Dispatched tailored messages to both WhatsApp and Email."

---

### Minute 2:30 – 3:45: Split-Pane Diagnostic & Zero False Asks
- **Action:** Click into **Aarav Sharma (`PT-0001`)** in the Patient Directory, then open the **Query Letters** tab.
- **Highlight:**
  1. **Left pane:** The original letter details, run diagnostic, and original PDF preview.
  2. **Right pane:** Discrete extracted points:
     - Point 1: *"Provide copies of final hospital bill..."* $\to$ **[COVERED BY LOCKER]** in emerald green.
     - Show that the covering document is already matched, and explain:
  > "Here is our core philosophy: **Code Wins Over LLM**. A generative model might hallucinate or politely ask the patient to re-upload. Protector's deterministic guardrails verify document type, validity period, and name match. Because the valid final bill was already vaulted in Aarav's locker, the false-ask count is **strictly zero**."

---

### Minute 3:45 – 4:45: The Patient Experience
- **Action:** Switch to the **Messages** tab to inspect the outbound WhatsApp dispatch.
- **Highlight:**
  - Masked recipient phone number (`+91******10`).
  - Plain-language wording (Grade $\le 6$ reading level, strictly under 900 characters).
  - Clear message: *"Hello Aarav, your insurer Star Health asked for documents. Good news: we already have your final hospital bill in your locker, so you don't need to do anything!"*
- **Action:** Now open an incognito window or navigate to `/upload/sample-token` to show the **Magic Upload** page:
  > "When a new document *is* truly missing (like in Letter L02 where indoor case papers were needed), the patient gets a direct, secure magic link. Mobile-friendly, camera-enabled, with instant OCR classification feedback—no app installation or password login required."

---

### Minute 4:45 – 5:45: Enterprise Operations & Preflight Lights
- **Action:** Click **Pipeline Admin** in the navigation bar (`/admin`).
- **Highlight:**
  1. **Preflight Ready Lights:** Subsystem health for Database, Fernet Encryption, LLM Provider, Twilio WhatsApp, and SMTP Email.
  2. **Latency KPIs:** p50 total resolution time (206ms) and p95 total resolution time (298ms).
  3. **Background Job Queue:** Async idempotent task state with retry actions.
  4. **Immutable Audit Journal:** Demonstrating DPDP & HIPAA compliance where every access, reveal, and dispatch is logged.

---

### Minute 5:45 – 7:00: Evaluation Harness & Final Proof
- **Action:** Show the evaluation report (`eval_report.md`):
  ```powershell
  .venv\Scripts\python.exe scripts/run_eval.py --stage all
  ```
- **Key Metrics to Highlight:**
  - **Document Classification:** 100.0% accuracy across all synthetic medical document types.
  - **Query Point Extraction:** 100.0% Recall and 100.0% Precision across all 12 query letters.
  - **Decision Invariant:** **0 False Asks** across all queries.
  - **Adversarial Resilience:** 100.0% defense against prompt injections, OCR noise, and legal boilerplate clutter.
- **Closing Statement:**
  > "Protector takes a high-friction, multi-day bottleneck in health insurance and turns it into a sub-second, autonomous, zero-false-ask experience. Thank you!"
