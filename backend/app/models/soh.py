from typing import Literal

from pydantic import BaseModel, Field


class SohRequest(BaseModel):
    age_months: float = Field(ge=0, le=240, description="Vehicle age in months")
    mileage_km: float = Field(ge=0, description="Total odometer reading in km")
    fast_charge_pct: float = Field(ge=0, le=100, description="% of charges that are DC fast-charging")
    climate_zone: Literal["hot", "temperate", "cold"]


class SohResponse(BaseModel):
    estimated_soh_pct: float
    model_type: str
    is_illustrative: bool = True
    note: str
