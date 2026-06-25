"""
Production: What-If Intent Detector — Chat Layer Add-on
============================================================
Problem this solves:
  The chat synthesizer (chat_service.py) correctly refuses to compute new
  numbers for scenarios outside session_context (e.g. "ถ้าลงทุน 350,000
  บาท แยก 2 กอง จะลดภาษีเท่าไหร่") — that's the right safety behavior.
  But today it just says "ไปปรึกษาที่ปรึกษา", which is a dead end for the
  client. This module detects that the question is a WHAT-IF that the
  pipeline COULD answer (by re-running Tax Engine / Suitability with a new
  amount), and returns a structured suggested_action the frontend renders
  as a prefilled "Apply & re-analyze" CTA instead of a plain refusal.

IMPORTANT — division of responsibility:
  This module ONLY detects intent and extracts a candidate amount. It does
  NOT compute tax savings itself. The actual numbers still only ever come
  from re-running the deterministic Tax Engine (node 4) via /analyze with
  overrides — never from this layer or from the chat LLM.

Usage (inside the /chat endpoint, BEFORE calling the chat LLM):
    what_if = detect_what_if(client_question)
    if what_if.detected:
        reply_text = WHAT_IF_REFUSAL_TEMPLATE.format(amount_str=what_if.amount_str)
        return {"reply": reply_text,
                "suggested_action": what_if.to_suggested_action()}
    # else: fall through to the normal chat_service.py synthesis path
"""

import re
from dataclasses import dataclass
from typing import Optional


# Thai number-word multipliers, reused from the same glossary logic as the
# Typhoon Interpreter (node 1) so "สามแสน", "ห้าหมื่น" etc. parse consistently
# across the whole system instead of having a second, divergent parser.
_THAI_UNIT_MULTIPLIERS = {
    "หมื่น": 10_000,
    "แสน": 100_000,
    "ล้าน": 1_000_000,
}

_THAI_DIGIT_WORDS = {
    "หนึ่ง": 1, "สอง": 2, "สาม": 3, "สี่": 4, "ห้า": 5,
    "หก": 6, "เจ็ด": 7, "แปด": 8, "เก้า": 9, "สิบ": 10,
}

# Trigger phrases for a hypothetical / what-if framing in Thai.
_WHAT_IF_TRIGGERS = [
    r"ถ้าลง", r"ถ้าลงทุน", r"ถ้าซื้อ", r"ถ้าจ่าย", r"ถ้าเพิ่ม",
    r"สมมติ(?:ว่า)?ลง", r"สมมติ(?:ว่า)?ซื้อ", r"หากลงทุน", r"หากซื้อ",
    r"แยกเป็น\s*\d", r"แบ่งเป็น\s*\d",
]
_WHAT_IF_PATTERN = re.compile("|".join(_WHAT_IF_TRIGGERS))

# Numeric amount, optionally with comma separators, optionally followed by บาท.
_AMOUNT_PATTERN = re.compile(r"(\d{1,3}(?:,\d{3})+|\d{4,})(?:\s*บาท)?")

# Simple Thai number-word amount, e.g. "สามแสน", "ห้าหมื่นห้าพัน".
_THAI_AMOUNT_PATTERN = re.compile(
    "(" + "|".join(_THAI_DIGIT_WORDS) + ")?(" + "|".join(_THAI_UNIT_MULTIPLIERS) + ")"
)


@dataclass
class WhatIfIntent:
    detected: bool
    amount: Optional[float] = None
    amount_str: Optional[str] = None
    raw_question: str = ""

    def to_suggested_action(self) -> Optional[dict]:
        if not self.detected:
            return None
        return {
            "type": "reanalyze_form",
            "label": "ลองคำนวณสถานการณ์นี้",
            "prefill": {"investment_amount": self.amount} if self.amount is not None else {},
        }


def _parse_amount(text: str) -> Optional[float]:
    """Best-effort numeric extraction. Returns None rather than guessing if
    the phrasing is too ambiguous to parse confidently — an unfilled form
    field is safer than a wrong prefill."""
    digit_match = _AMOUNT_PATTERN.search(text)
    if digit_match:
        try:
            return float(digit_match.group(1).replace(",", ""))
        except ValueError:
            pass

    thai_match = _THAI_AMOUNT_PATTERN.search(text)
    if thai_match:
        digit_word, unit_word = thai_match.group(1), thai_match.group(2)
        multiplier = _THAI_UNIT_MULTIPLIERS.get(unit_word)
        if multiplier is None:
            return None
        count = _THAI_DIGIT_WORDS.get(digit_word, 1) if digit_word else 1
        return float(count * multiplier)

    return None


def detect_what_if(client_question: str) -> WhatIfIntent:
    """Detect whether the client is asking a hypothetical re-allocation/
    re-investment question that the LLM should NOT try to answer with new
    arithmetic, but that the deterministic pipeline COULD answer if re-run
    with a different amount.
    """
    if not _WHAT_IF_PATTERN.search(client_question):
        return WhatIfIntent(detected=False, raw_question=client_question)

    amount = _parse_amount(client_question)
    amount_str = f"{amount:,.0f} บาท" if amount is not None else "จำนวนที่คุณระบุ"
    return WhatIfIntent(
        detected=True,
        amount=amount,
        amount_str=amount_str,
        raw_question=client_question,
    )


WHAT_IF_REFUSAL_TEMPLATE = (
    "ระบบยังไม่มีตัวเลขสำหรับสถานการณ์ {amount_str} เพราะต้องคำนวณภาษีใหม่ทั้งหมด "
    "ซึ่งเป็นหน้าที่ของเครื่องคำนวณภาษีโดยเฉพาะ ไม่ใช่สิ่งที่แชทนี้จะประมาณเองได้\n\n"
    "กดปุ่มด้านล่างเพื่อกรอกจำนวนเงินนี้เข้าฟอร์ม แล้วระบบจะคำนวณแผนใหม่ให้ทันที"
)


# ----------------------------------------------------------------------------
# Addendum to chat_service.CHAT_SYSTEM_PROMPT — append this only on the turns
# where detect_what_if() fired, so the LLM (if it still generates any prose
# around the CTA) reinforces the same "can't compute, use the form" framing
# instead of contradicting the structured suggested_action.
# ----------------------------------------------------------------------------
WHAT_IF_SYSTEM_ADDENDUM = """\

กฎเพิ่มเติมสำหรับคำถามเชิงสมมติ (what-if):
ถ้าลูกค้าถามสถานการณ์ใหม่ที่ไม่อยู่ใน session_context (เช่น "ถ้าลงทุนจำนวนอื่น
จะลดภาษีเท่าไหร่") ห้ามคำนวณเองและห้ามบอกแค่ "ไปปรึกษาที่ปรึกษา" เด็ดขาด —
ให้บอกลูกค้าสั้นๆว่าต้องคำนวณใหม่ทั้งหมด และให้ใช้ปุ่ม/ฟอร์มที่ระบบแสดงให้
ด้านล่างข้อความเพื่อกรอกจำนวนเงินแล้วให้ระบบคำนวณแผนใหม่ ไม่ต้องอธิบายซ้ำว่า
"ทำไมคำนวณเองไม่ได้" ยาวเกินไป — สั้น กระชับ แล้วชี้ไปที่ปุ่ม
"""
