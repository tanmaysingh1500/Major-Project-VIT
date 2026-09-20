import pytest

from app.models.recommend import RecommendWeights
from app.services import recommend


def _run(weights=None, **overrides):
    kwargs = dict(
        budget_inr=2_000_000,
        daily_km=40,
        state="Delhi",
        payment_mode="cash",
        ownership_years=5,
        assumed_climate_zone="temperate",
        assumed_fast_charge_pct=20,
        weights=weights or RecommendWeights(),
    )
    kwargs.update(overrides)
    return recommend.generate_recommendations(**kwargs)


def test_returns_all_seed_models():
    results = _run()
    assert len(results) == 5


def test_scores_are_between_0_and_1():
    results = _run()
    for r in results:
        assert 0.0 <= r["score"] <= 1.0


def test_within_budget_flag_is_correct():
    results = _run(budget_inr=900_000)  # only the cheapest model should fit
    within = [r for r in results if r["within_budget"]]
    not_within = [r for r in results if not r["within_budget"]]
    assert len(within) >= 1
    for r in within:
        assert r["tco"]["effective_purchase_price_inr"] <= 900_000
    for r in not_within:
        assert r["tco"]["effective_purchase_price_inr"] > 900_000


def test_within_budget_models_are_sorted_before_out_of_budget():
    results = _run(budget_inr=1_000_000)
    within_flags = [r["within_budget"] for r in results]
    # Once we hit a False, everything after must also be False (grouped, not interleaved)
    seen_false = False
    for flag in within_flags:
        if not flag:
            seen_false = True
        else:
            assert not seen_false, "within-budget model appears after an out-of-budget one"


def test_higher_cost_weight_favors_cheaper_models():
    cost_heavy = _run(weights=RecommendWeights(cost=100, range=0, battery_health=0, charging_speed=0))
    top_pick = cost_heavy[0]
    cheapest_model_id = "tata-tiago-ev"  # lowest base price in the seed catalog
    assert top_pick["model_id"] == cheapest_model_id


def test_all_zero_weights_falls_back_to_equal_weighting_without_crashing():
    results = _run(weights=RecommendWeights(cost=0, range=0, battery_health=0, charging_speed=0))
    assert len(results) == 5
    for r in results:
        assert 0.0 <= r["score"] <= 1.0


def test_projected_soh_reflects_ownership_years_and_usage():
    short_ownership = _run(ownership_years=1)
    long_ownership = _run(ownership_years=15)
    # Compare the same model across the two runs.
    short_soh = next(r for r in short_ownership if r["model_id"] == "tata-nexon-ev")["projected_soh_pct"]
    long_soh = next(r for r in long_ownership if r["model_id"] == "tata-nexon-ev")["projected_soh_pct"]
    assert short_soh > long_soh


def test_result_includes_resale_note_referencing_soh_and_years():
    results = _run(ownership_years=5)
    for r in results:
        assert str(r["projected_soh_pct"]) in r["soh_adjusted_resale_note"]
        assert "5 yrs" in r["soh_adjusted_resale_note"]


def test_deterministic_same_inputs_same_output():
    r1 = _run()
    r2 = _run()
    assert r1 == r2
