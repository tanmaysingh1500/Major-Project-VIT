"""
EV Pal backend — FastAPI app entrypoint.

MVP scope (see /README.md and /ARCHITECTURE.md for the full mapping back to
the FF-180 synopsis):
  - EV knowledge base (seed data, read-only)
  - Deterministic TCO calculator
  - Simplified SOH regression estimator
  - RAG-lite policy Q&A over a small local, illustrative corpus
  - Recommendation view combining all of the above with adjustable weights

Design principle carried through the whole system: numbers are computed,
not hallucinated. Every TCO figure, subsidy amount, and SOH estimate comes
from a deterministic function or a trained model — never from an LLM.
There is no LLM call anywhere in this MVP backend.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import ev_models, tco, soh, policy, recommend

app = FastAPI(
    title="EV Pal API",
    description="Integrated EV decision-support platform for the Indian EV market (MVP).",
    version="0.1.0",
)

# Wide-open CORS for local dev (frontend runs on a different port via Vite).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["meta"])
def health_check():
    """Simple liveness check used by the frontend and by ops tooling."""
    return {"status": "ok", "service": "ev-pal-backend"}


app.include_router(ev_models.router, prefix="/ev-models", tags=["ev-models"])
app.include_router(tco.router, prefix="/tco", tags=["tco"])
app.include_router(soh.router, prefix="/soh", tags=["soh"])
app.include_router(policy.router, prefix="/policy", tags=["policy"])
app.include_router(recommend.router, prefix="/recommend", tags=["recommend"])
