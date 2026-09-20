# EV Pal — MVP

An integrated EV decision-support platform for the Indian EV market. This
repo is the **MVP slice** of the full FF-180 project synopsis (Group 42):
four working modules on a small seed dataset, wired into one recommendation
view, built end-to-end and unit-tested.

See `ARCHITECTURE.md` for how each MVP module maps back to the full
synopsis (agents, XAI, full RAG, etc.) and what's deliberately left as a
stub for later.

## Core design principle

**Numbers are computed, not hallucinated.** Every TCO figure, subsidy
amount, and SOH estimate comes from a deterministic function or a trained
scikit-learn model — there is **no LLM call anywhere in this codebase**.
The policy Q&A module retrieves and returns real corpus text verbatim
(with citations), rather than having a model paraphrase or generate an
answer, for the same reason.

## What's implemented (MVP scope)

| Module | What it does | Where |
|---|---|---|
| EV Knowledge Base | 5 seed Indian EV models with specs | `data/ev_models.json`, `/ev-models` |
| TCO Calculator | Deterministic purchase/subsidy/running/maintenance/insurance/resale/loan math | `backend/app/services/tco_calculator.py`, `/tco/calculate` |
| SOH Estimator | scikit-learn regression trained on a synthetic dataset, from indirect usage factors | `ml/`, `backend/app/services/soh_estimator.py`, `/soh/estimate` |
| Policy Q&A (RAG-lite) | TF-IDF retrieval over a small local markdown corpus, with citations + last-verified dates | `data/policy_corpus/`, `backend/app/services/policy_rag.py`, `/policy/ask` |
| Recommendation view | Transparent weighted-sum scoring combining all of the above, with user-adjustable weights | `backend/app/services/recommend.py`, `/recommend/` |

All five are wired into a single React frontend (`frontend/`) with a tab
per module, hitting a FastAPI backend (`backend/`) over a local dev proxy.

## What's explicitly stubbed / simplified (see ARCHITECTURE.md for detail)

- **Agentic orchestration** — the backend calls each service module
  directly; there's a clean service-layer boundary (`app/services/*.py`,
  independent of any HTTP/FastAPI concerns) so an orchestrator can be
  dropped in later without rewriting the modules themselves.
- **SHAP explainability** — `soh_estimator.explain_soh()` is a stub with a
  TODO showing exactly where a `shap.TreeExplainer` would plug in.
- **Sentence-transformers + Chroma** — the RAG-lite module uses a local
  scikit-learn `TfidfVectorizer` instead, because this build environment
  had no network access to download an embedding model from Hugging Face.
  The retrieval interface (`build_index()` / `retrieve()`) is the seam —
  swapping in real embeddings + Chroma only touches
  `backend/app/services/policy_rag.py`.
- **Full 10–15 model catalog** — only 5 seed models are included, in a
  single JSON file (`data/ev_models.json`) that's trivial to extend.
- **Live/verified policy data** — the policy corpus is 7 short markdown
  files, each explicitly marked as an "illustrative summary" with a
  `last_verified` placeholder date. None of it should be treated as
  current, sourced policy.
- **Production auth, deployment, monitoring** — not built; this is a local
  dev MVP.

## Repo layout

```
backend/         FastAPI app (routes, services, models, tests)
frontend/        React (Vite) app
ml/              SOH training script, synthetic data generator, saved model
data/            Seed EV catalog, TCO assumption constants, policy corpus
README.md        This file
ARCHITECTURE.md  Maps MVP modules back to the full FF-180 synopsis
```

## How to run it

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate   # on Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Health check: `curl http://127.0.0.1:8000/health`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`. The Vite dev server proxies `/api/*` to the
backend on port 8000 (see `frontend/vite.config.js`) — no CORS/origin
config needed for local dev.

### Regenerating the SOH model

The trained model artifact (`ml/soh_model.joblib`) is checked in, but you
can regenerate it (e.g. after changing the synthetic data generator):

```bash
cd ml
python3 generate_synthetic_data.py   # writes ml/soh_training_data.csv
python3 train_soh_model.py           # trains + saves ml/soh_model.joblib
```

### Running tests

```bash
cd backend
source venv/bin/activate
python -m pytest tests/ -v
```

43 tests cover the TCO calculator, SOH estimator, policy retrieval, and
recommendation scoring — all pure-function / deterministic-logic tests,
no network or LLM calls involved.

## Database note

The MVP reads seed data directly from JSON/CSV files under `data/` and
`ml/` rather than a database — there was no need for SQLite yet since
nothing is written back at runtime. The synopsis calls for SQLite for the
MVP with a swap-in path to PostgreSQL later; the service-layer boundary
(`app/services/*.py`) is exactly where a SQLite-backed catalog/store would
slot in without touching the routes or the frontend.

## Data disclaimers

- `data/ev_models.json` — illustrative/representative specs, **not**
  verified against current manufacturer price lists.
- `data/tco_assumptions.json` — illustrative constants (electricity price,
  subsidy rules, maintenance/insurance %, loan terms), **not** official or
  current tariffs/subsidy figures.
- `data/policy_corpus/*.md` — illustrative summaries written for this demo,
  **not** verified against current government notifications.

Sourcing real, current, verified data for all three is a "Later" task —
see ARCHITECTURE.md.
