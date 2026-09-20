"""
Recommendation service.

This is the MVP stand-in for the full "Recommendation Agent" + MCDM scoring
described in the synopsis. It's a transparent, weighted-sum scoring formula
over normalized criteria — deliberately simple and auditable rather than a
black-box ranker, and the weights are exposed to the frontend so the user
can adjust them and see the ranking change live.

It calls the TCO calculator and SOH estimator services directly (no HTTP
hop, no orchestrator yet) — this is exactly the "clean service-layer
boundary" the project brief asks the MVP to leave, so a real orchestrator
agent can be dropped in later to call these same functions.
"""

from app.models.recommend import RecommendWeights
from app.services import ev_catalog, soh_estimator, tco_calculator


def _normalize(values: list[float], higher_is_better: bool) -> list[float]:
    """Min-max normalize a list of values to [0, 1]. If all values are equal,
    everyone gets a neutral 0.5 score rather than a divide-by-zero."""
    lo, hi = min(values), max(values)
    if hi == lo:
        return [0.5 for _ in values]
    if higher_is_better:
        return [(v - lo) / (hi - lo) for v in values]
    return [(hi - v) / (hi - lo) for v in values]


def generate_recommendations(
    budget_inr: float,
    daily_km: float,
    state: str,
    payment_mode: str,
    ownership_years: int,
    assumed_climate_zone: str,
    assumed_fast_charge_pct: float,
    weights: RecommendWeights,
) -> list[dict]:
    annual_km = daily_km * 365
    models = ev_catalog.list_ev_models()

    raw_rows = []
    for model in models:
        tco = tco_calculator.calculate_tco(
            model=model,
            annual_km=annual_km,
            state=state,
            payment_mode=payment_mode,
            ownership_years=ownership_years,
        )

        age_months = ownership_years * 12
        mileage_km = annual_km * ownership_years
        projected_soh = soh_estimator.predict_soh(
            age_months=age_months,
            mileage_km=mileage_km,
            fast_charge_pct=assumed_fast_charge_pct,
            climate_zone=assumed_climate_zone,
        )

        raw_rows.append(
            {
                "model": model,
                "tco": tco,
                "projected_soh_pct": round(projected_soh, 2),
            }
        )

    # --- normalize criteria across the candidate set ---
    costs = [r["tco"]["total_cost_of_ownership_inr"] for r in raw_rows]
    ranges = [r["model"].range_km for r in raw_rows]
    sohs = [r["projected_soh_pct"] for r in raw_rows]
    charge_speeds = [r["model"].charging_speed_kw for r in raw_rows]

    cost_scores = _normalize(costs, higher_is_better=False)
    range_scores = _normalize(ranges, higher_is_better=True)
    soh_scores = _normalize(sohs, higher_is_better=True)
    charge_scores = _normalize(charge_speeds, higher_is_better=True)

    total_weight = weights.cost + weights.range + weights.battery_health + weights.charging_speed
    if total_weight <= 0:
        # Guard against all-zero weights; fall back to equal weighting.
        w_cost = w_range = w_soh = w_charge = 0.25
    else:
        w_cost = weights.cost / total_weight
        w_range = weights.range / total_weight
        w_soh = weights.battery_health / total_weight
        w_charge = weights.charging_speed / total_weight

    results = []
    for i, row in enumerate(raw_rows):
        score = (
            w_cost * cost_scores[i]
            + w_range * range_scores[i]
            + w_soh * soh_scores[i]
            + w_charge * charge_scores[i]
        )
        model = row["model"]
        tco = row["tco"]
        soh = row["projected_soh_pct"]

        # Deterministic, computed note (no LLM): compares projected SOH to a
        # neutral 90% reference point to flag whether the straight-line
        # resale estimate might be optimistic or pessimistic given battery
        # condition at that usage profile.
        if soh >= 92:
            resale_note = (
                f"Projected battery health ~{soh}% after {ownership_years} yrs — "
                "above-average condition; the straight-line resale estimate may be conservative."
            )
        elif soh >= 85:
            resale_note = (
                f"Projected battery health ~{soh}% after {ownership_years} yrs — "
                "roughly in line with the straight-line resale estimate."
            )
        else:
            resale_note = (
                f"Projected battery health ~{soh}% after {ownership_years} yrs — "
                "below-average condition for this usage profile; actual resale value may run "
                "below the straight-line estimate."
            )

        results.append(
            {
                "model_id": model.id,
                "make": model.make,
                "model": model.model,
                "within_budget": tco["effective_purchase_price_inr"] <= budget_inr,
                "score": round(score, 4),
                "tco": tco,
                "projected_soh_pct": soh,
                "soh_adjusted_resale_note": resale_note,
            }
        )

    # Within-budget models first, then by score descending within each group.
    results.sort(key=lambda r: (not r["within_budget"], -r["score"]))
    return results
