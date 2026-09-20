import pytest

from app.services import soh_estimator


def test_predict_soh_returns_value_in_valid_range():
    soh = soh_estimator.predict_soh(
        age_months=24, mileage_km=40000, fast_charge_pct=20, climate_zone="temperate"
    )
    assert 0.0 <= soh <= 100.0


def test_predict_soh_is_deterministic():
    kwargs = dict(age_months=36, mileage_km=60000, fast_charge_pct=30, climate_zone="hot")
    r1 = soh_estimator.predict_soh(**kwargs)
    r2 = soh_estimator.predict_soh(**kwargs)
    assert r1 == r2


def test_new_car_has_higher_soh_than_old_car():
    """A near-new car should show a materially higher estimated SOH than a
    heavily aged/used one, all else equal — sanity check on model direction."""
    new_car_soh = soh_estimator.predict_soh(
        age_months=2, mileage_km=1000, fast_charge_pct=5, climate_zone="temperate"
    )
    old_car_soh = soh_estimator.predict_soh(
        age_months=90, mileage_km=180000, fast_charge_pct=90, climate_zone="hot"
    )
    assert new_car_soh > old_car_soh


def test_hot_climate_degrades_faster_than_temperate_all_else_equal():
    hot_soh = soh_estimator.predict_soh(
        age_months=48, mileage_km=80000, fast_charge_pct=40, climate_zone="hot"
    )
    temperate_soh = soh_estimator.predict_soh(
        age_months=48, mileage_km=80000, fast_charge_pct=40, climate_zone="temperate"
    )
    assert temperate_soh >= hot_soh


def test_more_fast_charging_degrades_soh_all_else_equal():
    low_fast_charge = soh_estimator.predict_soh(
        age_months=48, mileage_km=80000, fast_charge_pct=5, climate_zone="temperate"
    )
    high_fast_charge = soh_estimator.predict_soh(
        age_months=48, mileage_km=80000, fast_charge_pct=95, climate_zone="temperate"
    )
    assert low_fast_charge >= high_fast_charge


def test_explain_soh_stub_returns_not_implemented():
    result = soh_estimator.explain_soh(24, 40000, 20, "temperate")
    assert result["status"] == "not_implemented"
