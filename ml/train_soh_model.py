"""
Trains the MVP Battery State-of-Health (SOH) regression model and saves it
as a joblib artifact for the backend to load at request time.

This is a SIMPLIFIED stand-in for the full ML pipeline described in the
FF-180 synopsis (which calls for a model trained on real fleet/indirect
usage data). Here we train on the synthetic dataset from
generate_synthetic_data.py.

Model: scikit-learn Pipeline = [ColumnTransformer(one-hot climate_zone)] ->
RandomForestRegressor. Chosen for:
  - no assumption of linear relationships (age has diminishing-returns decay)
  - handles the categorical climate_zone feature cleanly
  - trains in well under a second on 2000 rows, easy to demo
"""

from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from generate_synthetic_data import generate

NUMERIC_FEATURES = ["age_months", "mileage_km", "fast_charge_pct"]
CATEGORICAL_FEATURES = ["climate_zone"]
TARGET = "soh_pct"

THIS_DIR = Path(__file__).parent
DATA_PATH = THIS_DIR / "soh_training_data.csv"
MODEL_PATH = THIS_DIR / "soh_model.joblib"


def build_pipeline() -> Pipeline:
    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
        ],
        remainder="passthrough",  # numeric features pass through unchanged
    )
    model = RandomForestRegressor(
        n_estimators=200,
        max_depth=8,
        min_samples_leaf=5,
        random_state=42,
    )
    return Pipeline(steps=[("preprocess", preprocessor), ("model", model)])


def main():
    if DATA_PATH.exists():
        df = pd.read_csv(DATA_PATH)
    else:
        df = generate()
        df.to_csv(DATA_PATH, index=False)

    X = df[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    y = df[TARGET]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    pipeline = build_pipeline()
    pipeline.fit(X_train, y_train)

    preds = pipeline.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    r2 = r2_score(y_test, preds)
    print(f"Test MAE: {mae:.3f} percentage points")
    print(f"Test R^2: {r2:.3f}")

    joblib.dump(pipeline, MODEL_PATH)
    print(f"Saved model to {MODEL_PATH}")


if __name__ == "__main__":
    main()
