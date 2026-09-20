from fastapi import APIRouter, HTTPException

from app.models.soh import SohRequest, SohResponse
from app.services import soh_estimator

router = APIRouter()


@router.post("/estimate", response_model=SohResponse)
def estimate(req: SohRequest):
    try:
        soh = soh_estimator.predict_soh(
            age_months=req.age_months,
            mileage_km=req.mileage_km,
            fast_charge_pct=req.fast_charge_pct,
            climate_zone=req.climate_zone,
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="SOH model artifact not found. Run ml/train_soh_model.py first.",
        )

    return SohResponse(
        estimated_soh_pct=round(soh, 2),
        model_type="RandomForestRegressor (scikit-learn, trained on synthetic data)",
        note=(
            "Estimated from a simplified model trained on SYNTHETIC data as an MVP "
            "stand-in — see ml/generate_synthetic_data.py. Not a substitute for a "
            "real BMS/diagnostic reading."
        ),
    )


@router.get("/explain")
def explain(
    age_months: float,
    mileage_km: float,
    fast_charge_pct: float,
    climate_zone: str,
):
    """Stub endpoint for future SHAP-based explainability — see soh_estimator.explain_soh()."""
    return soh_estimator.explain_soh(age_months, mileage_km, fast_charge_pct, climate_zone)
