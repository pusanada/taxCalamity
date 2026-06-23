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


class ClientIntakeSchema(BaseModel):
    age: int = Field(..., ge=0, description="Age of the client")
    monthly_income: float = Field(..., ge=0, description="Monthly assessable basic income in THB")
    bonus_months: int = Field(default=0, ge=0, description="Number of months of bonus")
    existing_rmf: float = Field(default=0.0, ge=0, description="Existing RMF investment in THB")
    existing_ssf: float = Field(default=0.0, ge=0, description="Existing SSF investment in THB")
    life_insurance: float = Field(default=0.0, ge=0, description="Existing life insurance premium in THB")
    goal: str = Field(default="Balanced", description="Goal: Growth, Dividend, Balanced")
    risk_profile: str = Field(default="Moderate", description="Risk profile: Conservative, Moderate, Aggressive")


class SuitabilitySchema(BaseModel):
    risk_profile: str = Field(..., description="Determined risk tolerance profile: Conservative, Moderate, Aggressive")
    investment_horizon: str = Field(..., description="Calculated suitable investment duration based on age and goals")
    recommended_allocation: Dict[str, float] = Field(..., description="E.g. {'Equity': 60, 'Fixed Income': 40}")


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


class ComplianceReportSchema(BaseModel):
    status: str = Field(..., description="approved or rejected")
    violations: List[str] = Field(default_factory=list, description="Compliance violations flagged")


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
