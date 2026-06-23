"""Extract Thai financial text from uploaded documents (PDF, JPG, PNG).

Strategy:
- PDF with a text layer  -> PyMuPDF text extraction (fast, exact).
- Scanned PDF / images   -> Groq vision model (Llama 4 Scout) transcribes the
  financial content into Thai text.

The output is plain text that feeds the existing Typhoon interpreter, which then
structures it. This layer never calculates or advises — it only transcribes.
"""
import base64
from typing import Tuple

from openai import OpenAI

from backend.app.config import settings

# Groq vision-capable model (confirmed available on the project's key).
VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

# Min characters of extracted PDF text before we treat it as a real text layer
# (anything less is assumed to be a scanned/image PDF needing vision).
_PDF_TEXT_MIN = 40
_MAX_VISION_PAGES = 5

_VISION_PROMPT = (
    "You are reading a Thai financial document — a payslip, tax form (e.g. 50 ทวิ), "
    "fund/RMF/SSF statement, insurance policy, or a handwritten note. Transcribe ALL "
    "financial information you can see into clear Thai text: salary (เงินเดือน), bonus "
    "(โบนัส), other income, RMF/SSF/ThaiESG holdings, provident fund (กองทุนสำรองเลี้ยงชีพ), "
    "insurance premiums (ประกันชีวิต/สุขภาพ/บำนาญ), home loan interest (ดอกเบี้ยบ้าน), "
    "family/dependents (คู่สมรส/บุตร/บิดามารดา), and any stated goals or risk preferences. "
    "Preserve exact numbers. Do NOT calculate taxes or give advice. If the image is "
    "unreadable, say so briefly. Output plain text only."
)


def _vision_client() -> OpenAI:
    if not settings.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not configured")
    return OpenAI(base_url=GROQ_BASE_URL, api_key=settings.GROQ_API_KEY)


def _vision_extract(data_url: str) -> str:
    resp = _vision_client().chat.completions.create(
        model=VISION_MODEL,
        temperature=0,
        max_tokens=1500,
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": _VISION_PROMPT},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        }],
    )
    return (resp.choices[0].message.content or "").strip()


def _extract_pdf(content: bytes) -> Tuple[str, str]:
    import fitz  # PyMuPDF

    doc = fitz.open(stream=content, filetype="pdf")
    try:
        text = "\n".join(page.get_text() for page in doc).strip()
        if len(text) >= _PDF_TEXT_MIN:
            return text, "pdf-text"
        # Scanned PDF: render pages to images and run vision on each.
        parts = []
        for i, page in enumerate(doc):
            if i >= _MAX_VISION_PAGES:
                break
            png = page.get_pixmap(dpi=150).tobytes("png")
            data_url = "data:image/png;base64," + base64.b64encode(png).decode()
            parts.append(_vision_extract(data_url))
        return "\n".join(p for p in parts if p).strip(), "pdf-vision"
    finally:
        doc.close()


def extract_text_from_file(filename: str, content: bytes) -> Tuple[str, str]:
    """Return (extracted_text, method) for a supported document.

    Raises ValueError for unsupported file types.
    """
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        return _extract_pdf(content)
    if name.endswith((".jpg", ".jpeg", ".png")):
        mime = "image/png" if name.endswith(".png") else "image/jpeg"
        data_url = f"data:{mime};base64," + base64.b64encode(content).decode()
        return _vision_extract(data_url), "vision"
    raise ValueError("Unsupported file type. Please upload a PDF, JPG, JPEG, or PNG.")
