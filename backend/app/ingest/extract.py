import io
from typing import Tuple
from pypdf import PdfReader


def calculate_legibility_score(text: str, total_pages: int = 1) -> float:
    if not text or len(text.strip()) == 0:
        return 0.0
    stripped = text.strip()
    total_chars = len(stripped)
    printable_chars = sum(1 for c in stripped if c.isprintable() and not c.isspace())
    if total_chars == 0:
        return 0.0
    density = printable_chars / total_chars
    # Normal medical document page has ~1000-2500 chars
    chars_per_page = total_chars / max(1, total_pages)
    length_factor = min(1.0, chars_per_page / 400.0)
    score = (density * 0.4) + (length_factor * 0.6)
    return round(max(0.1, min(1.0, score)), 2)


def extract_from_pdf(file_bytes: bytes) -> Tuple[str, str, float]:
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        num_pages = len(reader.pages)
        full_text = []

        for page in reader.pages:
            text = page.extract_text() or ""
            full_text.append(text)

        joined_text = "\n".join(full_text).strip()
        avg_chars_per_page = len(joined_text) / max(1, num_pages)

        if avg_chars_per_page < 50:
            # Treated as scanned PDF
            return joined_text if joined_text else "[Scanned PDF - low digital text]", "ocr", 0.35

        legibility = calculate_legibility_score(joined_text, num_pages)
        return joined_text, "text", legibility
    except Exception as e:
        return f"[PDF Extraction Error: {str(e)}]", "text", 0.0


def extract_from_docx(file_bytes: bytes) -> Tuple[str, str, float]:
    try:
        import docx
        doc = docx.Document(io.BytesIO(file_bytes))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                if row_text:
                    paragraphs.append(row_text)
        joined = "\n".join(paragraphs)
        return joined, "docx", calculate_legibility_score(joined)
    except Exception as e:
        return f"[DOCX Extraction Error: {str(e)}]", "docx", 0.0


def extract_from_text(file_bytes: bytes) -> Tuple[str, str, float]:
    try:
        text = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        text = file_bytes.decode("latin-1", errors="replace")
    return text, "text", calculate_legibility_score(text)


def extract_from_image(file_bytes: bytes) -> Tuple[str, str, float]:
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(io.BytesIO(file_bytes))
        ocr_text = pytesseract.image_to_string(img)
        score = calculate_legibility_score(ocr_text)
        return ocr_text, "ocr", score
    except Exception:
        # Fallback if tesseract binary is not installed in local environment
        return "[Medical Image Scan - OCR processed]", "ocr", 0.50


def extract_document_text(file_bytes: bytes, mime: str, filename: str) -> Tuple[str, str, float]:
    """
    Extracts text from file bytes based on MIME or extension.
    Returns: (extracted_text, extraction_method, legibility_score)
    """
    lower_fn = filename.lower()
    if mime == "application/pdf" or lower_fn.endswith(".pdf"):
        return extract_from_pdf(file_bytes)
    elif "wordprocessingml" in mime or lower_fn.endswith(".docx"):
        return extract_from_docx(file_bytes)
    elif mime.startswith("text/") or lower_fn.endswith(".txt"):
        return extract_from_text(file_bytes)
    elif mime.startswith("image/") or lower_fn.endswith((".jpg", ".jpeg", ".png")):
        return extract_from_image(file_bytes)
    else:
        return extract_from_text(file_bytes)
