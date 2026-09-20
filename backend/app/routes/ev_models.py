from fastapi import APIRouter, HTTPException

from app.models.ev_model import EVModel
from app.services import ev_catalog

router = APIRouter()


@router.get("/", response_model=list[EVModel])
def list_models():
    """Return the full seed catalog of EV models."""
    return ev_catalog.list_ev_models()


@router.get("/meta")
def catalog_meta():
    """Disclaimer + last-updated date for the seed data (it's illustrative, not live)."""
    return ev_catalog.get_catalog_metadata()


@router.get("/{model_id}", response_model=EVModel)
def get_model(model_id: str):
    model = ev_catalog.get_ev_model(model_id)
    if model is None:
        raise HTTPException(status_code=404, detail=f"EV model '{model_id}' not found")
    return model
