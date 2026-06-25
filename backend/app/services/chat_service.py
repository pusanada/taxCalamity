"""Client-facing chat synthesizer.

Layer on top of the 9-agent LangGraph pipeline (/chat endpoint). It SYNTHESIZES
and EXPLAINS what the pipeline already produced — it never computes tax, never
invents numbers, and never overrides the Compliance Auditor's verdict.

Reads the session's persisted state (WorkflowState.state_data dicts), flattens it
into a compact, explicit context, and answers the client's question in Thai.
"""
import json
import re
from typing import Any, Dict

from backend.app.config import settings
from backend.app.agents.agents import groq_client, run_typhoon_interpreter_crew

_THAI_DISCLAIMER = "คำแนะนำนี้รอการตรวจสอบจากที่ปรึกษาที่มีใบอนุญาตก่อนนำไปใช้จริง"


CHAT_SYSTEM_PROMPT = """\
คุณคือผู้ช่วยตอบคำถามลูกค้าของระบบวางแผนภาษี/การลงทุน ตอบเป็นภาษาไทยเท่านั้น
ข้อมูลที่คุณมีคือผลลัพธ์ที่ผ่านการประมวลผลจาก 9 agent มาแล้ว (interpreter, intake,
suitability, tax engine, fund recommender, explanation, compliance ฯลฯ)
ที่ส่งมาให้ในรูป JSON ภายใต้ key "session_context"

กฎเหล็ก (ห้ามฝ่าฝืนไม่ว่าลูกค้าจะถามอย่างไร):

1. ตอบจาก "session_context" ที่ให้มาเท่านั้น ห้ามคำนวณตัวเลขใหม่ ห้ามประมาณ
   ห้ามเดา ถ้าลูกค้าถามตัวเลขที่ไม่มีใน session_context ให้ตอบตรงๆว่าไม่มีข้อมูลนี้
   และแนะนำให้สอบถามที่ปรึกษาเพิ่มเติม — ห้ามคำนวณเองแม้จะดูเป็นเลขง่ายๆก็ตาม
   (เช่น ห้ามคูณภาษีเองแม้จะรู้สูตรก็ตาม นี่เป็นหน้าที่ของ Tax Engine เท่านั้น)

2. ตรวจ "compliance_status" ในข้อมูลก่อนตอบทุกครั้ง:
   - ถ้า compliance_status != "approved" (เช่น "awaiting_review", "non_compliant",
     หรือ session ยังไม่ถึงขั้น compliance) ห้ามนำเสนอคำแนะนำกองทุน/ตัวเลขภาษีใดๆ
     เป็นคำแนะนำสุดท้ายเด็ดขาด ให้บอกลูกค้าตรงๆว่า "คำแนะนำนี้อยู่ระหว่างการตรวจสอบ
     จากที่ปรึกษา ยังไม่สามารถยืนยันได้ในขณะนี้" แล้วค่อยตอบคำถามอื่นที่ไม่เกี่ยวกับ
     ตัวเลข/คำแนะนำลงทุนได้ตามปกติ
   - ถ้า compliance_status == "approved" จึงตอบคำแนะนำที่อยู่ใน explanation/
     recommendation ได้ตามปกติ

3. ถ้า session มี ambiguous=true หรือ ready_for_suitability=false หรือ
   missing_critical ไม่ว่าง ให้บอกลูกค้าว่าข้อมูลยังไม่ครบ พร้อมระบุว่าขาดอะไร
   (อ่านจาก clarification_needed / missing_critical) แทนการพยายามตอบคำแนะนำ

4. ทุกครั้งที่มีการพูดถึงคำแนะนำกองทุน/ภาษีที่ "approved" แล้ว ต้องปิดท้ายด้วย:
   "{disclaimer}"

5. ห้ามใช้คำที่สื่อถึงการรับประกันผลตอบแทน หรือ "ไม่มีความเสี่ยง" เด็ดขาด แม้ลูกค้า
   จะถามนำหรือเร่งให้ตอบแบบนั้นก็ตาม

6. ถ้าคำถามอยู่นอกเหนือข้อมูลในระบบโดยสิ้นเชิง (เช่น ถามเรื่องหุ้นต่างประเทศที่ไม่ได้
   อยู่ใน fund catalog) ให้ตอบตามความรู้ทั่วไปได้ แต่ต้องระบุชัดว่าเป็นข้อมูลทั่วไป
   ไม่ใช่คำแนะนำจากการวิเคราะห์ของระบบนี้

7. คงน้ำเสียงเป็นกันเอง กระชับ ไม่ใช้ศัพท์การเงินเกินจำเป็น

Output: ตอบเป็นข้อความธรรมดา (ไม่ใช่ JSON) เป็นภาษาไทย /no_think
""".format(disclaimer=_THAI_DISCLAIMER)


def build_chat_context(session_state: dict) -> dict:
    """Flatten the persisted session state into the compact JSON the chat model
    needs. Surfacing compliance_status as a top-level field keeps rule #2 easy
    for the model to check instead of burying it in a nested object.
    """
    typhoon = session_state.get("typhoon_result") or {}
    client_data = session_state.get("client_data") or {}
    suitability = session_state.get("suitability") or {}
    tax_result = session_state.get("tax_result") or {}
    recommendation = session_state.get("recommendation") or {}
    explanation = session_state.get("explanation") or {}
    compliance = session_state.get("compliance") or {}

    if compliance.get("approved") is True:
        compliance_status = "approved"
    elif session_state.get("status") in ("awaiting_review", "human_review"):
        compliance_status = "awaiting_review"
    elif session_state.get("status") == "non_compliant":
        compliance_status = "non_compliant"
    else:
        compliance_status = "not_yet_reached"

    return {
        "compliance_status": compliance_status,
        "ambiguous": typhoon.get("ambiguous", False),
        "clarification_needed": typhoon.get("clarification_needed"),
        "ready_for_suitability": client_data.get("ready_for_suitability", False),
        "missing_critical": client_data.get("missing_critical", []),
        "client_profile": {
            "age": client_data.get("age"),
            "goal": client_data.get("goal"),
            "risk_profile": client_data.get("risk_profile"),
        },
        "suitability": {
            "investment_horizon": suitability.get("investment_horizon"),
            "recommended_allocation": suitability.get("recommended_allocation"),
            "requires_human_review": suitability.get("requires_human_review", False),
        },
        "tax_result": {
            "tax_before": tax_result.get("tax_before"),
            "tax_after": tax_result.get("tax_after"),
            "saving": tax_result.get("saving"),
        },
        "recommended_funds": recommendation.get("recommended_funds", []),
        "explanation": {
            "overall_explanation": explanation.get("overall_explanation"),
            "explanations": explanation.get("explanations", []),
            "data_gaps": explanation.get("data_gaps", []),
        },
        "compliance_issues": compliance.get("issues", []),
    }


def build_chat_user_prompt(session_context: dict, client_question: str) -> str:
    context_json = json.dumps(session_context, ensure_ascii=False, indent=2)
    return (
        f"session_context:\n{context_json}\n\n"
        f"คำถามจากลูกค้า:\n\"{client_question}\"\n\n"
        "ตอบตามกฎทั้งหมดในระบบพรอมต์ โดยอ้างอิงจาก session_context เท่านั้น"
    )


def synthesize_chat_reply(session_state: dict, client_question: str) -> str:
    """Produce a plain-text Thai reply grounded in the session's context."""
    if not groq_client:
        raise RuntimeError("LLM client is not configured")
    context = build_chat_context(session_state)
    resp = groq_client.chat.completions.create(
        model=settings.LLM_MODEL,
        temperature=0.3,
        messages=[
            {"role": "system", "content": CHAT_SYSTEM_PROMPT},
            {"role": "user", "content": build_chat_user_prompt(context, client_question)},
        ],
    )
    text = resp.choices[0].message.content or ""
    # Strip any Qwen3 <think> reasoning block; chat output must be plain text.
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    return text


# ============================================================================
# CHAT v2 — partial-info-friendly, cross-turn profile accumulation
#
# Fixes the production bug where the chat repeated "ข้อมูลยังไม่ครบ" every turn
# because each turn was evaluated against the frozen pipeline client_data,
# never absorbing facts the client typed into chat. v2 accumulates a
# chat_profile across turns (persisted in state_data by the /chat handler),
# acknowledges what's known, gives qualitative guidance, asks for at most the
# single most useful missing field, and escalates multi-topic life-planning
# requests to a licensed advisor.
# ============================================================================

_CFA_PARTNER_CONTACT = {
    "name": "ทีมที่ปรึกษาการเงินที่มีใบอนุญาต (CFA)",
    # TODO(ship): replace with the real partner channel (Line/phone/email).
    # Left as an explicit placeholder, not invented contact info.
    "contact_method": "<TODO: ใส่ช่องทางติดต่อ partner จริง (Line/เบอร์โทร/อีเมล)>",
}

# Major life-planning topics. Two or more together (in one message OR
# accumulated across turns) signals a request beyond this system's
# tax/fund-deduction scope -> escalate to a licensed advisor.
_MAJOR_LIFE_TOPICS = ["ซื้อบ้าน", "มีลูก", "ประกันชีวิต", "เกษียณ", "หย่า", "มรดก"]

# Critical fields that gate full numeric planning, in priority order: the
# single most useful next question is the first one still missing.
_CRITICAL_FIELDS = ["goal", "monthly_income", "age", "risk_profile"]

_FIELD_LABELS = {
    "age": "อายุ",
    "monthly_income": "รายได้ต่อเดือน",
    "employment_type": "ประเภทอาชีพ",
    "goal": "เป้าหมาย",
    "risk_profile": "ระดับความเสี่ยงที่รับได้",
    "life_events": "เหตุการณ์ชีวิตที่วางแผนไว้ (เช่น มีลูก/ซื้อบ้าน/ซื้อประกัน)",
}


CHAT_SYSTEM_PROMPT_V2 = """\
คุณคือผู้ช่วยวางแผนการเงินเบื้องต้น ตอบเป็นภาษาไทยเท่านั้น พูดเหมือนคนคุยกับลูกค้าจริง
ไม่ใช่บอทที่วนตอบประโยคเดิมซ้ำๆ

ข้อมูลที่มีอยู่ตอนนี้อยู่ใน "known_facts" (สิ่งที่ลูกค้าให้มาแล้วในแชทนี้ทั้งหมด สะสม
จากทุก turn ไม่ใช่แค่ข้อความล่าสุด) และ "missing_fields" (สิ่งที่ยังไม่รู้)

กฎการตอบ (เรียงตามลำดับความสำคัญ):

1. ห้ามตอบ "ข้อมูลยังไม่ครบ" แบบลอยๆซ้ำเดิม — ต้องเริ่มด้วยการสรุปสิ่งที่รู้แล้วแบบ
   เจาะจง (เช่น "จากที่บอกมา: อายุ 20 ปี ฟรีแลนซ์ รายได้ 150,000 บาท/เดือน เป้าหมาย
   คือลดภาษีและสร้างเงินเพิ่ม") เพื่อให้ลูกค้ารู้สึกว่าระบบ "ฟัง" จริง ไม่ใช่เพิกเฉย
   ข้อมูลที่ให้ไปแล้ว

2. ใช้ known_facts ตอบคำแนะนำเชิงคุณภาพแบบทั่วไปได้ทันที แม้ข้อมูลจะยังไม่ครบ 100%
   เช่น ถ้ารู้ว่าเป็นฟรีแลนซ์ + ต้องการลดภาษี ให้อธิบายแนวคิดทั่วไปได้ (เช่น
   ฟรีแลนซ์มีสิทธิ์ลดหย่อนผ่าน SSF/RMF/ประกันชีวิตได้เหมือนพนักงานประจำ) — ห้ามใส่
   ตัวเลขเฉพาะเจาะจง (จำนวนเงินที่ควรซื้อ, ภาษีที่ประหยัดได้) เพราะตัวเลขจริงต้องรอ
   ระบบคำนวณแบบเต็มรูปแบบ (deterministic tax engine) เท่านั้น

3. ถามต่อแค่ "ข้อมูลเดียวที่สำคัญที่สุด" ที่ขาดในตอนนี้ ไม่ใช่ไล่ถามทุกอย่างซ้ำใน
   ทุกข้อความ — เลือกจาก missing_fields ตัวที่ส่งผลต่อคำแนะนำมากที่สุดก่อน

4. Escalation rule — ส่งต่อให้ที่ปรึกษาจริง (CFA partner) เมื่อเข้าเงื่อนไขใดข้อหนึ่ง:
   - คำขอครอบคลุมหลายเรื่องใหญ่พร้อมกันที่ต้องวางแผนเป็นองค์รวม (เช่น มีลูก + ซื้อบ้าน
     + ซื้อประกันชีวิต พร้อมกัน) ซึ่งเกินกว่าที่ระบบนี้ (ออกแบบมาเพื่อภาษี/กองทุนลดหย่อน
     โดยเฉพาะ) จะวิเคราะห์ให้ครบทุกมิติได้
   - ลูกค้าขอคำแนะนำเชิงลึกที่เป็นการวางแผนการเงินส่วนบุคคลแบบครบวงจร ไม่ใช่แค่
     ลดหย่อนภาษี/เลือกกองทุน
   เมื่อ escalate ให้ตอบส่วนที่ระบบช่วยได้ก่อน (ตามกฎ #2) แล้วต่อท้ายด้วยการแนะนำ
   ติดต่อที่ปรึกษา CFA สำหรับส่วนที่ลึกกว่านั้น — ห้ามแนะนำ "ไปหาที่ปรึกษา" แบบลอยๆ
   ไม่มีช่องทาง ให้ใช้ suggested_action ที่ระบบส่งมาให้ (ดู escalate_to_advisor)

5. ถ้า compliance_status != "approved" ห้ามให้ตัวเลข/คำแนะนำกองทุนเป็นคำแนะนำสุดท้าย
   (เหมือนกฎเดิม) แต่ยังคุยเรื่องอื่นและให้คำแนะนำเชิงคุณภาพได้ตามกฎ #2

6. ห้ามใช้คำว่า "การันตี"/"ไม่มีความเสี่ยง" และต้องมี disclaimer ทุกครั้งที่พูดถึง
   คำแนะนำที่ approved แล้ว (เหมือนกฎเดิมของระบบ)

โทนเสียง: เป็นกันเอง ฟังดูเป็นคนจริง ไม่ใช่ template — เขียนประโยคให้หลากหลาย
แม้สถานการณ์จะคล้ายกัน (เช่น "ข้อมูลยังไม่ครบ" ไม่ควรใช้ถ้อยคำเดียวกันทุกครั้ง)

Output: ตอบเป็นข้อความธรรมดา (ไม่ใช่ JSON) เป็นภาษาไทย /no_think
"""


def build_known_facts_summary(accumulated_profile: dict) -> str:
    """Render what the client has told us so far as a short bullet list the
    model can echo back — this is what fixes the "doesn't feel heard"
    complaint. Built on EVERY turn from the accumulated profile."""
    lines = [
        f"- {_FIELD_LABELS.get(k, k)}: {', '.join(v) if isinstance(v, list) else v}"
        for k, v in accumulated_profile.items()
        if v not in (None, "", [])
    ]
    return "\n".join(lines) if lines else "(ยังไม่มีข้อมูลใดๆ)"


def extract_entities_from_message(message: str) -> dict:
    """Pull structured entities from a single chat message by reusing the
    Typhoon interpreter (node 1) — the SAME parser as the main pipeline, so
    chat and pipeline never diverge. Returns {} on any failure (chat must
    degrade gracefully, never 500 because extraction hiccuped)."""
    try:
        result = run_typhoon_interpreter_crew(message)
        return result.entities.model_dump()
    except Exception:
        return {}


def merge_chat_profile(chat_profile: dict, new_entities: dict, message: str) -> dict:
    """Merge newly-extracted entities into the accumulated profile WITHOUT
    discarding previously-known values — the core cross-turn fix. Only
    non-empty new values overwrite; everything else is preserved."""
    out = dict(chat_profile or {})
    for k in ("age", "monthly_income", "employment_type", "goal", "risk_profile"):
        v = (new_entities or {}).get(k)
        if v not in (None, "", []):
            out[k] = v
    topics = [t for t in _MAJOR_LIFE_TOPICS if t in (message or "")]
    if topics:
        out["life_events"] = sorted(set(out.get("life_events") or []) | set(topics))
    return out


def _effective_profile(session_state: dict, chat_profile: dict) -> dict:
    """Combine the accumulated chat profile (highest priority — most recently
    stated) with whatever the pipeline already knew (client_data, then the
    interpreter entities) so known_facts reflects EVERYTHING the client has
    ever told us, across both the form and the chat."""
    client = session_state.get("client_data") or {}
    entities = (session_state.get("typhoon_result") or {}).get("entities") or {}
    cp = chat_profile or {}

    def pick(*vals):
        for v in vals:
            if v not in (None, "", []):
                return v
        return None

    eff = {
        "age": pick(cp.get("age"), client.get("age"), entities.get("age")),
        "monthly_income": pick(cp.get("monthly_income"), client.get("monthly_income"), entities.get("monthly_income")),
        "employment_type": pick(cp.get("employment_type"), entities.get("employment_type")),
        "goal": pick(cp.get("goal"), client.get("goal"), entities.get("goal")),
        "risk_profile": pick(cp.get("risk_profile"), client.get("risk_profile"), entities.get("risk_profile")),
    }
    if cp.get("life_events"):
        eff["life_events"] = cp["life_events"]
    return {k: v for k, v in eff.items() if v not in (None, "", [])}


def _compute_missing_fields(effective: dict) -> list:
    return [f for f in _CRITICAL_FIELDS if effective.get(f) in (None, "", [])]


def should_escalate_to_advisor(client_question: str, accumulated_profile: dict) -> bool:
    """Deterministic check, NOT left to the LLM alone — same philosophy as the
    rest of the pipeline. Two+ major life-planning topics (in this message or
    accumulated across turns) is the clearest signal this exceeds the system's
    tax/fund-recommendation scope."""
    hits = sum(1 for t in _MAJOR_LIFE_TOPICS if t in (client_question or ""))
    accumulated = len(set((accumulated_profile or {}).get("life_events") or []))
    return hits >= 2 or accumulated >= 2


def build_escalate_suggested_action() -> dict:
    return {
        "type": "escalate_to_advisor",
        "label": f"ปรึกษา {_CFA_PARTNER_CONTACT['name']}",
        "contact_method": _CFA_PARTNER_CONTACT["contact_method"],
    }


def _build_chat_user_prompt_v2(session_context: dict, known_facts: str, missing_fields: list, client_question: str) -> str:
    missing_labels = [_FIELD_LABELS.get(f, f) for f in missing_fields]
    context_json = json.dumps(session_context, ensure_ascii=False, indent=2)
    return (
        f"known_facts (สะสมจากทุก turn):\n{known_facts}\n\n"
        f"missing_fields (เรียงตามความสำคัญ มากไปน้อย): "
        f"{', '.join(missing_labels) if missing_labels else '(ครบแล้ว)'}\n\n"
        f"session_context (ผลจาก pipeline ถ้ามี):\n{context_json}\n\n"
        f"คำถามล่าสุดจากลูกค้า:\n\"{client_question}\"\n\n"
        "ตอบตามกฎใน system prompt: เริ่มด้วยสรุปสิ่งที่รู้แบบเจาะจง ให้คำแนะนำเชิงคุณภาพจาก "
        "known_facts (ห้ามใส่ตัวเลขเฉพาะ) แล้วถามต่อแค่ข้อมูลเดียวที่สำคัญที่สุดที่ยังขาด"
    )


def synthesize_chat_reply_v2(session_state: dict, chat_profile: dict, client_question: str) -> str:
    """Partial-info-friendly reply grounded in the accumulated profile."""
    if not groq_client:
        raise RuntimeError("LLM client is not configured")
    effective = _effective_profile(session_state, chat_profile)
    known_facts = build_known_facts_summary(effective)
    missing_fields = _compute_missing_fields(effective)
    context = build_chat_context(session_state)
    resp = groq_client.chat.completions.create(
        model=settings.LLM_MODEL,
        temperature=0.45,
        messages=[
            {"role": "system", "content": CHAT_SYSTEM_PROMPT_V2},
            {"role": "user", "content": _build_chat_user_prompt_v2(context, known_facts, missing_fields, client_question)},
        ],
    )
    text = resp.choices[0].message.content or ""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    return text
