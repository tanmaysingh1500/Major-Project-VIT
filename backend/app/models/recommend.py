from typing import Literal

from pydantic import BaseModel, Field


class RecommendWeights(BaseModel):
    """Weights must be non-negative; they're normalized internally so they
    don't need to sum to 1 — the frontend sliders can be intuitive 0-100."""
    cost: float = Field(default=40, ge=0)
    range: float = Field(default=25, ge=0)
    battery_health: float = Field(default=20, ge=0)
    charging_speed: float = Field(default=15, ge=0)


class RecommendRequest(BaseModel):
    budget_inr: float = Field(gt=0)
    daily_km: float = Field(gt=0)
    state: str
    payment_mode: Literal["cash", "loan"] = "cash"
    ownership_years: int = Field(default=5, gt=0, le=20)
    # Assume a representative usage profile for the SOH-adjusted resale note,
    # since the recommendation view doesn't collect full SOH inputs.
    assumed_climate_zone: Literal["hot", "temperate", "cold"] = "temperate"
    assumed_fast_charge_pct: float = Field(default=20, ge=0, le=100)
    weights: RecommendWeights = Field(default_factory=RecommendWeights)


class RecommendedModel(BaseModel):
    model_id: str
    make: str
    model: str
    within_budget: bool
    score: float
    tco: dict
    projected_soh_pct: float
    soh_adjusted_resale_note: str


class RecommendResponse(BaseModel):
    weights_used: RecommendWeights
    results: list[RecommendedModel]
