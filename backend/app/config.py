"""
Central path/config module. Keeping all file paths in one place makes it
trivial to swap SQLite -> Postgres, or the local /data files -> a real DB,
without hunting through route handlers.
"""

from pathlib import Path

# Repo layout: <root>/backend, <root>/frontend, <root>/data, <root>/ml
BACKEND_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BACKEND_DIR.parent

DATA_DIR = ROOT_DIR / "data"
ML_DIR = ROOT_DIR / "ml"

EV_MODELS_PATH = DATA_DIR / "ev_models.json"
TCO_ASSUMPTIONS_PATH = DATA_DIR / "tco_assumptions.json"
POLICY_CORPUS_DIR = DATA_DIR / "policy_corpus"

SOH_MODEL_PATH = ML_DIR / "soh_model.joblib"
SOH_TRAINING_DATA_PATH = ML_DIR / "soh_training_data.csv"
