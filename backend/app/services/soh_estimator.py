"""
Battery State-of-Health (SOH) estimation service.

Loads the scikit-learn pipeline trained by ml/train_soh_model.py and exposes
a simple predict() function. No LLM is involved in producing the numeric
estimate — it comes entirely from the trained regression model, consistent
with the project's "numbers are computed, not hallucinated" principle.
"""

from functools import lru_cache

import joblib
import pandas as pd

from app.config import SOH_MODEL_PATH

FEATURE_COLUMNS = ["age_months", "mileage_km", "fast_charge_pct", "climate_zone"]


@lru_cache(maxsize=1)
def _load_model():
    return joblib.load(SOH_MODEL_PATH)


def predict_soh(age_months: float, mileage_km: float, fast_charge_pct: float, climate_zone: str) -> float:
    model = _load_model()
    row = pd.DataFrame(
        [{
            "age_months": age_months,
            "mileage_km": mileage_km,
            "fast_charge_pct": fast_charge_pct,
            "climate_zone": climate_zone,
        }],
        columns=FEATURE_COLUMNS,
    )
    prediction = model.predict(row)[0]
    # Clamp to a sane physical range for display purposes.
    return float(max(0.0, min(100.0, prediction)))


def explain_soh(age_months: float, mileage_km: float, fast_charge_pct: float, climate_zone: str) -> dict:
    """
    STUB — full XAI explainability (per the FF-180 synopsis) is a 'Later' item.

    TODO(SHAP integration): Replace this stub with a real SHAP explainer, e.g.:

        import shap
        model = _load_model()
        # RandomForestRegressor sits behind a ColumnTransformer in the
        # pipeline, so build the explainer on model.named_steps["model"]
        # using the *transformed* feature matrix (after one-hot encoding
        # climate_zone), then map SHAP values back to human-readable
        # feature names for the response.
        explainer = shap.TreeExplainer(model.named_steps["model"])
        transformed_row = model.named_steps["preprocess"].transform(row)
        shap_values = explainer.shap_values(transformed_row)
        # -> return per-feature contribution to the prediction, e.g.
        #    {"age_months": -3.1, "mileage_km": -2.4, "fast_charge_pct": -1.9,
        #     "climate_zone_hot": -1.2, "base_value": 98.5}

    For now this returns a placeholder so the API shape is stable and the
    frontend/route layer doesn't need to change when SHAP is wired in.
    """
    return {
        "status": "not_implemented",
        "message": "SHAP-based explainability is a planned 'Later' feature — see ARCHITECTURE.md.",
    }
