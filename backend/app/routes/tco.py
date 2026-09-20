from fastapi import APIRouter, HTTPException

from app.models.tco import TcoBreakdown, TcoRequest
from app.services import ev_catalog, tco_calculator

router = APIRouter()


@router.post("/calculate", response_model=TcoBreakdown)
def calculate(req: TcoRequest):
    model = ev_catalog.get_ev_model(req.model_id)
    if model is None:
        raise HTTPException(status_code=404, detail=f"EV model '{req.model_id}' not found")

    result = tco_calculator.calculate_tco(
        model=model,
        annual_km=req.annual_km,
        state=req.state,
        payment_mode=req.payment_mode,
        ownership_years=req.ownership_years,
    )
    return result
