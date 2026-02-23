import io
import logging

import pdfplumber

from config import MAX_DOC_CHARS

logger = logging.getLogger(__name__)


def _table_to_markdown(table: list[list]) -> str:
    if not table:
        return ""
    rows = []
    for i, row in enumerate(table):
        cells = [str(cell or "").strip() for cell in row]
        rows.append("| " + " | ".join(cells) + " |")
        if i == 0:
            rows.append("|" + "|".join(["---"] * len(cells)) + "|")
    return "\n".join(rows)


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text and tables from PDF bytes using pdfplumber."""
    pages_text = []
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                parts = []
                text = page.extract_text(x_tolerance=3, y_tolerance=3)
                if text:
                    parts.append(text.strip())
                tables = page.extract_tables()
                for table in tables:
                    md = _table_to_markdown(table)
                    if md:
                        parts.append(md)
                if parts:
                    pages_text.append("\n".join(parts))
    except Exception as e:
        logger.error(f"PDF extraction error: {e}")
        raise ValueError(f"Failed to extract PDF: {e}")

    full_text = "\n\n".join(pages_text)
    if len(full_text) > MAX_DOC_CHARS:
        full_text = full_text[:MAX_DOC_CHARS]
    return full_text
