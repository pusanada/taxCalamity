from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class TyphoonEntitiesSchema(BaseModel):
    age: Optional[int] = Field(default=None, description="Age of client")
    monthly_income: Optional[float] = Field(default=None, description="Monthly basic income in THB")
    annual_income: Optional[float] = Field(default=None, description="Annual income in THB")
    bonus_months: Optional[float] = Field(default=None, description="Number of months of bonus")
    rmf: Optional[float] = Field(default=None, description="Existing RMF investment in THB")
    ssf: Optional[float] = Field(default=None, description="Existing SSF investment in THB")
    life_insurance: Optional[float] = Field(default=None, description="Existing life insurance premium in THB")
    goal: Optional[str] = Field(default=None, description="Goal details")
    risk_profile: Optional[str] = Field(default=None, description="Risk profile")
    employment_type: Optional[str] = Field(default=None, description="Employment type (salary, freelance, etc.)")


class TyphoonOutputSchema(BaseModel):
    normalized_thai: str = Field(..., description="Normalized Thai text")
    english_translation: str = Field(..., description="Standard professional financial English translation")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence level of the extraction (0.0 to 1.0)")
    missing_information: List[str] = Field(default_factory=list, description="List of required but missing fields")
    entities: TyphoonEntitiesSchema = Field(..., description="Extracted entities")
    intent: Optional[str] = Field(default=None, description="High-level client intent, e.g. 'tax_optimization', 'fund_inquiry'")
    ambiguous: bool = Field(default=False, description="True if confidence < 0.6 or the request can be read multiple ways")
    clarification_needed: Optional[str] = Field(default=None, description="What to ask the client/advisor when ambiguous=True")


class ClientIntakeSchema(BaseModel):
    # NOTE: age, monthly_income, goal, and risk_profile are the four fields the
    # audit flagged as being silently fabricated (age->35, income->100000,
    # goal->'Balanced', risk_profile->'Moderate'). They are now Optional and
    # left as None when the client never stated them — the pipeline must not
    # invent client data. bonus/rmf/ssf/life_insurance keep a 0.0 default
    # because "no bonus / no existing investment" is a meaningful, non-invented
    # default, not a guess about an unstated fact.
    age: Optional[int] = Field(default=None, ge=0, description="Age of the client; null if not stated")
    monthly_income: Optional[float] = Field(default=None, ge=0, description="Monthly assessable basic income in THB; null if not stated")
    bonus_months: int = Field(default=0, ge=0, description="Number of months of bonus")
    existing_rmf: float = Field(default=0.0, ge=0, description="Existing RMF investment in THB")
    existing_ssf: float = Field(default=0.0, ge=0, description="Existing SSF investment in THB")
    life_insurance: float = Field(default=0.0, ge=0, description="Existing life insurance premium in THB")
    goal: Optional[str] = Field(default=None, description="Goal: Growth, Dividend, Balanced; null if not stated")
    risk_profile: Optional[str] = Field(default=None, description="Risk profile: Conservative, Moderate, Aggressive; null if not stated")
    sanity_flags: List[str] = Field(default_factory=list, description="Internally-inconsistent data detected during intake, e.g. age vs income mismatch")
    missing_critical: List[str] = Field(default_factory=list, description="Critical fields still missing after intake (age, monthly_income, goal)")
    ready_for_suitability: bool = Field(default=False, description="True only if no missing_critical fields and no critical sanity_flags")


class SuitabilitySchema(BaseModel):
    risk_profile: str = Field(..., description="Determined risk tolerance profile: Conservative, Moderate, Aggressive")
    investment_horizon: str = Field(..., description="Calculated suitable investment duration based on age and goals")
    recommended_allocation: Dict[str, List[float]] = Field(
        ..., description="Allocation as a [min, max] range per asset class, e.g. {'Equity': [50, 70], 'Fixed Income': [30, 50]} — never a single point value, to avoid implying a guaranteed/precise outcome."
    )
    requires_human_review: bool = Field(default=False, description="True if the client's stated risk tolerance conflicts with age/time horizon")
    review_reason: Optional[str] = Field(default=None, description="Why human review is required, when requires_human_review=True")


class TaxOutputSchema(BaseModel):
    tax_before: float
    tax_after: float
    saving: float
    detailed_calculations: Dict[str, Any] = Field(default_factory=dict)


class FundDetail(BaseModel):
    fund_code: str
    fund_name: str
    fund_type: str
    amount_thb: float
    allocation_percentage: float
    risk_level: int
    expense_ratio: float
    reason: str


class FundRecommendationSchema(BaseModel):
    recommended_funds: List[FundDetail] = Field(default_factory=list)


class ExplanationDetail(BaseModel):
    fund_code: str = Field(..., description="Ticker/Symbol of the mutual fund")
    why: str = Field(..., description="Why this fund was selected")
    benefit: str = Field(..., description="Benefit of this investment")
    risk: str = Field(..., description="Risk of this specific fund")
    assumptions: str = Field(..., description="Assumptions made for this projection")


class ExplanationSchema(BaseModel):
    explanations: List[ExplanationDetail] = Field(default_factory=list, description="Detailed explanation for each recommended fund")
    overall_explanation: str = Field(..., description="Overall summary of the tax optimization and fund selection logic")
    data_gaps: List[str] = Field(default_factory=list, description="Numbers the explanation could not source from upstream JSON and therefore omitted")
    flag_for_compliance: bool = Field(default=False, description="True if the explanation content looks inconsistent with tax/allocation data and needs Compliance Auditor attention")
    disclaimer_included: bool = Field(default=False, description="True once the mandatory Thai advisor-review disclaimer has been appended")


class ComplianceIssue(BaseModel):
    severity: str = Field(..., description="'critical' or 'warning'")
    location: str = Field(..., description="Pointer to the offending field, e.g. 'explanation.benefit_summary[1]'")
    description: str = Field(..., description="What is wrong")
    route_back_to: Optional[str] = Field(default=None, description="Which upstream node should fix this, e.g. 'node_6_explanation'")


class ComplianceReportSchema(BaseModel):
    approved: bool = Field(..., description="True only if there are zero critical-severity issues")
    issues: List[ComplianceIssue] = Field(default_factory=list, description="Structured compliance findings; empty when approved")
    compliance_notes: str = Field(default="", description="Free-text auditor summary")


class AdvisoryWorkflowRequest(BaseModel):
    raw_input_text: str = Field(..., min_length=1, description="Raw conversational transcript of client details")
    session_id: Optional[str] = Field(default=None, description="Optional session tracker")
    overrides: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Advisor-provided authoritative profile values (e.g. {'rmf': 0}) merged into extracted entities, bypassing LLM re-extraction."
    )


class AdvisoryWorkflowResponse(BaseModel):
    session_id: str
    typhoon_result: Optional[TyphoonOutputSchema] = None
    client_data: Optional[ClientIntakeSchema] = None
    suitability: Optional[SuitabilitySchema] = None
    tax_result: Optional[TaxOutputSchema] = None
    recommendation: Optional[FundRecommendationSchema] = None
    explanation: Optional[ExplanationSchema] = None
    compliance: Optional[ComplianceReportSchema] = None
    status: str
    trace: List[str] = Field(default_factory=list)
