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
    ComplianceIssue,
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
    retries: int = 1,
) -> dict:
    """Call an OpenAI-compatible chat endpoint and return parsed JSON.

    Retries once on transient errors (network blips, rate limits, malformed
    JSON) so a single hiccup doesn't fail the whole request now that mock
    fallback is off in production.
    """
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
    last_err = None
    for _ in range(retries + 1):
        try:
            resp = client.chat.completions.create(**kwargs)
            return _extract_json(resp.choices[0].message.content)
        except Exception as e:
            last_err = e
    raise last_err


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
    "You are a Thai financial language interpreter. You are an expert at informal "
    "Thai financial slang and Thai number words. Convert raw Thai client text into "
    "structured financial data. Never invent numbers; use null when a value is not "
    "stated.\n\n"
    "Thai number glossary (memorize and apply):\n"
    "- หมื่น = 10,000 ; สามหมื่น = 30,000 ; ห้าหมื่น = 50,000\n"
    "- แสน = 100,000 ; แสนห้า / แสนห้าหมื่น = 150,000 ; แสนสอง = 120,000\n"
    "- สองแสน = 200,000 ; ครึ่งล้าน = 500,000 ; ล้าน = 1,000,000\n"
    "- 'โบนัส 3-4 เดือน' = 3.5 months ; 'โบนัสปีละ 4 เดือน' = bonus_months 4\n\n"
    "Examples:\n"
    "- 'เงินเดือนประมาณแสนห้า' -> monthly_income 150000\n"
    "- 'รายได้ 120,000 ต่อเดือน' -> monthly_income 120000\n"
    "- 'ซื้อ RMF บ้างนิดหน่อย' -> rmf is small/unspecified, use null (not 0)\n\n"
    "Confidence and ambiguity rule (hard gate, not a suggestion):\n"
    "- confidence must reflect how certain you are about BOTH the extracted numbers "
    "AND the client's intent.\n"
    "- If confidence < 0.6, you MUST set ambiguous=true and fill clarification_needed "
    "with the single most important question to ask the client/advisor.\n"
    "- If the text can reasonably be read in more than one way (e.g. unclear whether "
    "an amount is monthly or annual, or the goal is tax-saving vs. growth), set "
    "ambiguous=true even if confidence is otherwise high.\n"
    "- Never resolve genuine ambiguity by silently picking the interpretation that "
    "seems most likely — flag it instead.\n\n"
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
        '  "intent": "high-level client intent, e.g. \'tax_optimization\', \'fund_inquiry\', \'general_question\'",\n'
        '  "ambiguous": true|false,\n'
        '  "clarification_needed": "string or null; required if ambiguous=true",\n'
        '  "entities": {\n'
        '     "age": int|null, "monthly_income": float|null, "annual_income": float|null,\n'
        '     "bonus_months": float|null, "rmf": float|null, "ssf": float|null,\n'
        '     "life_insurance": float|null, "goal": string|null,\n'
        '     "risk_profile": "Conservative|Moderate|Aggressive"|null,\n'
        '     "employment_type": "salary|freelance|other"|null\n'
        "  }\n"
        "}\n\n"
        "Rules:\n"
        "- 'อยากลดภาษี' -> goal 'Seeking tax optimization', intent 'tax_optimization'.\n"
        "- Preserve any explicit demand for guaranteed returns in the translation verbatim.\n"
        "- Apply the confidence/ambiguity hard gate described in the system prompt."
    )


def _coerce_typhoon(data: dict) -> TyphoonOutputSchema:
    ent = data.get("entities") or {}
    confidence = float(data.get("confidence", 0.0))
    ambiguous = bool(data.get("ambiguous", False)) or confidence < 0.6
    return TyphoonOutputSchema(
        normalized_thai=data.get("normalized_thai", ""),
        english_translation=data.get("english_translation", ""),
        confidence=confidence,
        missing_information=data.get("missing_information") or [],
        intent=data.get("intent"),
        ambiguous=ambiguous,
        clarification_needed=data.get("clarification_needed")
        or ("Confidence below 0.6 — please verify the extracted figures with the client." if ambiguous else None),
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
                _INTERPRETER_SYSTEM, user_prompt, use_json_mode=False, temperature=0.0,
            )
            return _coerce_typhoon(data)
        except Exception as e:
            _log(f"[Typhoon] live call failed, falling back to Groq: {e}")

    # 2) Fallback: Groq (Qwen3 is multilingual and handles Thai well).
    if groq_client:
        try:
            data = _groq_json(_INTERPRETER_SYSTEM, user_prompt, temperature=0.0)
            return _coerce_typhoon(data)
        except Exception as e:
            _log(f"[Typhoon] Groq fallback failed: {e}")

    return _maybe_mock(lambda: _mock_typhoon(raw_input_text))


# ============================================================================
# 2. CLIENT INTAKE
# ============================================================================

def run_intake_crew(typhoon_data: TyphoonOutputSchema) -> ClientIntakeSchema:
    data: dict = {}
    if groq_client:
        try:
            entities_json = json.dumps(typhoon_data.entities.model_dump(), ensure_ascii=False)
            system = (
                "You map pre-processed financial data into a client profile. "
                "CRITICAL RULE: never invent a value the client did not state. "
                "If a field is unknown, return null for it — do NOT substitute a "
                "plausible-looking default. Fabricating client data (e.g. assuming "
                "age 35 or income 100000 when unstated) is a compliance violation. "
                "Respond with ONLY a valid JSON object. /no_think"
            )
            user = (
                f"Normalized Thai: {typhoon_data.normalized_thai}\n"
                f"English: {typhoon_data.english_translation}\n"
                f"Extracted entities: {entities_json}\n\n"
                "Return JSON with keys: age (int|null), monthly_income (float|null), "
                "bonus_months (int|null), existing_rmf (float|null), existing_ssf (float|null), "
                "life_insurance (float|null), goal (string|null), "
                "risk_profile ('Conservative'|'Moderate'|'Aggressive'|null).\n"
                "Use null for age, monthly_income, goal, and risk_profile if the client never "
                "stated them. bonus_months/existing_rmf/existing_ssf/life_insurance may be 0 "
                "when the client implies they have none of that (not merely 'unknown')."
            )
            data = _groq_json(system, user)
        except Exception as e:
            _log(f"[Intake] live call failed: {e}")
            return _maybe_mock(lambda: _mock_intake(typhoon_data))
    else:
        return _maybe_mock(lambda: _mock_intake(typhoon_data))

    # Backfill from the extracted entities for any field the intake LLM omitted.
    # entities is the authoritative extraction (and already carries advisor
    # overrides), so this restores known values without ever inventing one.
    e = typhoon_data.entities

    age = data.get("age")
    if age is None:
        age = e.age
    monthly_income = data.get("monthly_income")
    if monthly_income is None:
        monthly_income = e.monthly_income if e.monthly_income is not None else (
            e.annual_income / 12.0 if e.annual_income else None
        )
    goal = data.get("goal") or e.goal
    risk_profile = data.get("risk_profile") or e.risk_profile

    def _num(key: str, fallback) -> float:
        v = data.get(key)
        if v is None:
            v = fallback
        return float(v or 0.0)

    profile = ClientIntakeSchema(
        age=int(age) if age is not None else None,
        monthly_income=float(monthly_income) if monthly_income is not None else None,
        bonus_months=int(data.get("bonus_months") if data.get("bonus_months") is not None else (e.bonus_months or 0)),
        existing_rmf=_num("existing_rmf", e.rmf),
        existing_ssf=_num("existing_ssf", e.ssf),
        life_insurance=_num("life_insurance", e.life_insurance),
        goal=goal,
        risk_profile=risk_profile,
    )
    _apply_intake_sanity_checks(profile)
    return profile


def _apply_intake_sanity_checks(profile: ClientIntakeSchema) -> None:
    """Deterministic (code-side, auditable) sanity checks and gating.

    This is intentionally NOT delegated to the LLM: whether the pipeline is
    allowed to proceed to Suitability must be a reproducible, code-level
    decision, not something an LLM call can flip non-deterministically.
    """
    sanity_flags: list = []
    missing_critical: list = []

    if profile.age is None:
        missing_critical.append("age")
    if profile.monthly_income is None:
        missing_critical.append("monthly_income")
    if profile.goal is None:
        missing_critical.append("goal")
    if profile.risk_profile is None:
        missing_critical.append("risk_profile")

    if profile.age is not None and profile.monthly_income is not None:
        # Minor with adult-level income is an internally inconsistent profile.
        if profile.age < 18 and profile.monthly_income > 50000:
            sanity_flags.append(
                f"Age/income mismatch: stated age {profile.age} with monthly income "
                f"฿{profile.monthly_income:,.2f} is implausible for a minor."
            )
        if profile.age > 100:
            sanity_flags.append(f"Implausible age: {profile.age}.")

    profile.sanity_flags = sanity_flags
    profile.missing_critical = missing_critical
    profile.ready_for_suitability = (len(missing_critical) == 0) and (len(sanity_flags) == 0)


# ============================================================================
# 3. SUITABILITY
# ============================================================================

def run_suitability_crew(client_data: ClientIntakeSchema) -> SuitabilitySchema:
    if groq_client:
        try:
            system = (
                "You are an investment suitability analyst. Allocations must be expressed "
                "as a [min, max] PERCENTAGE RANGE per asset class, never a single point "
                "value — a precise point value implies a guarantee of a specific outcome, "
                "which is not permitted. "
                "Respond with ONLY a valid JSON object. /no_think"
            )
            user = (
                f"Client: age={client_data.age}, goal={client_data.goal}, "
                f"risk_profile={client_data.risk_profile}.\n\n"
                "Return JSON: {\"risk_profile\": string, \"investment_horizon\": string, "
                "\"recommended_allocation\": {\"Equity\": [min, max], \"Fixed Income\": [min, max]}, "
                "\"requires_human_review\": bool, \"review_reason\": string|null}.\n"
                "Each [min,max] range's midpoints across asset classes should roughly sum to 100. "
                "Younger clients get longer horizons and more equity; conservative profiles get "
                "more fixed income.\n"
                "Set requires_human_review=true if the client's stated risk_profile conflicts with "
                "their age/likely time horizon (e.g. 'Aggressive' at an age typically associated "
                "with a short horizon), and explain why in review_reason."
            )
            data = _groq_json(system, user)
            alloc_raw = data.get("recommended_allocation") or {}
            alloc = {k: [float(v[0]), float(v[1])] for k, v in alloc_raw.items()} if alloc_raw else {
                "Equity": [40.0, 60.0], "Fixed Income": [40.0, 60.0]
            }
            suitability = SuitabilitySchema(
                risk_profile=data.get("risk_profile") or client_data.risk_profile,
                investment_horizon=data.get("investment_horizon") or "Medium-Term (5-10 Years)",
                recommended_allocation=alloc,
                requires_human_review=bool(data.get("requires_human_review", False)),
                review_reason=data.get("review_reason"),
            )
            _apply_suitability_sanity_check(client_data, suitability)
            return suitability
        except Exception as e:
            _log(f"[Suitability] live call failed: {e}")

    return _maybe_mock(lambda: _mock_suitability(client_data))


def _apply_suitability_sanity_check(client_data: ClientIntakeSchema, suitability: SuitabilitySchema) -> None:
    """Deterministic backstop: don't trust the LLM alone to flag risk/age conflicts."""
    if suitability.requires_human_review:
        return
    age = client_data.age
    if age is not None and suitability.risk_profile == "Aggressive" and age >= 60:
        suitability.requires_human_review = True
        suitability.review_reason = (
            f"Client age {age} with 'Aggressive' risk profile — short likely time horizon "
            "conflicts with an aggressive allocation. Requires advisor confirmation."
        )


# ============================================================================
# 4. EXPLANATION
# ============================================================================

_THAI_DISCLAIMER = "คำแนะนำนี้รอการตรวจสอบจากที่ปรึกษาที่มีใบอนุญาตก่อนนำไปใช้จริง"


def run_explanation_crew(
    client_data: ClientIntakeSchema,
    tax_data: TaxOutputSchema,
    portfolio_data: FundRecommendationSchema,
) -> ExplanationSchema:
    if not portfolio_data.recommended_funds:
        return ExplanationSchema(
            explanations=[],
            overall_explanation=f"ไม่มีกองทุนเพิ่มเติมที่แนะนำในรอบนี้ {_THAI_DISCLAIMER}",
            disclaimer_included=True,
        )

    if groq_client:
        try:
            portfolio_json = json.dumps(
                [f.model_dump() for f in portfolio_data.recommended_funds], ensure_ascii=False
            )
            valid_fund_codes = {f.fund_code for f in portfolio_data.recommended_funds}
            system = (
                "คุณคือที่ปรึกษาความมั่งคั่งที่อธิบายให้ลูกค้าฟังง่าย ใช้ภาษาไทยล้วนเท่านั้น "
                "ห้ามรับประกันหรือสื่อถึงการการันตีผลตอบแทนเด็ดขาด ห้ามใส่ตัวเลขที่ไม่ได้มาจากข้อมูลที่ให้มา "
                "(ถ้าต้องใช้ตัวเลขที่ไม่มีให้ระบุใน data_gaps แทนการประมาณเอง) "
                "ตอบเป็น JSON เท่านั้น ห้ามมี markdown หรือคำอธิบายอื่นปน /no_think"
            )
            user = (
                f"Client goal: {client_data.goal}\n"
                f"Tax saving: {tax_data.saving:,.2f} THB\n"
                f"Recommended funds: {portfolio_json}\n\n"
                "Return JSON: {\"explanations\": [{\"fund_code\": str, \"why\": str (ภาษาไทย), "
                "\"benefit\": str (ภาษาไทย), \"risk\": str (ภาษาไทย), \"assumptions\": str (ภาษาไทย)}], "
                "\"overall_explanation\": str (ภาษาไทย, สรุปทั้งเหตุผลและความเสี่ยงคู่กัน), "
                "\"data_gaps\": [str], \"flag_for_compliance\": bool}.\n"
                "fund_code ต้องตรงกับที่ให้มาเท่านั้น ห้ามสร้างกองทุนใหม่ขึ้นมา\n"
                "One entry per fund_code."
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
                data_gaps = list(data.get("data_gaps") or [])
                flag_for_compliance = bool(data.get("flag_for_compliance", False))

                # Deterministic backstop: catch fund codes the model hallucinated
                # that don't exist in the actual recommended portfolio.
                for exp in explanations:
                    if exp.fund_code not in valid_fund_codes:
                        flag_for_compliance = True
                        data_gaps.append(
                            f"Explanation references fund_code '{exp.fund_code}' which is not "
                            f"in the recommended portfolio ({sorted(valid_fund_codes)})."
                        )

                overall = data.get("overall_explanation", "").strip()
                disclaimer_included = _THAI_DISCLAIMER in overall
                if not disclaimer_included:
                    # The disclaimer is mandatory — never optional, never left to the LLM
                    # to remember. Append it deterministically if missing.
                    overall = f"{overall}\n\n{_THAI_DISCLAIMER}" if overall else _THAI_DISCLAIMER
                    disclaimer_included = True

                return ExplanationSchema(
                    explanations=explanations,
                    overall_explanation=overall,
                    data_gaps=data_gaps,
                    flag_for_compliance=flag_for_compliance,
                    disclaimer_included=disclaimer_included,
                )
        except Exception as e:
            _log(f"[Explanation] live call failed: {e}")

    return _maybe_mock(lambda: _mock_explanation(client_data, tax_data, portfolio_data))


# ============================================================================
# 5. COMPLIANCE AUDIT
# ============================================================================

# Deterministic risk ceilings per profile (also enforced in code as a safety net).
_RISK_CEILING = {"Conservative": 3, "Moderate": 6, "Aggressive": 8}


def _deterministic_compliance_issues(
    client_data: ClientIntakeSchema,
    portfolio_data: FundRecommendationSchema,
    explanation_data: ExplanationSchema,
) -> list:
    """Code-side compliance checks that must never depend on an LLM call.

    Covers: (a) fund risk exceeding the client's risk ceiling, (b) the
    mandatory Thai disclaimer being missing, (c) explanation referencing a
    fund_code that isn't actually in the recommended portfolio (unsourced /
    hallucinated numbers).
    """
    issues: list = []
    max_allowed = _RISK_CEILING.get(client_data.risk_profile, 6)
    for fund in portfolio_data.recommended_funds:
        if fund.risk_level > max_allowed:
            issues.append(ComplianceIssue(
                severity="critical",
                location=f"recommendation.recommended_funds[{fund.fund_code}].risk_level",
                description=(
                    f"Fund {fund.fund_code} has risk level {fund.risk_level}, exceeding the "
                    f"maximum ({max_allowed}) allowed for a {client_data.risk_profile} risk profile."
                ),
                route_back_to="node_5_fund_recommender",
            ))

    if not explanation_data.disclaimer_included:
        issues.append(ComplianceIssue(
            severity="critical",
            location="explanation.disclaimer_included",
            description="Mandatory advisor-review disclaimer is missing from the client-facing explanation.",
            route_back_to="node_6_explanation",
        ))

    valid_fund_codes = {f.fund_code for f in portfolio_data.recommended_funds}
    for exp in explanation_data.explanations:
        if exp.fund_code not in valid_fund_codes:
            # Warning, not critical: the displayed fund_code is derived from the
            # fund name, so a label mismatch is a data-provenance note for review —
            # not a regulatory violation that should reject the whole recommendation.
            issues.append(ComplianceIssue(
                severity="warning",
                location=f"explanation.explanations[{exp.fund_code}]",
                description=f"Explanation references fund_code '{exp.fund_code}' with no matching entry in the recommended portfolio (verify labeling).",
                route_back_to="node_6_explanation",
            ))

    if explanation_data.flag_for_compliance:
        issues.append(ComplianceIssue(
            severity="warning",
            location="explanation.flag_for_compliance",
            description="Explanation agent self-flagged a possible inconsistency for compliance review.",
            route_back_to="node_6_explanation",
        ))

    return issues


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

    This agent AUDITS only — it never edits prior node output. Every rejection
    carries a route_back_to pointing at the upstream node responsible, so the
    workflow can route there for a fix instead of silently dropping the
    recommendation.
    """
    deterministic_issues = _deterministic_compliance_issues(client_data, portfolio_data, explanation_data)

    if groq_client:
        try:
            portfolio_json = json.dumps(
                [f.model_dump() for f in portfolio_data.recommended_funds], ensure_ascii=False
            )
            system = (
                "You are a strict SEC Thailand compliance auditor for mutual fund advice. "
                "You AUDIT ONLY — you never rewrite or fix content yourself. "
                "Flag any guaranteed-return claims or demands, misleading promises, "
                "risk-profile mismatches, or numbers not traceable to the supplied data. "
                "SEC Thailand strictly prohibits guaranteeing investment returns; a client "
                "DEMANDING guaranteed returns is itself a violation that must be rejected. "
                "Respond with ONLY a valid JSON object. /no_think"
            )
            user = (
                f"Client original request (verbatim): {client_context}\n"
                f"Client: goal={client_data.goal}, risk_profile={client_data.risk_profile}\n"
                f"Advisor explanation: {explanation_data.overall_explanation}\n"
                f"Recommended funds: {portfolio_json}\n\n"
                "Return JSON: {\"approved\": bool, \"issues\": [{\"severity\": \"critical\"|\"warning\", "
                "\"location\": str, \"description\": str, \"route_back_to\": str|null}], "
                "\"compliance_notes\": str}.\n"
                "If the client demands or is promised guaranteed/minimum returns, or 'no losses', "
                "approved MUST be false and you must add a critical issue with "
                "route_back_to='node_6_explanation' (or 'node_3_suitability' if the mismatch is "
                "about risk profile itself). If no issues, approved=true with an empty issues list."
            )
            data = _groq_json(system, user)
            llm_issues = [
                ComplianceIssue(
                    severity=item.get("severity", "warning"),
                    location=item.get("location", ""),
                    description=item.get("description", ""),
                    route_back_to=item.get("route_back_to"),
                )
                for item in (data.get("issues") or [])
            ]
            all_issues = llm_issues + deterministic_issues
            # approved is derived solely from issue severity, per the schema's
            # contract ("True only if there are zero critical-severity issues") —
            # never trusted directly from the LLM's own approved/rejected guess,
            # which could disagree with its own issues list.
            approved = not any(i.severity == "critical" for i in all_issues)
            return ComplianceReportSchema(
                approved=approved,
                issues=all_issues,
                compliance_notes=data.get("compliance_notes", ""),
            )
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
            intent=None,
            ambiguous=True,
            clarification_needed="ลูกค้าให้ข้อมูลน้อยเกินไป ต้องสอบถามอายุ รายได้ และเป้าหมายการลงทุนเพิ่มเติม",
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
    profile = ClientIntakeSchema(
        age=e.age,
        monthly_income=e.monthly_income,
        bonus_months=int(e.bonus_months) if e.bonus_months is not None else 0,
        existing_rmf=e.rmf if e.rmf is not None else 0.0,
        existing_ssf=e.ssf if e.ssf is not None else 0.0,
        life_insurance=e.life_insurance if e.life_insurance is not None else 0.0,
        goal=e.goal,
        risk_profile=e.risk_profile,
    )
    _apply_intake_sanity_checks(profile)
    return profile


def _mock_suitability(client_data: ClientIntakeSchema) -> SuitabilitySchema:
    risk = client_data.risk_profile or "Moderate"
    age = client_data.age if client_data.age is not None else 35
    horizon = "Long-Term (10+ Years)" if age < 50 else "Medium-Term (5-10 Years)"
    allocations = {
        "Conservative": {"Equity": [10.0, 30.0], "Fixed Income": [70.0, 90.0]},
        "Moderate": {"Equity": [50.0, 70.0], "Fixed Income": [30.0, 50.0]},
        "Aggressive": {"Equity": [80.0, 100.0], "Fixed Income": [0.0, 20.0]},
    }
    suitability = SuitabilitySchema(
        risk_profile=risk,
        investment_horizon=horizon,
        recommended_allocation=allocations.get(risk, {"Equity": [40.0, 60.0], "Fixed Income": [40.0, 60.0]}),
    )
    _apply_suitability_sanity_check(client_data, suitability)
    return suitability


def _mock_explanation(
    client_data: ClientIntakeSchema,
    tax_data: TaxOutputSchema,
    portfolio_data: FundRecommendationSchema,
) -> ExplanationSchema:
    explanations = []
    for fund in portfolio_data.recommended_funds:
        explanations.append(ExplanationDetail(
            fund_code=fund.fund_code,
            why=f"เลือก {fund.fund_code} เพื่อใช้สิทธิลดหย่อนภาษีประเภท {fund.fund_type} ภายในวงเงินที่กำหนด",
            benefit="ช่วยลดภาระภาษีเงินได้จากเงินลงทุนตามสิทธิที่กฎหมายอนุญาต",
            risk=f"มีความผันผวนตามระดับความเสี่ยง {fund.risk_level} ของสินทรัพย์ประเภทนี้",
            assumptions="สมมติว่าถือครองตามระยะเวลาที่กฎหมายกำหนด (เช่น 5 ปีสำหรับ ESG, 10 ปีสำหรับ SSF)",
        ))
    overall = (
        f"การวางแผนภาษีช่วยลดภาระภาษีได้ประมาณ {tax_data.saving:,.2f} บาท โดยเลือกกองทุนให้สอดคล้องกับ "
        f"ระดับความเสี่ยงของลูกค้า ({client_data.risk_profile or 'ไม่ระบุ'})\n\n{_THAI_DISCLAIMER}"
    )
    return ExplanationSchema(
        explanations=explanations,
        overall_explanation=overall,
        disclaimer_included=True,
    )


def _mock_compliance(
    client_data: ClientIntakeSchema,
    tax_data: TaxOutputSchema,
    portfolio_data: FundRecommendationSchema,
    explanation_data: ExplanationSchema,
    client_context: str = "",
) -> ComplianceReportSchema:
    issues = []
    haystack = " ".join([
        client_context or "",
        explanation_data.overall_explanation or "",
        client_data.risk_profile or "",
    ]).lower()
    if "รับประกัน" in haystack or "guarantee" in haystack or "guaranteed" in haystack:
        issues.append(ComplianceIssue(
            severity="critical",
            location="client_context",
            description=(
                "Client demands guaranteed/minimum returns. SEC Thailand regulations strictly "
                "prohibit marketing or guaranteeing investment returns on mutual fund products."
            ),
            route_back_to="node_6_explanation",
        ))
        if client_data.risk_profile == "Conservative":
            issues.append(ComplianceIssue(
                severity="critical",
                location="client_data.risk_profile",
                description="Client is classified 'Conservative' risk but is requesting aggressive guaranteed returns.",
                route_back_to="node_3_suitability",
            ))
    issues.extend(_deterministic_compliance_issues(client_data, portfolio_data, explanation_data))
    approved = not any(i.severity == "critical" for i in issues)
    return ComplianceReportSchema(approved=approved, issues=issues, compliance_notes="")
