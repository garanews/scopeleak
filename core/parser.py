"""Agreement upload -> plain text."""
import fitz  # PyMuPDF


def extract_text(filename: str, data: bytes) -> str:
    if filename.lower().endswith(".pdf"):
        with fitz.open(stream=data, filetype="pdf") as doc:
            return "\n".join(page.get_text() for page in doc)
    return data.decode("utf-8", errors="replace")
