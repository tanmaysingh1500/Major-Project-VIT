"""
EV catalog service.

This module is the single access point for EV model data. It is deliberately
kept free of any FastAPI/HTTP concerns so that:
  (a) it's independently unit-testable, and
  (b) a future 'Specification Agent' (per the FF-180 synopsis) can call this
      same function directly instead of going through HTTP.
"""

import json
from functools import lru_cache
from typing import Optional

from app.config import EV_MODELS_PATH
from app.models.ev_model import EVModel


@lru_cache(maxsize=1)
def _load_raw() -> dict:
    with open(EV_MODELS_PATH, "r") as f:
        return json.load(f)


def get_catalog_metadata() -> dict:
    """Returns the disclaimer + last_updated fields shipped with the seed data."""
    raw = _load_raw()
    return {"disclaimer": raw.get("_disclaimer"), "last_updated": raw.get("last_updated")}


def list_ev_models() -> list[EVModel]:
    raw = _load_raw()
    return [EVModel(**m) for m in raw["models"]]


def get_ev_model(model_id: str) -> Optional[EVModel]:
    for m in list_ev_models():
        if m.id == model_id:
            return m
    return None
