"""
Deterministic Total Cost of Ownership (TCO) calculator.

Every function here is a pure function of its inputs (plus the static
assumptions dict) — no randomness, no network calls, no LLM involved. This
is the module the project's core design principle refers to: "numbers are
computed, not hallucinated". These functions are the ones covered by
backend/tests/test_tco_calculator.py.
"""

import json
from functools import lru_cache

from app.config import TCO_ASSUMPTIONS_PATH
from app.models.ev_model import EVModel


@lru_cache(maxsize=1)
def load_assumptions() -> dict:
    with open(TCO_ASSUMPTIONS_PATH, "r") as f:
        return json.load(f)


def compute_subsidy(model: EVModel, state: str, assumptions: dict) -> tuple[float, float]:
    """Returns (central_subsidy_inr, state_subsidy_inr).

    Simplified, illustrative rule set — see data/tco_assumptions.json for the
    disclaimer. Central subsidy is capped at the lower of a flat max and a
    per-kWh rate, and only applies to the body types listed in assumptions
    (mirrors FAME-II's historical narrow scoping toward smaller vehicles).
    """
    central_cfg = assumptions["central_subsidy"]
    central_subsidy = 0.0
    if model.body_type in central_cfg["applies_to_body_types"]:
        per_kwh_amount = model.battery_kwh * central_cfg["per_kwh_inr"]
        central_subsidy = min(per_kwh_amount, central_cfg["max_subsidy_inr"])

    state_subsidies = assumptions["state_subsidies_inr"]
    state_subsidy = state_subsidies.get(state, state_subsidies.get("Other", 0.0))

    return central_subsidy, float(state_subsidy)


def compute_effective_price(base_price: float, central_subsidy: float, state_subsidy: float) -> float:
    total_subsidy = central_subsidy + state_subsidy
    # Subsidy can never exceed the vehicle price.
    total_subsidy = min(total_subsidy, base_price)
    return base_price - total_subsidy


def compute_running_cost(model: EVModel, annual_km: float, years: int, assumptions: dict) -> tuple[float, float]:
    """Returns (annual_running_cost_inr, total_running_cost_inr).

    Cost per km = (battery_kwh / range_km) kWh/km, grossed up for charging
    losses, times the electricity price.
    """
    kwh_per_km = model.battery_kwh / model.range_km
    efficiency = assumptions["home_charging_efficiency"]
    price_per_kwh = assumptions["electricity_price_inr_per_kwh"]

    cost_per_km = (kwh_per_km / efficiency) * price_per_kwh
    annual_cost = cost_per_km * annual_km
    total_cost = annual_cost * years
    return annual_cost, total_cost


def compute_maintenance_cost(base_price: float, years: int, assumptions: dict) -> tuple[float, float]:
    """Returns (annual_maintenance_inr, total_maintenance_inr). Flat % of base price per year."""
    pct = assumptions["annual_maintenance_pct_of_price"]
    annual = base_price * pct
    return annual, annual * years


def compute_insurance_cost(base_price: float, years: int, assumptions: dict) -> float:
    """Total insurance cost across the ownership period.

    Insurance premium each year is a % of the vehicle's *declining* insured
    value (a simple straight-line-ish depreciation proxy), floored so the
    premium never goes to zero.
    """
    pct = assumptions["annual_insurance_pct_of_price"]
    dep_factor = assumptions["insurance_depreciation_factor_per_year"]

    total = 0.0
    insured_value = base_price
    for _year in range(years):
        total += insured_value * pct
        insured_value = max(insured_value * (1 - dep_factor), 0.0)
    return total


def compute_resale_value(base_price: float, years: int, assumptions: dict) -> float:
    """Simple straight-line resale value estimate with a floor.

    value(t) = base_price * max(1 - annual_depreciation_pct * t, min_resale_pct)
    """
    annual_dep = assumptions["annual_resale_depreciation_pct"]
    min_pct = assumptions["min_resale_value_pct"]
    remaining_pct = max(1 - annual_dep * years, min_pct)
    return base_price * remaining_pct


def compute_loan_schedule(principal_after_subsidy: float, assumptions: dict) -> dict:
    """Standard amortizing-loan EMI calculation.

    down_payment is taken as a % of the (post-subsidy) price the buyer
    finances; loan_tenure_years and loan_interest_rate_annual come from the
    shared assumptions config.
    """
    down_pct = assumptions["loan_down_payment_pct"]
    rate_annual = assumptions["loan_interest_rate_annual"]
    tenure_years = assumptions["loan_tenure_years"]

    down_payment = principal_after_subsidy * down_pct
    principal = principal_after_subsidy - down_payment

    monthly_rate = rate_annual / 12
    n_months = tenure_years * 12

    if monthly_rate == 0:
        emi = principal / n_months if n_months else 0.0
    else:
        emi = (
            principal
            * monthly_rate
            * (1 + monthly_rate) ** n_months
            / ((1 + monthly_rate) ** n_months - 1)
        )

    total_paid = emi * n_months
    total_interest = total_paid - principal

    return {
        "down_payment_inr": round(down_payment, 2),
        "principal_inr": round(principal, 2),
        "monthly_emi_inr": round(emi, 2),
        "total_interest_inr": round(total_interest, 2),
        "total_paid_inr": round(total_paid + down_payment, 2),
    }


def calculate_tco(
    model: EVModel,
    annual_km: float,
    state: str,
    payment_mode: str,
    ownership_years: int,
    assumptions: dict | None = None,
) -> dict:
    """Top-level orchestrating function — still pure, just composes the pieces above."""
    if assumptions is None:
        assumptions = load_assumptions()

    central_subsidy, state_subsidy = compute_subsidy(model, state, assumptions)
    effective_price = compute_effective_price(model.price_inr, central_subsidy, state_subsidy)

    running_annual, running_total = compute_running_cost(model, annual_km, ownership_years, assumptions)
    maint_annual, maint_total = compute_maintenance_cost(model.price_inr, ownership_years, assumptions)
    insurance_total = compute_insurance_cost(model.price_inr, ownership_years, assumptions)
    resale_value = compute_resale_value(model.price_inr, ownership_years, assumptions)

    loan_breakdown = None
    loan_interest_component = 0.0
    if payment_mode == "loan":
        loan_breakdown = compute_loan_schedule(effective_price, assumptions)
        loan_interest_component = loan_breakdown["total_interest_inr"]

    total_cost = (
        effective_price
        + running_total
        + maint_total
        + insurance_total
        + loan_interest_component
        - resale_value
    )

    return {
        "model_id": model.id,
        "base_price_inr": model.price_inr,
        "central_subsidy_inr": round(central_subsidy, 2),
        "state_subsidy_inr": round(state_subsidy, 2),
        "total_subsidy_inr": round(central_subsidy + state_subsidy, 2),
        "effective_purchase_price_inr": round(effective_price, 2),
        "running_cost_annual_inr": round(running_annual, 2),
        "running_cost_total_inr": round(running_total, 2),
        "maintenance_cost_annual_inr": round(maint_annual, 2),
        "maintenance_cost_total_inr": round(maint_total, 2),
        "insurance_cost_total_inr": round(insurance_total, 2),
        "loan": loan_breakdown,
        "resale_value_inr": round(resale_value, 2),
        "total_cost_of_ownership_inr": round(total_cost, 2),
        "ownership_years": ownership_years,
        "assumptions_used": assumptions,
    }
