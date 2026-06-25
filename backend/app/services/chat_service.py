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
from backend.app.agents.agents import groq_client

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
