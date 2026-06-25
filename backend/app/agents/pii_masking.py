"""
Production: Deterministic PII Scrubber
==========================================
Runs as a backstop AFTER the Typhoon Interpreter LLM call, on both
normalized_thai and english_translation, before anything gets logged to
AgentRun / WorkflowState / the LangGraph SQLite checkpoint.

Why a deterministic backstop and not just a prompt instruction:
  Same philosophy as the rest of this pipeline (tax math, risk ceilings,
  disclaimer enforcement) — an LLM instruction to "don't include PII" can be
  forgotten or partially followed, especially when the source text is a
  pasted document full of ID numbers and names. A regex-based scrubber gives
  a guarantee independent of model behavior. The LLM-side prompt change
  (asking it to extract only financial figures, not dump the document) is
  still the first line of defense — this is the second line, not a
  replacement.

Coverage:
  - Thai national ID / taxpayer ID numbers (13 digits, with or without
    dashes: X-XXXX-XXXXX-XX-X)
  - Phone numbers (Thai mobile/landline formats)
  - Email addresses
  - Bank/registration-style long digit runs (10+ consecutive digits, catches
    company registration numbers, account numbers not matched above)
  - Thai honorific + name patterns (นาย/นาง/นางสาว/บริษัท ... จำกัด)

This is intentionally biased toward over-masking: a false positive (masking
something that wasn't actually PII, e.g. an amount that happens to be 10+
digits) is far cheaper than a false negative (a real ID number leaking into
logs). If a number that should have stayed (e.g. a large THB amount) gets
masked, that's a sign the upstream prompt is returning raw document content
that shouldn't be there in the first place — fix the prompt, not the masker.
"""

import re

_PATTERNS = [
    # Thai national ID / taxpayer ID: 13 digits, optionally dashed
    # e.g. 1-2345-67890-12-3 or 1234567890123
    (re.compile(r"\b\d-?\d{4}-?\d{5}-?\d{2}-?\d\b"), "[เลขประจำตัว-ถูกปิดบัง]"),

    # Thai phone numbers: 0XX-XXX-XXXX or 0XXXXXXXXX (9-10 digits starting with 0)
    (re.compile(r"\b0\d{1,2}-?\d{3}-?\d{4}\b"), "[เบอร์โทร-ถูกปิดบัง]"),

    # Email addresses
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "[อีเมล-ถูกปิดบัง]"),

    # Any other run of 10+ consecutive digits (company registration numbers,
    # bank account numbers, etc. not already caught above). Runs AFTER the
    # more specific patterns so it doesn't fight them.
    (re.compile(r"\b\d{10,}\b"), "[หมายเลข-ถูกปิดบัง]"),

    # Thai honorific + name: นาย/นาง/นางสาว followed by 1-3 Thai words
    (re.compile(r"(?:นาย|นาง|นางสาว)\s*[ก-๙]+(?:\s+[ก-๙]+){0,2}"), "[ชื่อบุคคล-ถูกปิดบัง]"),

    # Company name pattern: "บริษัท ... จำกัด" (with optional มหาชน)
    (re.compile(r"บริษัท[ก-๙\s]+?จำกัด(?:\s*\(มหาชน\))?"), "[ชื่อบริษัท-ถูกปิดบัง]"),
]


def mask_pii(text: str) -> str:
    """Apply all masking patterns in order. Idempotent — safe to call on
    already-masked text."""
    if not text:
        return text
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def mask_typhoon_output(typhoon_result) -> None:
    """Mutates a TyphoonOutputSchema instance in place: scrubs
    normalized_thai and english_translation. entities (age, monthly_income,
    goal, etc.) are untouched — those are exactly the structured financial
    fields downstream nodes need, and they aren't PII on their own.

    Call this immediately after _coerce_typhoon(), before the result is
    returned from run_typhoon_interpreter_crew() — i.e. before it ever
    reaches log_agent_run_to_db() or save_workflow_state_to_db().
    """
    typhoon_result.normalized_thai = mask_pii(typhoon_result.normalized_thai)
    typhoon_result.english_translation = mask_pii(typhoon_result.english_translation)
