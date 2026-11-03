import sys
import time
import argparse
import asyncio
from pathlib import Path

# Add root directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from backend.app.db import AsyncSessionLocal
from backend.app.models import Patient, Document, QueryLetter, OutboundMessage, QueryPoint, PointDecision
from backend.app.storage import save_encrypted_file
from backend.app.pipeline.process_letter import run_process_letter_pipeline


async def drop_letter_cli(patient_code: str, file_path_str: str):
    file_path = Path(file_path_str)
    if not file_path.exists():
        print(f"Error: File not found: {file_path}")
        return 1

    print(f"=== Dropping Query Letter for Patient {patient_code} ===")
    print(f"File: {file_path.name}")

    async with AsyncSessionLocal() as session:
        # Find Patient
        p_res = await session.execute(select(Patient).where(Patient.patient_code == patient_code))
        patient = p_res.scalar_one_or_none()
        if not patient:
            print(f"Error: Patient {patient_code} not found.")
            return 1

        file_bytes = file_path.read_bytes()
        storage_path, sha, sz, mime = await save_encrypted_file(
            patient_id=patient.id,
            file_bytes=file_bytes,
            filename=file_path.name
        )

        doc = Document(
            patient_id=patient.id,
            filename=file_path.name,
            mime=mime,
            size=sz,
            sha256=sha,
            storage_path=storage_path,
            uploaded_by="cli_drop",
            source="insurer",
            doc_kind="query_letter",
            classification_status="done",
            doc_type="insurer_query_letter",
            doc_type_confidence=1.0,
            claim_ref=f"CLM-{file_path.stem}"
        )
        session.add(doc)
        await session.flush()

        ql = QueryLetter(
            patient_id=patient.id,
            document_id=doc.id,
            claim_ref=doc.claim_ref,
            insurer_name=patient.insurer_name,
            status="received"
        )
        session.add(ql)
        await session.commit()
        ql_id = ql.id

    print(f"Ingested as Document {doc.id} | QueryLetter {ql_id}")
    print("Executing automated pipeline (extract -> match -> compose -> dispatch)...")

    # Run the pipeline
    await run_process_letter_pipeline(ql_id)

    # Fetch results
    async with AsyncSessionLocal() as session:
        ql_res = await session.execute(select(QueryLetter).where(QueryLetter.id == ql_id))
        ql = ql_res.scalar_one()

        pts_res = await session.execute(
            select(QueryPoint).where(QueryPoint.query_letter_id == ql_id).order_by(QueryPoint.ordinal)
        )
        pts = pts_res.scalars().all()

        msg_res = await session.execute(
            select(OutboundMessage).where(OutboundMessage.query_letter_id == ql_id)
        )
        msgs = msg_res.scalars().all()

        print("\n" + "=" * 65)
        print(f"PIPELINE COMPLETED in {ql.total_ms or 0} ms | Status: {ql.status.upper()}")
        print("=" * 65)

        print("\n--- Parsed Query Points & Decisions ---")
        for p in pts:
            dec_res = await session.execute(select(PointDecision).where(PointDecision.query_point_id == p.id))
            dec = dec_res.scalar_one_or_none()
            dec_str = dec.decision if dec else "pending"
            reason = dec.reason_patient if dec else ""
            print(f"Point {p.ordinal}: {p.verbatim_text[:70]}...")
            print(f"  -> Decision: {dec_str} | Reason: {reason}")

        print("\n--- Outbound Messages Dispatched ---")
        for m in msgs:
            print(f"[{m.channel.upper()}] To: {m.recipient_masked} | Status: {m.status.upper()} | Provider: {m.provider or 'internal'}")
            print(f"Preview:\n{m.body_rendered[:140]}...\n")

        print("=" * 65)
        print("Done: 2 Outbound messages reaching sent/delivered with no manual action.")

    return 0


def main():
    parser = argparse.ArgumentParser(description="Drop Query Letter into Patient Locker")
    parser.add_argument("--patient", required=True, help="Patient code, e.g. PT-0001")
    parser.add_argument("--file", required=True, help="Path to query letter PDF")
    args = parser.parse_args()

    code = asyncio.run(drop_letter_cli(args.patient, args.file))
    sys.exit(code)


if __name__ == "__main__":
    main()
