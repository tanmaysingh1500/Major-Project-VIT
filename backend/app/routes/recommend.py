from fastapi import APIRouter

from app.models.recommend import RecommendRequest, RecommendResponse
from app.services import recommend as recommend_service

router = APIRouter()


@router.post("/", response_model=RecommendResponse)
def recommend(req: RecommendRequest):
    results = recommend_service.generate_recommendations(
        budget_inr=req.budget_inr,
        daily_km=req.daily_km,
        state=req.state,
        payment_mode=req.payment_mode,
        ownership_years=req.ownership_years,
        assumed_climate_zone=req.assumed_climate_zone,
        assumed_fast_charge_pct=req.assumed_fast_charge_pct,
        weights=req.weights,
    )
    return {"weights_used": req.weights, "results": results}
