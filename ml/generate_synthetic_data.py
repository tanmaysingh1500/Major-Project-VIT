"""
Generates a SYNTHETIC training dataset for the Battery State-of-Health (SOH)
estimator MVP.

This is explicitly a stand-in for real fleet/BMS-derived data (see the
project synopsis's full ML pipeline). The relationships below are
hand-authored to be *plausible* (age, mileage, fast-charging and climate all
degrade battery health, roughly matching commonly cited EV battery
degradation patterns) but are NOT fitted to any real observed dataset.
Treat this model's predictions as illustrative only.

Features:
  - age_months: vehicle age in months (0-96)
  - mileage_km: total odometer reading (0-200,000)
  - fast_charge_pct: % of charging sessions that are DC fast-charging (0-100)
  - climate_zone: one of {hot, temperate, cold} — proxy for thermal stress

Target:
  - soh_pct: estimated State of Health, 100 = new battery, degrading over time
"""

import numpy as np
import pandas as pd

RNG_SEED = 42


def generate(n_samples: int = 2000, seed: int = RNG_SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    age_months = rng.uniform(0, 96, n_samples)
    mileage_km = rng.uniform(0, 200_000, n_samples)
    # Correlate mileage loosely with age (older cars tend to have driven more),
    # but keep enough spread that mileage carries independent signal too.
    mileage_km = 0.6 * mileage_km + 0.4 * (age_months / 96) * 200_000
    fast_charge_pct = rng.uniform(0, 100, n_samples)
    climate_zone = rng.choice(["hot", "temperate", "cold"], size=n_samples, p=[0.35, 0.4, 0.25])

    # Climate stress multiplier: hot climates accelerate calendar degradation
    # the most, cold has a smaller but real effect, temperate is the baseline.
    climate_factor = np.select(
        [climate_zone == "hot", climate_zone == "cold", climate_zone == "temperate"],
        [1.35, 1.15, 1.0],
    )

    # Base degradation model (illustrative, not derived from measured data):
    #   - calendar aging ~ sqrt(age) (fast early, slows down)
    #   - cycling aging ~ linear in mileage
    #   - fast charging adds extra stress, scaling with usage share
    calendar_degradation = 0.35 * np.sqrt(age_months) * climate_factor
    cycling_degradation = mileage_km / 200_000 * 10.0
    fast_charge_degradation = (fast_charge_pct / 100) * 4.0

    noise = rng.normal(0, 1.2, n_samples)

    soh = 100 - calendar_degradation - cycling_degradation - fast_charge_degradation + noise
    soh = np.clip(soh, 55, 100)  # batteries don't realistically report below ~55% SOH here

    df = pd.DataFrame(
        {
            "age_months": np.round(age_months, 1),
            "mileage_km": np.round(mileage_km, 0).astype(int),
            "fast_charge_pct": np.round(fast_charge_pct, 1),
            "climate_zone": climate_zone,
            "soh_pct": np.round(soh, 2),
        }
    )
    return df


if __name__ == "__main__":
    from pathlib import Path

    out_path = Path(__file__).parent / "soh_training_data.csv"
    df = generate()
    df.to_csv(out_path, index=False)
    print(f"Wrote {len(df)} synthetic rows to {out_path}")
    print(df.describe(include="all"))
