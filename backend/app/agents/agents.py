import json
import re
from typing import Optional, Any

from openai import OpenAI

from backend.app.config import settings
from backend.app.schemas.schemas import (
    ClientIntakeSchema,
    SuitabilitySchema,
    TaxOutputSchema,
    FundRecommendationSchema,
    ExplanationSchema,
    ExplanationDetail,
    ComplianceReportSchema,
    TyphoonOutputSchema,
    TyphoonEntitiesSchema,
)

# ----------------------------------------------------------------------------
# LLM CLIENTS
#
# We bypass CrewAI's structured-output (instructor) layer at runtime. It is
# unreliable with Groq's Qwen models (tool_use_failed) and does not forward
# per-LLM credentials to custom OpenAI-compatible endpoints like Typhoon.
# Instead we call both providers directly via their OpenAI-compatible APIs and
# validate the JSON into our existing Pydantic schemas. The hardcoded mock
# responses remain only as a last-resort fallback if every live call fails.
# ----------------------------------------------------------------------------

GROQ_BASE_URL = "https://api.groq.com/openai/v1"


def is_valid_key(key: Optional[str]) -> bool:
    """A key is usable if present and not an obvious placeholder."""
    return bool(key and key != "mock_key" and key != "mock-key" and not key.startswith("your-"))


groq_client: Optional[OpenAI] = (
    OpenAI(base_url=GROQ_BASE_URL, api_key=settings.GROQ_API_KEY)
    if is_valid_key(settings.GROQ_API_KEY)
    else None
)

typhoon_client: Optional[OpenAI] = (
    OpenAI(base_url=settings.TYPHOON_API_BASE, api_key=settings.TYPHOON_API_KEY)
    if is_valid_key(settings.TYPHOON_API_KEY)
    else None
)


def _log(msg: str) -> None:
    if settings.VERBOSE:
        try:
            print(msg)
        except Exception:
            pass


def _extract_json(text: str) -> dict:
    """Robustly pull a JSON object out of an LLM response.

    Handles Qwen3 <think> blocks, markdown code fences, and leading prose.
    """
    if text is None:
        raise ValueError("Empty LLM response")
    # Strip reasoning blocks emitted by Qwen3 and similar models.
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = text.strip()
    # Strip markdown code fences.
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*", "", text).rsplit("```", 1)[0].strip()
    # Grab the outermost JSON object.
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return json.loads(match.group(0) if match else text)


def _chat_json(
    client: OpenAI,
    model: str,
    system: str,
    user: str,
    use_json_mode: bool = True,
    temperature: float = 0.2,
) -> dict:
    """Call an OpenAI-compatible chat endpoint and return parsed JSON."""
    kwargs: dict = {
        "model": model,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    if use_json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    resp = client.chat.completions.create(**kwargs)
    return _extract_json(resp.choices[0].message.content)


def _groq_json(system: str, user: str, **kw) -> dict:
    if not groq_client:
        raise RuntimeError("Groq client not configured")
    return _chat_json(groq_client, settings.LLM_MODEL, system, user, **kw)


def _maybe_mock(factory):
    """Return a deterministic mock only if explicitly enabled; otherwise raise.

    Keeps mock code available for local testing (USE_MOCK_FALLBACK=true) while
    guaranteeing production never silently serves fabricated data.
    """
    if settings.USE_MOCK_FALLBACK:
        return factory()
    raise RuntimeError(
        "Live LLM call failed and mock fallback is disabled. "
        "Set USE_MOCK_FALLBACK=true for local testing."
    )


# ============================================================================
# 1. TYPHOON INTERPRETER  (Thai -> normalized + English + structured entities)
# ============================================================================

_INTERPRETER_SYSTEM = (
    "You are a Thai financial language interpreter. You understand informal Thai "
    "financial slang (e.g. 'แสนห้า' = 150000, 'โบนัส 3-4 เดือน' = 3.5 months). "
    "Convert raw Thai client text into structured financial data. Never invent "
    "numbers; use null when a value is not stated. "
    "Respond with ONLY a valid JSON object, no markdown, no explanation. /no_think"
)


def _interpreter_user_prompt(raw_input_text: str) -> str:
    return (
        f"Raw Thai client input:\n\"\"\"\n{raw_input_text}\n\"\"\"\n\n"
        "Return a JSON object with exactly these keys:\n"
        "{\n"
        '  "normalized_thai": "cleaned Thai text with numbers normalized",\n'
        '  "english_translation": "formal English financial translation",\n'
        '  "confidence": 0.0-1.0,\n'
        '  "missing_information": ["list of required fields not provided"],\n'
        '  "entities": {\n'
        '     "age": int|null, "monthly_income": float|null, "annual_income": float|null,\n'
        '     "bonus_months": float|null, "rmf": float|null, "ssf": float|null,\n'
        '     "life_insurance": float|null, "goal": string|null,\n'
        '     "risk_profile": "Conservative|Moderate|Aggressive"|null,\n'
        '     "employment_type": "salary|freelance|other"|null\n'
        "  }\n"
        "}\n\n"
        "Rules:\n"
        "- If the input is vague or missing critical data (like income), set confidence BELOW 0.80.\n"
        "- 'อยากลดภาษี' -> goal 'Seeking tax optimization'.\n"
        "- Preserve any explicit demand for guaranteed returns in the translation verbatim."
    )


def _coerce_typhoon(data: dict) -> TyphoonOutputSchema:
    ent = data.get("entities") or {}
    return TyphoonOutputSchema(
        normalized_thai=data.get("normalized_thai", ""),
        english_translation=data.get("english_translation", ""),
        confidence=float(data.get("confidence", 0.0)),
        missing_information=data.get("missing_information") or [],
        entities=TyphoonEntitiesSchema(**{
            k: ent.get(k)
            for k in TyphoonEntitiesSchema.model_fields
            if k in ent
        }),
    )


def run_typhoon_interpreter_crew(raw_input_text: str) -> TyphoonOutputSchema:
    user_prompt = _interpreter_user_prompt(raw_input_text)

    # 1) Preferred: Typhoon (specialized for Thai).
    if typhoon_client:
        try:
            data = _chat_json(
                typhoon_client, settings.TYPHOON_MODEL,
                _INTERPRETER_SYSTEM, user_prompt, use_json_mode=False,
            )
            return _coerce_typhoon(data)
        except Exception as e:
            _log(f"[Typhoon] live call failed, falling back to Groq: {e}")

    # 2) Fallback: Groq (Qwen3 is multilingual and handles Thai well).
    if groq_client:
        try:
            data = _groq_json(_INTERPRETER_SYSTEM, user_prompt)
            return _coerce_typhoon(data)
        except Exception as e:
            _log(f"[Typhoon] Groq fallback failed: {e}")

    return _maybe_mock(lambda: _mock_typhoon(raw_input_text))


# ============================================================================
# 2. CLIENT INTAKE
# ============================================================================

def run_intake_crew(typhoon_data: TyphoonOutputSchema) -> ClientIntakeSchema:
    if groq_client:
        try:
            entities_json = json.dumps(typhoon_data.entities.model_dump(), ensure_ascii=False)
            system = (
                "You map pre-processed financial data into a strict client profile. "
                "Respond with ONLY a valid JSON object. /no_think"
            )
            user = (
                f"Normalized Thai: {typhoon_data.normalized_thai}\n"
                f"English: {typhoon_data.english_translation}\n"
                f"Extracted entities: {entities_json}\n\n"
                "Return JSON with keys: age (int), monthly_income (float), "
                "bonus_months (int), existing_rmf (float), existing_ssf (float), "
                "life_insurance (float), goal (string), "
                "risk_profile ('Conservative'|'Moderate'|'Aggressive').\n"
                "Use these defaults when unknown: age 35, monthly_income 100000, "
                "bonus_months 0, investments 0.0, goal 'Balanced', risk_profile 'Moderate'."
            )
            data = _groq_json(system, user)
            return ClientIntakeSchema(
                age=int(data.get("age") or 35),
                monthly_income=float(data.get("monthly_income") or 100000.0),
                bonus_months=int(data.get("bonus_months") or 0),
                existing_rmf=float(data.get("existing_rmf") or 0.0),
                existing_ssf=float(data.get("existing_ssf") or 0.0),
                life_insurance=float(data.get("life_insurance") or 0.0),
                goal=data.get("goal") or "Balanced",
                risk_profile=data.get("risk_profile") or "Moderate",
            )
        except Exception as e:
            _log(f"[Intake] live call failed: {e}")

    return _maybe_mock(lambda: _mock_intake(typhoon_data))


# ============================================================================
# 3. SUITABILITY
# ============================================================================

def run_suitability_crew(client_data: ClientIntakeSchema) -> SuitabilitySchema:
    if groq_client:
        try:
            system = (
                "You are an investment suitability analyst. "
                "Respond with ONLY a valid JSON object. /no_think"
            )
            user = (
                f"Client: age={client_data.age}, goal={client_data.goal}, "
                f"risk_profile={client_data.risk_profile}.\n\n"
                "Return JSON: {\"risk_profile\": string, \"investment_horizon\": string, "
                "\"recommended_allocation\": {\"Equity\": number, \"Fixed Income\": number}}.\n"
                "Allocation percentages must sum to 100. Younger clients get longer horizons "
                "and more equity; conservative profiles get more fixed income."
            )
            data = _groq_json(system, user)
            alloc = data.get("recommended_allocation") or {}
            alloc = {k: float(v) for k, v in alloc.items()} if alloc else {"Equity": 50.0, "Fixed Income": 50.0}
            return SuitabilitySchema(
                risk_profile=data.get("risk_profile") or client_data.risk_profile,
                investment_horizon=data.get("investment_horizon") or "Medium-Term (5-10 Years)",
                recommended_allocation=alloc,
            )
        except Exception as e:
            _log(f"[Suitability] live call failed: {e}")

    return _maybe_mock(lambda: _mock_suitability(client_data))


# ============================================================================
# 4. EXPLANATION
# ============================================================================

def run_explanation_crew(
    client_data: ClientIntakeSchema,
    tax_data: TaxOutputSchema,
    portfolio_data: FundRecommendationSchema,
) -> ExplanationSchema:
    if not portfolio_data.recommended_funds:
        return ExplanationSchema(
            explanations=[],
            overall_explanation="No additional fund purchases were recommended, so there is nothing further to explain.",
        )

    if groq_client:
        try:
            portfolio_json = json.dumps(
                [f.model_dump() for f in portfolio_data.recommended_funds], ensure_ascii=False
            )
            system = (
                "You are a client-friendly wealth advisor. Explain fund choices clearly "
                "and never promise or guarantee returns. "
                "Respond with ONLY a valid JSON object. /no_think"
            )
            user = (
                f"Client goal: {client_data.goal}\n"
                f"Tax saving: {tax_data.saving:,.2f} THB\n"
                f"Recommended funds: {portfolio_json}\n\n"
                "Return JSON: {\"explanations\": [{\"fund_code\": str, \"why\": str, "
                "\"benefit\": str, \"risk\": str, \"assumptions\": str}], "
                "\"overall_explanation\": str}. One entry per fund_code."
            )
            data = _groq_json(system, user, temperature=0.4)
            explanations = [
                ExplanationDetail(
                    fund_code=item.get("fund_code", ""),
                    why=item.get("why", ""),
                    benefit=item.get("benefit", ""),
                    risk=item.get("risk", ""),
                    assumptions=item.get("assumptions", ""),
                )
                for item in (data.get("explanations") or [])
            ]
            if explanations:
                return ExplanationSchema(
                    explanations=explanations,
                    overall_explanation=data.get("overall_explanation", ""),
                )
        except Exception as e:
            _log(f"[Explanation] live call failed: {e}")

    return _maybe_mock(lambda: _mock_explanation(client_data, tax_data, portfolio_data))


# ============================================================================
# 5. COMPLIANCE AUDIT
# ============================================================================

# Deterministic risk ceilings per profile (also enforced in code as a safety net).
_RISK_CEILING = {"Conservative": 3, "Moderate": 6, "Aggressive": 8}


def _deterministic_risk_violations(
    client_data: ClientIntakeSchema, portfolio_data: FundRecommendationSchema
) -> list:
    """Code-side guarantee that fund risk never exceeds the client's profile."""
    violations = []
    max_allowed = _RISK_CEILING.get(client_data.risk_profile, 6)
    for fund in portfolio_data.recommended_funds:
        if fund.risk_level > max_allowed:
            violations.append(
                f"Risk Level Violation: Recommended fund {fund.fund_code} has risk level "
                f"{fund.risk_level}, exceeding the maximum ({max_allowed}) allowed for a "
                f"{client_data.risk_profile} risk profile."
            )
    return violations


def run_compliance_audit_crew(
    client_data: ClientIntakeSchema,
    tax_data: TaxOutputSchema,
    portfolio_data: FundRecommendationSchema,
    explanation_data: ExplanationSchema,
    client_context: str = "",
) -> ComplianceReportSchema:
    """Audit the recommendation for SEC violations.

    `client_context` is the client's original request/translation. It is essential
    for detecting client-side demands (e.g. guaranteed returns) that are
    deliberately scrubbed from the advisor-facing explanation.
    """
    deterministic = _deterministic_risk_violations(client_data, portfolio_data)

    if groq_client:
        try:
            portfolio_json = json.dumps(
                [f.model_dump() for f in portfolio_data.recommended_funds], ensure_ascii=False
            )
            system = (
                "You are a strict SEC Thailand compliance auditor for mutual fund advice. "
                "Flag any guaranteed-return claims or demands, misleading promises, or "
                "risk-profile mismatches. SEC Thailand strictly prohibits guaranteeing "
                "investment returns; a client DEMANDING guaranteed returns is itself a "
                "violation that must be rejected. Respond with ONLY a valid JSON object. /no_think"
            )
            user = (
                f"Client original request (verbatim): {client_context}\n"
                f"Client: goal={client_data.goal}, risk_profile={client_data.risk_profile}\n"
                f"Advisor explanation: {explanation_data.overall_explanation}\n"
                f"Recommended funds: {portfolio_json}\n\n"
                "Return JSON: {\"status\": \"approved\"|\"rejected\", \"violations\": [str]}.\n"
                "If the client demands or is promised guaranteed/minimum returns, or 'no losses', "
                "status MUST be 'rejected'. If no issues, status 'approved' with empty violations."
            )
            data = _groq_json(system, user)
            violations = list(data.get("violations") or [])
            # Merge deterministic checks the LLM may have missed.
            for v in deterministic:
                if v not in violations:
                    violations.append(v)
            status = "rejected" if violations else (data.get("status") or "approved")
            return ComplianceReportSchema(status=status, violations=violations)
        except Exception as e:
            _log(f"[Compliance] live call failed: {e}")

    return _maybe_mock(
        lambda: _mock_compliance(client_data, tax_data, portfolio_data, explanation_data, client_context)
    )


# ============================================================================
# MOCK FALLBACKS  (last resort only — used when every live provider fails)
# ============================================================================

def _mock_typhoon(raw_input_text: str) -> TyphoonOutputSchema:
    text = raw_input_text.lower()
    if "เงินเดือนประมาณแสนห้า" in text or ("แสนห้า" in text and "ฟรีแลนซ์" not in text):
        entities = TyphoonEntitiesSchema(
            age=None, monthly_income=150000.0, annual_income=2400000.0, bonus_months=4.0,
            rmf=None, ssf=None, life_insurance=None, goal="Seeking tax optimization",
            risk_profile=None, employment_type="salary",
        )
        return TyphoonOutputSchema(
            normalized_thai="เงินเดือนประมาณ 150,000 บาท โบนัสปีละ 4 เดือน ซื้อ RMF เล็กน้อย มีประกันชีวิต วัตถุประสงค์เพื่อลดหย่อนภาษีเพิ่มเติม",
            english_translation="Salary approximately 150,000 THB, annual bonus of 4 months, small RMF investment, existing life insurance. Objective: seeking tax optimization.",
            confidence=0.90,
            missing_information=["age", "existing_rmf", "existing_ssf", "life_insurance"],
            entities=entities,
        )
    elif "ฟรีแลนซ์" in text or "รายได้ไม่แน่นอน" in text:
        entities = TyphoonEntitiesSchema(
            age=None, monthly_income=None, annual_income=None, bonus_months=0.0,
            rmf=None, ssf=None, life_insurance=None, goal="Seeking tax optimization",
            risk_profile=None, employment_type="freelance",
        )
        return TyphoonOutputSchema(
            normalized_thai="รายได้ไม่แน่นอน ประกอบอาชีพฟรีแลนซ์ ปีที่แล้วเสียภาษีจำนวนมาก ต้องการซื้อกองทุน SSF",
            english_translation="Unstable income, freelancer, paid high taxes last year. Seeking SSF tax-saving mutual funds.",
            confidence=0.85,
            missing_information=["age", "monthly_income", "existing_rmf", "existing_ssf", "life_insurance"],
            entities=entities,
        )
    elif "55" in text:
        entities = TyphoonEntitiesSchema(
            age=55, monthly_income=120000.0, annual_income=1440000.0, bonus_months=0.0,
            rmf=0.0, ssf=0.0, life_insurance=0.0,
            goal="Seeking retirement tax optimization", risk_profile="Conservative",
            employment_type="salary",
        )
        return TyphoonOutputSchema(
            normalized_thai="ลูกค้าอายุ 55 ปี รายได้ 120,000 บาทต่อเดือน วัตถุประสงค์เพื่อลดหย่อนภาษี มีความเสี่ยงต่ำ ต้องการรับประกันผลตอบแทนไม่ต่ำกว่า 15%",
            english_translation="Client aged 55 years, monthly income 120,000 THB, seeking retirement tax optimization, low risk tolerance, requests guaranteed returns of at least 15% per year.",
            confidence=0.95,
            missing_information=[],
            entities=entities,
        )
    elif len(raw_input_text) < 15 or "อยากรวย" in text:
        return TyphoonOutputSchema(
            normalized_thai="ข้อมูลสั้นเกินไปหรือไม่ชัดเจน",
            english_translation="Insufficient client information provided",
            confidence=0.50,
            missing_information=["age", "monthly_income"],
            entities=TyphoonEntitiesSchema(),
        )
    else:
        entities = TyphoonEntitiesSchema(
            age=42, monthly_income=180000.0, annual_income=3240000.0, bonus_months=6.0,
            rmf=0.0, ssf=100000.0, life_insurance=50000.0, goal="Balanced",
            risk_profile="Moderate", employment_type="salary",
        )
        return TyphoonOutputSchema(
            normalized_thai="ลูกค้าอายุ 42 ปี รายได้ 180,000 บาทต่อเดือน โบนัส 6 เดือน ซื้อ SSF 100,000 บาท RMF 0 บาท ประกันชีวิต 50,000 บาท ความเสี่ยงระดับปานกลาง",
            english_translation="Client aged 42 years, monthly income 180,000 THB, 6 months bonus, SSF 100,000 THB, RMF 0 THB, life insurance 50,000 THB, moderate risk profile.",
            confidence=0.95,
            missing_information=[],
            entities=entities,
        )


def _mock_intake(typhoon_data: TyphoonOutputSchema) -> ClientIntakeSchema:
    e = typhoon_data.entities
    return ClientIntakeSchema(
        age=e.age if e.age is not None else 35,
        monthly_income=e.monthly_income if e.monthly_income is not None else 100000.0,
        bonus_months=int(e.bonus_months) if e.bonus_months is not None else 0,
        existing_rmf=e.rmf if e.rmf is not None else 0.0,
        existing_ssf=e.ssf if e.ssf is not None else 0.0,
        life_insurance=e.life_insurance if e.life_insurance is not None else 0.0,
        goal=e.goal if e.goal is not None else "Balanced",
        risk_profile=e.risk_profile if e.risk_profile is not None else "Moderate",
    )


def _mock_suitability(client_data: ClientIntakeSchema) -> SuitabilitySchema:
    risk = client_data.risk_profile
    horizon = "Long-Term (10+ Years)" if client_data.age < 50 else "Medium-Term (5-10 Years)"
    allocations = {
        "Conservative": {"Equity": 20.0, "Fixed Income": 80.0},
        "Moderate": {"Equity": 60.0, "Fixed Income": 40.0},
        "Aggressive": {"Equity": 90.0, "Fixed Income": 10.0},
    }
    return SuitabilitySchema(
        risk_profile=risk,
        investment_horizon=horizon,
        recommended_allocation=allocations.get(risk, {"Equity": 50.0, "Fixed Income": 50.0}),
    )


def _mock_explanation(
    client_data: ClientIntakeSchema,
    tax_data: TaxOutputSchema,
    portfolio_data: FundRecommendationSchema,
) -> ExplanationSchema:
    explanations = []
    for fund in portfolio_data.recommended_funds:
        explanations.append(ExplanationDetail(
            fund_code=fund.fund_code,
            why=f"Selected {fund.fund_code} to maximize {fund.fund_type} tax savings under the allowed limits.",
            benefit="Saves up to 30% of investable amount from income tax liability.",
            risk=f"Subject to market volatility associated with a risk level {fund.risk_level} asset class.",
            assumptions="Assumes holding period is maintained for the duration required by Thai regulations (e.g. 5y for ESG, 10y for SSF).",
        ))
    overall = (
        f"Tax optimization successfully reduced your taxable income by utilizing Thai ESG and retirement fund caps, "
        f"generating {tax_data.saving:,.2f} THB in immediate savings. Funds were mapped directly to your risk profile ({client_data.risk_profile})."
    )
    return ExplanationSchema(explanations=explanations, overall_explanation=overall)


def _mock_compliance(
    client_data: ClientIntakeSchema,
    tax_data: TaxOutputSchema,
    portfolio_data: FundRecommendationSchema,
    explanation_data: ExplanationSchema,
    client_context: str = "",
) -> ComplianceReportSchema:
    violations = []
    haystack = " ".join([
        client_context or "",
        explanation_data.overall_explanation or "",
        client_data.risk_profile or "",
    ]).lower()
    if "รับประกัน" in haystack or "guarantee" in haystack or "guaranteed" in haystack:
        violations.append("Guaranteed Returns Violation: The client request demands guaranteed/minimum returns. SEC Thailand regulations strictly prohibit marketing or guaranteeing investment returns on mutual fund products.")
        if client_data.risk_profile == "Conservative":
            violations.append("Risk Profile Mismatch: The client is classified as 'Conservative' risk, but is requesting aggressive guaranteed returns.")
    violations.extend(_deterministic_risk_violations(client_data, portfolio_data))
    status = "rejected" if violations else "approved"
    return ComplianceReportSchema(status=status, violations=violations)
