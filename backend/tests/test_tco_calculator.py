import pytest

from app.models.ev_model import EVModel
from app.services import tco_calculator as calc

ASSUMPTIONS = {
    "electricity_price_inr_per_kwh": 8.0,
    "home_charging_efficiency": 0.9,
    "annual_maintenance_pct_of_price": 0.015,
    "annual_insurance_pct_of_price": 0.03,
    "insurance_depreciation_factor_per_year": 0.1,
    "annual_resale_depreciation_pct": 0.12,
    "min_resale_value_pct": 0.15,
    "loan_interest_rate_annual": 0.10,
    "loan_tenure_years": 5,
    "loan_down_payment_pct": 0.2,
    "central_subsidy": {
        "applies_to_body_types": ["Hatchback"],
        "max_subsidy_inr": 100000,
        "per_kwh_inr": 10000,
    },
    "state_subsidies_inr": {
        "Delhi": 100000,
        "Karnataka": 0,
        "Other": 0,
    },
}


def make_model(**overrides) -> EVModel:
    defaults = dict(
        id="test-car",
        make="Test",
        model="Car",
        body_type="SUV",
        price_inr=1_500_000,
        battery_kwh=40.0,
        range_km=400.0,
        charging_speed_kw=50.0,
        fast_charge_10_80_min=55,
        warranty_years=8,
        warranty_km=160000,
    )
    defaults.update(overrides)
    return EVModel(**defaults)


# ---- compute_subsidy ----

def test_subsidy_zero_for_non_eligible_body_type():
    model = make_model(body_type="SUV")
    central, state = calc.compute_subsidy(model, "Delhi", ASSUMPTIONS)
    assert central == 0.0
    assert state == 100000.0


def test_subsidy_applies_and_caps_for_eligible_body_type():
    # 40 kWh * 10000/kWh = 400000, capped at max_subsidy_inr=100000
    model = make_model(body_type="Hatchback", battery_kwh=40.0)
    central, state = calc.compute_subsidy(model, "Karnataka", ASSUMPTIONS)
    assert central == 100000.0
    assert state == 0.0


def test_subsidy_per_kwh_below_cap():
    # 2 kWh * 10000 = 20000, below the 100000 cap
    model = make_model(body_type="Hatchback", battery_kwh=2.0)
    central, _ = calc.compute_subsidy(model, "Other", ASSUMPTIONS)
    assert central == 20000.0


def test_subsidy_unknown_state_falls_back_to_other():
    model = make_model(body_type="SUV")
    _, state = calc.compute_subsidy(model, "SomeUnlistedState", ASSUMPTIONS)
    assert state == 0.0


# ---- compute_effective_price ----

def test_effective_price_subtracts_subsidy():
    assert calc.compute_effective_price(1_000_000, 50_000, 25_000) == 925_000


def test_effective_price_never_negative():
    # Subsidy larger than price should be clamped, not go negative.
    assert calc.compute_effective_price(10_000, 100_000, 100_000) == 0.0


# ---- compute_running_cost ----

def test_running_cost_basic_math():
    model = make_model(battery_kwh=40.0, range_km=400.0)  # 0.1 kWh/km
    annual, total = calc.compute_running_cost(model, annual_km=10000, years=3, assumptions=ASSUMPTIONS)
    # cost_per_km = (0.1 / 0.9) * 8 = 0.8888...
    expected_annual = (0.1 / 0.9) * 8.0 * 10000
    assert annual == pytest.approx(expected_annual)
    assert total == pytest.approx(expected_annual * 3)


def test_running_cost_scales_linearly_with_km():
    model = make_model(battery_kwh=40.0, range_km=400.0)
    annual_1, _ = calc.compute_running_cost(model, annual_km=10000, years=1, assumptions=ASSUMPTIONS)
    annual_2, _ = calc.compute_running_cost(model, annual_km=20000, years=1, assumptions=ASSUMPTIONS)
    assert annual_2 == pytest.approx(annual_1 * 2)


# ---- compute_maintenance_cost ----

def test_maintenance_cost():
    annual, total = calc.compute_maintenance_cost(1_000_000, years=5, assumptions=ASSUMPTIONS)
    assert annual == pytest.approx(15_000)
    assert total == pytest.approx(75_000)


# ---- compute_insurance_cost ----

def test_insurance_cost_declines_each_year():
    # year 1: 1,000,000 * 0.03 = 30000; value now 900000
    # year 2: 900,000 * 0.03 = 27000
    total = calc.compute_insurance_cost(1_000_000, years=2, assumptions=ASSUMPTIONS)
    assert total == pytest.approx(30_000 + 27_000)


def test_insurance_cost_zero_years():
    assert calc.compute_insurance_cost(1_000_000, years=0, assumptions=ASSUMPTIONS) == 0.0


# ---- compute_resale_value ----

def test_resale_value_straight_line():
    # 12% per year for 3 years = 36% depreciation -> 64% remaining
    value = calc.compute_resale_value(1_000_000, years=3, assumptions=ASSUMPTIONS)
    assert value == pytest.approx(640_000)


def test_resale_value_floors_at_minimum():
    # 12%/yr * 20 years = 240% > 100%, should floor at min_resale_value_pct (15%)
    value = calc.compute_resale_value(1_000_000, years=20, assumptions=ASSUMPTIONS)
    assert value == pytest.approx(150_000)


def test_resale_value_never_negative():
    value = calc.compute_resale_value(1_000_000, years=100, assumptions=ASSUMPTIONS)
    assert value >= 0


# ---- compute_loan_schedule ----

def test_loan_schedule_basic_shape():
    schedule = calc.compute_loan_schedule(1_000_000, ASSUMPTIONS)
    assert schedule["down_payment_inr"] == pytest.approx(200_000)
    assert schedule["principal_inr"] == pytest.approx(800_000)
    assert schedule["monthly_emi_inr"] > 0
    assert schedule["total_interest_inr"] > 0
    # total paid should equal down payment + all EMIs
    expected_total = schedule["down_payment_inr"] + schedule["monthly_emi_inr"] * (
        ASSUMPTIONS["loan_tenure_years"] * 12
    )
    assert schedule["total_paid_inr"] == pytest.approx(expected_total, rel=1e-6)


def test_loan_schedule_zero_interest_is_simple_division():
    zero_interest_assumptions = dict(ASSUMPTIONS, loan_interest_rate_annual=0.0)
    schedule = calc.compute_loan_schedule(1_200_000, zero_interest_assumptions)
    # principal after 20% down = 960,000 over 60 months = 16,000/month, no interest
    assert schedule["monthly_emi_inr"] == pytest.approx(16_000)
    assert schedule["total_interest_inr"] == pytest.approx(0.0, abs=1e-6)


# ---- calculate_tco (integration of the pure functions) ----

def test_calculate_tco_cash_purchase_has_no_loan_breakdown():
    model = make_model(body_type="SUV", price_inr=1_500_000)
    result = calc.calculate_tco(
        model=model,
        annual_km=12000,
        state="Delhi",
        payment_mode="cash",
        ownership_years=5,
        assumptions=ASSUMPTIONS,
    )
    assert result["loan"] is None
    assert result["total_subsidy_inr"] == 100_000  # Delhi state subsidy only
    assert result["effective_purchase_price_inr"] == 1_400_000
    assert result["total_cost_of_ownership_inr"] > 0


def test_calculate_tco_loan_purchase_includes_breakdown_and_costs_more():
    model = make_model(body_type="SUV", price_inr=1_500_000)
    cash_result = calc.calculate_tco(
        model=model, annual_km=12000, state="Delhi",
        payment_mode="cash", ownership_years=5, assumptions=ASSUMPTIONS,
    )
    loan_result = calc.calculate_tco(
        model=model, annual_km=12000, state="Delhi",
        payment_mode="loan", ownership_years=5, assumptions=ASSUMPTIONS,
    )
    assert loan_result["loan"] is not None
    assert loan_result["loan"]["total_interest_inr"] > 0
    # Financing should never be cheaper overall than paying cash (interest > 0).
    assert loan_result["total_cost_of_ownership_inr"] > cash_result["total_cost_of_ownership_inr"]


def test_calculate_tco_is_deterministic():
    """Same inputs -> exactly the same output. No randomness anywhere."""
    model = make_model()
    r1 = calc.calculate_tco(model, 10000, "Karnataka", "cash", 4, ASSUMPTIONS)
    r2 = calc.calculate_tco(model, 10000, "Karnataka", "cash", 4, ASSUMPTIONS)
    assert r1 == r2


def test_calculate_tco_subsidy_never_exceeds_price():
    # Cheap hatchback with a huge battery relative to price shouldn't go negative.
    model = make_model(body_type="Hatchback", price_inr=50_000, battery_kwh=40.0)
    result = calc.calculate_tco(model, 8000, "Delhi", "cash", 3, ASSUMPTIONS)
    assert result["effective_purchase_price_inr"] >= 0
