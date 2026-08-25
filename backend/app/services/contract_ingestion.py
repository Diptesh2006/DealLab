from pathlib import Path

import fitz


def extract_text_from_pdf(path: Path) -> str:
    with fitz.open(path) as document:
        pages = [page.get_text("text") for page in document]
    return "\n".join(pages).strip()


def normalize_contract_text(text: str) -> str:
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())
