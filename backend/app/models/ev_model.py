from pydantic import BaseModel


class EVModel(BaseModel):
    id: str
    make: str
    model: str
    body_type: str
    price_inr: float
    battery_kwh: float
    range_km: float
    charging_speed_kw: float
    fast_charge_10_80_min: float
    warranty_years: float
    warranty_km: float
