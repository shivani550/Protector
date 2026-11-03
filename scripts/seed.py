import os
import sys
import json
import random
import asyncio
from pathlib import Path
from datetime import datetime, date, timedelta, timezone

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors

from backend.app.config import settings
from backend.app.db import engine, Base, AsyncSessionLocal
from backend.app.models import User, Patient, CaseAssignment, Document, QueryLetter, MessageTemplate
from backend.app.security import hash_password, encrypt_text
from backend.app.storage import save_encrypted_file

# Fixed seed for deterministic generation
random.seed(42)

SEED_DIR = Path("data/seed_generated")
DOCS_DIR = SEED_DIR / "documents"
LETTERS_DIR = SEED_DIR / "letters"


def make_pdf(file_path: Path, title: str, lines: list[str], header_color=colors.navy):
    c = canvas.Canvas(str(file_path), pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(header_color)
    c.drawString(50, 750, title)
    
    c.setStrokeColor(colors.gray)
    c.setLineWidth(1)
    c.line(50, 740, 560, 740)

    c.setFont("Helvetica", 10)
    c.setFillColor(colors.black)
    y = 715
    for line in lines:
        if line == "---":
            c.setStrokeColor(colors.lightgrey)
            c.line(50, y, 560, y)
            y -= 15
        elif line.startswith("# "):
            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, y, line[2:])
            c.setFont("Helvetica", 10)
            y -= 18
        else:
            c.drawString(50, y, line)
            y -= 14
        if y < 60:
            c.showPage()
            c.setFont("Helvetica", 10)
            y = 750
    c.save()


async def seed_database():
    print("=== Starting Deterministic Seed Generation ===")
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    LETTERS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Clean & Initialize Tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # 2. Patients Specification
    patients_data = [
        {
            "code": "PT-0001",
            "name": "Arjun Sharma",
            "dob": "1985-04-12",
            "gender": "male",
            "phone": settings.DEMO_PHONE_E164,
            "email": settings.DEMO_EMAIL,
            "insurer": "Star Health Insurance",
            "policy": "SH-2024-884912",
            "aadhaar": "981245671234",
            "trap": "has_discharge_summary_and_bills",
        },
        {
            "code": "PT-0002",
            "name": "Kavita Nair",
            "dob": "1992-09-28",
            "gender": "female",
            "phone": "+919876543202",
            "email": "kavita.nair@demo.test",
            "insurer": "HDFC ERGO General Insurance",
            "policy": "HE-2023-410923",
            "aadhaar": "456712349812",
            "trap": "discharge_card_alias",  # titled "Discharge Card"
        },
        {
            "code": "PT-0003",
            "name": "Vikram Malhotra",
            "dob": "1978-12-05",
            "gender": "male",
            "phone": "+919876543203",
            "email": "vikram.m@demo.test",
            "insurer": "Care Health Insurance",
            "policy": "CH-2024-672109",
            "aadhaar": "781290345612",
            "trap": "bill_other_name",  # Bill has name 'Ramesh Gupta'
        },
        {
            "code": "PT-0004",
            "name": "Ananya Deshmukh",
            "dob": "1995-02-18",
            "gender": "female",
            "phone": "+919876543204",
            "email": "ananya.d@demo.test",
            "insurer": "ICICI Lombard",
            "policy": "IL-2024-118902",
            "aadhaar": "334455667788",
            "trap": "blurry_lab_report",  # Lab report legibility 0.35
        },
        {
            "code": "PT-0005",
            "name": "Deepak Verma",
            "dob": "1980-07-25",
            "gender": "male",
            "phone": "+919876543205",
            "email": "deepak.v@demo.test",
            "insurer": "Niva Bupa Health Insurance",
            "policy": "NB-2022-990142",
            "aadhaar": "889900112233",
            "trap": "expired_policy_copy",  # Policy expired in 2023
        },
        {
            "code": "PT-0006",
            "name": "Sunita Rao",
            "dob": "1974-03-30",
            "gender": "female",
            "phone": "+919876543206",
            "email": "sunita.rao@demo.test",
            "insurer": "Star Health Insurance",
            "policy": "SH-2024-773322",
            "aadhaar": "556677889900",
            "trap": "aadhaar_only_address",  # KYC Aadhaar also satisfies address
        },
        {
            "code": "PT-0007",
            "name": "Manish Kumar",
            "dob": "1989-10-15",
            "gender": "male",
            "phone": "+919876543207",
            "email": "manish.k@demo.test",
            "insurer": "HDFC ERGO General Insurance",
            "policy": "HE-2024-554433",
            "aadhaar": "112233445566",
            "trap": "duplicate_upload",  # Uploaded same bill twice
        },
        {
            "code": "PT-0008",
            "name": "Meera Iyer",
            "dob": "1998-06-20",
            "gender": "female",
            "phone": "+919876543208",
            "email": "meera.i@demo.test",
            "insurer": "Care Health Insurance",
            "policy": "CH-2024-998877",
            "aadhaar": "223344556677",
            "trap": "full_locker_all_clear",  # Has every required document
        },
        {
            "code": "PT-0009",
            "name": "Rohan Gupta",
            "dob": "1983-08-11",
            "gender": "male",
            "phone": "+919876543209",
            "email": "rohan.g@demo.test",
            "insurer": "ICICI Lombard",
            "policy": "IL-2024-445566",
            "aadhaar": "998877665544",
            "trap": "standard_locker",
        },
        {
            "code": "PT-0010",
            "name": "Pooja Hegde",
            "dob": "1993-11-04",
            "gender": "female",
            "phone": "+919876543210",
            "email": "pooja.h@demo.test",
            "insurer": "Niva Bupa Health Insurance",
            "policy": "NB-2024-332211",
            "aadhaar": "667788990011",
            "trap": "empty_locker",  # Zero documents in locker
        },
    ]

    async with AsyncSessionLocal() as session:
        # 3. Create Demo Users
        admin_pass = hash_password(settings.DEMO_PASSWORD)
        admin = User(
            id="admin-demo-uuid",
            email="admin@demo.test",
            password_hash=admin_pass,
            role="admin",
            is_active=True
        )
        worker = User(
            id="worker-demo-uuid",
            email="worker@demo.test",
            password_hash=admin_pass,
            role="case_worker",
            is_active=True
        )
        session.add(admin)
        session.add(worker)
        await session.flush()

        created_patients = {}

        for p_idx, p_data in enumerate(patients_data):
            p_id = f"pt-uuid-{p_data['code'].lower()}"
            pol = p_data["policy"]
            aadh = p_data["aadhaar"]
            
            patient = Patient(
                id=p_id,
                patient_code=p_data["code"],
                full_name=p_data["name"],
                dob=p_data["dob"],
                gender=p_data["gender"],
                phone_e164=p_data["phone"],
                email=p_data["email"],
                preferred_language="en",
                insurer_name=p_data["insurer"],
                policy_number_enc=encrypt_text(pol),
                policy_number_last4=pol[-4:],
                aadhaar_enc=encrypt_text(aadh),
                aadhaar_last4=aadh[-4:],
                consent_whatsapp=True,
                consent_email=True
            )
            session.add(patient)
            created_patients[p_data["code"]] = patient

            # Case worker gets assigned first 5 patients
            if p_idx < 5:
                assignment = CaseAssignment(
                    user_id=worker.id,
                    patient_id=p_id
                )
                session.add(assignment)

            # Patient demo user for patient 1
            if p_data["code"] == "PT-0001":
                p_user = User(
                    id="patient1-demo-uuid",
                    email="patient1@demo.test",
                    password_hash=admin_pass,
                    role="patient",
                    patient_id=p_id,
                    is_active=True
                )
                session.add(p_user)

        await session.flush()

        # 4. Generate Locker Documents
        print("Generating synthetic patient documents...")
        for p_data in patients_data:
            code = p_data["code"]
            p_obj = created_patients[code]
            trap = p_data["trap"]

            if trap == "empty_locker":
                continue

            doc_specs = [
                ("discharge_summary", "Discharge Summary" if trap != "discharge_card_alias" else "Discharge Card", "discharge_summary.pdf"),
                ("final_hospital_bill", "Final Hospital Bill", "final_bill.pdf"),
                ("payment_receipts", "Payment Receipt", "payment_receipt.pdf"),
                ("lab_reports", "Diagnostic Pathology Report", "lab_report.pdf"),
                ("bank_proof", "Cancelled Cheque", "cancelled_cheque.pdf"),
                ("policy_copy", "Health Insurance Policy Schedule", "policy_schedule.pdf"),
            ]

            # Adjustments for traps
            for doc_type, doc_title, fname in doc_specs:
                pt_name_on_doc = p_data["name"]
                legibility = 0.95
                valid_period = "2024-01-10 to 2024-01-15"

                if trap == "bill_other_name" and doc_type == "final_hospital_bill":
                    pt_name_on_doc = "Ramesh Gupta"  # Name mismatch trap

                if trap == "blurry_lab_report" and doc_type == "lab_reports":
                    legibility = 0.35  # Illegible trap

                if trap == "expired_policy_copy" and doc_type == "policy_copy":
                    valid_period = "2022-01-01 to 2023-01-01"  # Expired trap

                pdf_path = DOCS_DIR / f"{code}_{fname}"
                make_pdf(
                    file_path=pdf_path,
                    title=f"CITY CARE HOSPITAL - {doc_title.upper()}",
                    lines=[
                        f"Patient Name: {pt_name_on_doc}",
                        f"Patient ID: {code} | DOB: {p_data['dob']}",
                        f"Admission Date: 2024-01-10 | Discharge Date: 2024-01-15",
                        f"Treating Consultant: Dr. K. S. Murthy, MD (Internal Medicine)",
                        "---",
                        f"# Document: {doc_title}",
                        f"Validity Period: {valid_period}",
                        f"Diagnosis: Acute Enteritis with Moderate Dehydration",
                        f"Hospital Reg No: H-99214 | Policy: {p_data['policy']}",
                        "Breakdown of Charges: Room: Rs. 15,000 | Pharmacy: Rs. 8,200 | Diagnostics: Rs. 4,500",
                        f"Total Amount Claimed: Rs. 32,700 (INR)",
                        "Status: Settled and Verified by Hospital Accounts",
                        "---",
                        "Attending Physician Signature: Dr. K. S. Murthy (Reg #MCI-48192)"
                    ]
                )

                file_bytes = pdf_path.read_bytes()
                storage_path, sha, sz, mime = await save_encrypted_file(
                    patient_id=p_obj.id,
                    file_bytes=file_bytes,
                    filename=fname
                )

                extracted_text = (
                    f"CITY CARE HOSPITAL - {doc_title}\n"
                    f"Patient Name: {pt_name_on_doc}\n"
                    f"Patient ID: {code}\n"
                    f"Validity Period: {valid_period}\n"
                    f"Diagnosis: Acute Enteritis with Moderate Dehydration\n"
                    f"Policy: {p_data['policy']}\n"
                    f"Total Amount Claimed: Rs. 32,700\n"
                )

                meta_data = {
                    "issue_date": "2024-01-15",
                    "expiry_date": "2023-01-01" if (trap == "expired_policy_copy" and doc_type == "policy_copy") else ("2027-12-31" if doc_type == "policy_copy" else None),
                    "period_from": "2024-01-10",
                    "period_to": "2024-01-15",
                    "issuer": "City Care Hospital",
                    "patient_name_on_doc": pt_name_on_doc,
                    "name_matches_patient": (pt_name_on_doc == p_data["name"]),
                    "amount": 32700,
                    "legibility_score": legibility,
                    "summary_redacted": f"{doc_title} for treatment in Jan 2024"
                }

                doc = Document(
                    patient_id=p_obj.id,
                    filename=fname,
                    mime=mime,
                    size=sz,
                    sha256=sha,
                    storage_path=storage_path,
                    uploaded_by="patient",
                    source="patient",
                    doc_kind="general",
                    doc_type=doc_type,
                    doc_type_confidence=0.98 if legibility > 0.5 else 0.45,
                    classification_status="done",
                    extracted_text_enc=encrypt_text(extracted_text),
                    redacted_text=extracted_text.replace(p_data["name"], "[PATIENT]"),
                    extraction_method="text",
                    legibility_score=legibility,
                    meta=meta_data,
                    is_superseded=False
                )
                session.add(doc)

        await session.flush()

        # 5. Generate 12 Query Letters & Expected Answers
        print("Generating 12 synthetic query letters...")
        letters_spec = [
            {
                "id": "L01",
                "patient_code": "PT-0001",
                "claim_ref": "CLM-ST-88190",
                "insurer": "Star Health Insurance",
                "title": "Claim Query Deficiency Letter",
                "points": [
                    "1. Please provide the hospital final itemized bill and doctor's prescription."
                ],
                "expected": [
                    {
                        "ordinal": 1,
                        "normalized_ask": "Provide hospital final itemized bill and doctor's prescription",
                        "point_type": "document_request",
                        "decision": "needs_new_document",  # final_bill is in locker, prescriptions is missing
                        "needed_doc_types": ["prescriptions"],
                        "covered_doc_types": ["final_hospital_bill"]
                    }
                ]
            },
            {
                "id": "L02",
                "patient_code": "PT-0001",
                "claim_ref": "CLM-ST-88191",
                "insurer": "Star Health Insurance",
                "title": "Additional Information Request",
                "points": [
                    "1. Please submit the treating physician certificate justifying hospital admission.",
                    "2. Submit itemized pharmacy bills and chemist receipts.",
                    "3. Submit operation notes and implant invoice if any surgery performed."
                ],
                "expected": [
                    {
                        "ordinal": 1,
                        "normalized_ask": "Submit treating physician certificate justifying admission",
                        "point_type": "document_request",
                        "decision": "needs_new_document",
                        "needed_doc_types": ["doctor_note_treatment"]
                    },
                    {
                        "ordinal": 2,
                        "normalized_ask": "Submit pharmacy bills and receipts",
                        "point_type": "document_request",
                        "decision": "needs_new_document",
                        "needed_doc_types": ["pharmacy_bills"]
                    },
                    {
                        "ordinal": 3,
                        "normalized_ask": "Submit operation notes and implant invoice",
                        "point_type": "document_request",
                        "decision": "needs_new_document",
                        "needed_doc_types": ["operation_notes"]
                    }
                ]
            },
            {
                "id": "L03",
                "patient_code": "PT-0002",
                "claim_ref": "CLM-HE-41092",
                "insurer": "HDFC ERGO General Insurance",
                "title": "Claim Assessment Notice - Unnumbered Asks",
                "points": [
                    "We are processing the reimbursement claim and observe that Indoor Case Papers and admission notes are required to verify the duration of intravenous fluid administration. Kindly furnish the indoor case papers at the earliest."
                ],
                "expected": [
                    {
                        "ordinal": 1,
                        "normalized_ask": "Furnish indoor case papers and admission notes",
                        "point_type": "document_request",
                        "decision": "needs_new_document",
                        "needed_doc_types": ["consultation_papers"]
                    }
                ]
            },
            {
                "id": "L04",
                "patient_code": "PT-0002",
                "claim_ref": "CLM-HE-41093",
                "insurer": "HDFC ERGO General Insurance",
                "title": "Compound Documentation Request",
                "points": [
                    "1. Please submit the discharge card along with complete payment receipts and cancelled cheque for NEFT settlement."
                ],
                "expected": [
                    {
                        "ordinal": 1,
                        "normalized_ask": "Submit discharge card, payment receipts, and cancelled cheque",
                        "point_type": "document_request",
                        "decision": "covered",  # PT-0002 has discharge card, payment receipts, cancelled cheque in locker!
                        "needed_doc_types": [],
                        "covered_doc_types": ["discharge_summary", "payment_receipts", "bank_proof"]
                    }
                ]
            },
            {
                "id": "L05",
                "patient_code": "PT-0003",
                "claim_ref": "CLM-CH-67211",
                "insurer": "Care Health Insurance",
                "title": "Deficiency Notice - Vague Requirement",
                "points": [
                    "1. Kindly provide all supporting documents for medical necessity of hospital admission."
                ],
                "expected": [
                    {
                        "ordinal": 1,
                        "normalized_ask": "Provide supporting documents for medical necessity",
                        "point_type": "document_request",
                        "decision": "needs_new_document",
                        "needed_doc_types": ["doctor_note_treatment"]
                    }
                ]
            },
            {
                "id": "L06",
                "patient_code": "PT-0003",
                "claim_ref": "CLM-CH-67212",
                "insurer": "Care Health Insurance",
                "title": "Clarification Requirement",
                "points": [
                    "1. Please explain the 3-day delay in intimation of hospitalization to the insurance company."
                ],
                "expected": [
                    {
                        "ordinal": 1,
                        "normalized_ask": "Explain 3-day delay in intimation of hospitalization",
                        "point_type": "clarification",
                        "decision": "needs_patient_clarification",
                        "needed_doc_types": []
                    }
                ]
            },
            {
                "id": "L07",
                "patient_code": "PT-0004",
                "claim_ref": "CLM-IL-11891",
                "insurer": "ICICI Lombard",
                "title": "Diagnostic Verification Query",
                "points": [
                    "1. The submitted laboratory report is unclear and illegible. Please submit a legible copy of all diagnostic pathology reports.",
                    "2. Submit treating doctor's prescription slip."
                ],
                "expected": [
                    {
                        "ordinal": 1,
                        "normalized_ask": "Submit legible copy of laboratory reports",
                        "point_type": "document_request",
                        "decision": "needs_new_document",  # PT-0004 has blurry lab report (legibility 0.35), so needs clearer copy
                        "needed_doc_types": ["lab_reports"]
                    },
                    {
                        "ordinal": 2,
                        "normalized_ask": "Submit doctor prescription slip",
                        "point_type": "document_request",
                        "decision": "needs_new_document",
                        "needed_doc_types": ["prescriptions"]
                    }
                ]
            },
            {
                "id": "L08",
                "patient_code": "PT-0008",
                "claim_ref": "CLM-CH-99881",
                "insurer": "Care Health Insurance",
                "title": "All-Clear Repeat Notice",
                "points": [
                    "1. Please submit the discharge summary, final hospital bill, and payment receipt."
                ],
                "expected": [
                    {
                        "ordinal": 1,
                        "normalized_ask": "Submit discharge summary, final hospital bill, and payment receipt",
                        "point_type": "document_request",
                        "decision": "covered",  # PT-0008 has all 3 in locker -> All Clear!
                        "needed_doc_types": [],
                        "covered_doc_types": ["discharge_summary", "final_hospital_bill", "payment_receipts"]
                    }
                ]
            },
            {
                "id": "L09",
                "patient_code": "PT-0005",
                "claim_ref": "CLM-NB-99015",
                "insurer": "Niva Bupa Health Insurance",
                "title": "Query with Heavy Legal Boilerplate",
                "points": [
                    "NOTICE UNDER CLAUSE 14 OF IRDAI REGULATIONS 2016.",
                    "Without prejudice to the rights and contentions of the company under policy terms:",
                    "1. Provide previous year policy schedule copy to verify waiting period continuity.",
                    "2. Furnish signed Claim Form Part B from the hospital."
                ],
                "expected": [
                    {
                        "ordinal": 1,
                        "normalized_ask": "Provide previous year policy schedule copy",
                        "point_type": "document_request",
                        "decision": "needs_new_document",
                        "needed_doc_types": ["previous_policy"]
                    },
                    {
                        "ordinal": 2,
                        "normalized_ask": "Furnish signed Claim Form Part B",
                        "point_type": "document_request",
                        "decision": "needs_new_document",
                        "needed_doc_types": ["claim_form"]
                    }
                ]
            },
            {
                "id": "L10",
                "patient_code": "PT-0006",
                "claim_ref": "CLM-ST-77335",
                "insurer": "Star Health Insurance",
                "title": "Notice with Hidden Request in Closing",
                "points": [
                    "We acknowledge receipt of your claim documents for Star Health Insurance policy.",
                    "The medical team has reviewed your records and approved the surgical component.",
                    "Kindly note that cancelled cheque with printed name must be submitted before NEFT disbursement."
                ],
                "expected": [
                    {
                        "ordinal": 1,
                        "normalized_ask": "Submit cancelled cheque with printed name",
                        "point_type": "document_request",
                        "decision": "covered",  # PT-0006 has bank_proof in locker
                        "needed_doc_types": [],
                        "covered_doc_types": ["bank_proof"]
                    }
                ]
            },
            {
                "id": "L11",
                "patient_code": "PT-0007",
                "claim_ref": "CLM-HE-55444",
                "insurer": "HDFC ERGO General Insurance",
                "title": "Query with Transliterated Asks",
                "points": [
                    "1. Kripya doctor ka treatment note aur justification certificate jama karein.",
                    "2. Submit chemist pharmacy bills for verification."
                ],
                "expected": [
                    {
                        "ordinal": 1,
                        "normalized_ask": "Submit doctor treatment note and justification certificate",
                        "point_type": "document_request",
                        "decision": "needs_new_document",
                        "needed_doc_types": ["doctor_note_treatment"]
                    },
                    {
                        "ordinal": 2,
                        "normalized_ask": "Submit chemist pharmacy bills",
                        "point_type": "document_request",
                        "decision": "needs_new_document",
                        "needed_doc_types": ["pharmacy_bills"]
                    }
                ]
            },
            {
                "id": "L12",
                "patient_code": "PT-0003",
                "claim_ref": "CLM-CH-67215",
                "insurer": "Care Health Insurance",
                "title": "Trap Validation Letter",
                "points": [
                    "1. Please submit the itemized final hospital bill showing patient name clearly.",
                    "2. Provide FIR or MLC report if accident related."
                ],
                "expected": [
                    {
                        "ordinal": 1,
                        "normalized_ask": "Submit final hospital bill showing patient name clearly",
                        "point_type": "document_request",
                        "decision": "needs_new_document",  # PT-0003 has bill under Ramesh Gupta (name mismatch) -> MUST ask for valid bill!
                        "needed_doc_types": ["final_hospital_bill"]
                    },
                    {
                        "ordinal": 2,
                        "normalized_ask": "Provide FIR or MLC report",
                        "point_type": "document_request",
                        "decision": "needs_new_document",
                        "needed_doc_types": ["fir_mlc"]
                    }
                ]
            }
        ]

        expected_manifest = {}

        for l_spec in letters_spec:
            l_id = l_spec["id"]
            pdf_path = LETTERS_DIR / f"{l_id}.pdf"
            p_code = l_spec["patient_code"]
            p_obj = created_patients[p_code]

            lines = [
                f"INSURER: {l_spec['insurer'].upper()}",
                f"Deficiency Letter Ref: {l_spec['claim_ref']}",
                f"Date of Notice: 2024-01-20",
                f"Insured Patient: {p_obj.full_name} | Policy: {p_data['policy']}",
                "---",
                f"# SUBJECT: {l_spec['title'].upper()}",
                "Dear Policyholder,",
                "With reference to your health insurance claim under the above mentioned policy,",
                "the claim cannot be processed further without the following requirements:",
            ]
            for pt in l_spec["points"]:
                lines.append(pt)
            lines.extend([
                "---",
                "Please submit these requirements within 15 days of this notice to avoid claim closure.",
                "Yours faithfully,",
                f"Claims Assessment Dept, {l_spec['insurer']}"
            ])

            make_pdf(pdf_path, f"{l_spec['insurer'].upper()}", lines, header_color=colors.darkred)

            expected_manifest[l_id] = {
                "letter_id": l_id,
                "patient_code": p_code,
                "claim_ref": l_spec["claim_ref"],
                "insurer_name": l_spec["insurer"],
                "pdf_file": str(pdf_path),
                "expected_points": l_spec["expected"]
            }

        # Write expected.json
        expected_json_path = SEED_DIR / "expected.json"
        with open(expected_json_path, "w", encoding="utf-8") as f:
            json.dump(expected_manifest, f, indent=2)

        print(f"Saved expected manifest to {expected_json_path}")
        await session.commit()

    print("=== Deterministic Seed Generation Completed Successfully ===")


if __name__ == "__main__":
    asyncio.run(seed_database())
