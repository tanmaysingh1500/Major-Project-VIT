from typing import Literal

from pydantic import BaseModel, Field


class TcoRequest(BaseModel):
    model_id: str
    annual_km: float = Field(gt=0, description="Estimated km driven per year")
    state: str = Field(description="Indian state, used to look up state subsidy")
    payment_mode: Literal["cash", "loan"] = "cash"
    ownership_years: int = Field(gt=0, le=20, description="Years of ownership to project")


class LoanBreakdown(BaseModel):
    down_payment_inr: float
    principal_inr: float
    monthly_emi_inr: float
    total_interest_inr: float
    total_paid_inr: float


class TcoBreakdown(BaseModel):
    model_id: str
    base_price_inr: float
    central_subsidy_inr: float
    state_subsidy_inr: float
    total_subsidy_inr: float
    effective_purchase_price_inr: float
    running_cost_annual_inr: float
    running_cost_total_inr: float
    maintenance_cost_annual_inr: float
    maintenance_cost_total_inr: float
    insurance_cost_total_inr: float
    loan: LoanBreakdown | None
    resale_value_inr: float
    total_cost_of_ownership_inr: float
    ownership_years: int
    assumptions_used: dict
