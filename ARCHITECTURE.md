# ARCHITECTURE — MVP vs. Full FF-180 Synopsis

This document maps what's actually built in this repo back to each
component of the original project synopsis (FF No. 180, Group 42), so a
reviewer/guide can see exactly how the partial MVP build relates to the
full proposed system.

## 1. EV Knowledge Base

| | Synopsis | This MVP |
|---|---|---|
| Scope | 10–15 Indian EV models | 5 seed models |
| Storage | Structured knowledge base | Single JSON file (`data/ev_models.json`) |
| Data quality | Verified, current specs | Illustrative/representative, explicitly disclaimed |

**Why this shape:** a small, fast seed set was prioritized so the rest of
the pipeline (TCO, SOH, recommendation) could be built and demoed
end-to-end quickly. The catalog lives behind `app/services/ev_catalog.py`,
so swapping the JSON file for a real database-backed catalog with 10–15+
verified models later only touches that one module.

**Later:** replace `data/ev_models.json` with a SQLite table (or external
API) of verified specs; `ev_catalog.py`'s function signatures
(`list_ev_models()`, `get_ev_model(id)`) shouldn't need to change.

## 2. Retrieval-Augmented Generation (Policy/Regulatory Q&A)

| | Synopsis | This MVP |
|---|---|---|
| Embeddings | sentence-transformers (or similar local model) | scikit-learn `TfidfVectorizer` |
| Vector store | Chroma | In-memory cosine-similarity search over a cached TF-IDF matrix |
| Corpus | Live government sources, with freshness/staleness tracking | 7 hand-written illustrative markdown docs |
| Answer generation | LLM synthesizes an answer from retrieved chunks, with citations | Top-matching chunk(s) returned **verbatim**, with citation + `last_verified` date |
| Freshness tracking | Full staleness detection against live sources | A static `last_verified` date per document, no live checking |

**Why this shape:** this build environment has no network access to
download an embedding model from Hugging Face, so TF-IDF was used as a
drop-in, fully local substitute — it needs no external downloads and no
API key. It's a materially weaker retriever than sentence-transformer
embeddings (no semantic/synonym matching, only term overlap), but the
*architecture* — embed corpus once, embed query, rank by similarity, cite
sources — is the same, and the swap point is isolated to
`build_index()`/`retrieve()` in `backend/app/services/policy_rag.py`.

The decision to return retrieved text **verbatim** rather than having an
LLM paraphrase/synthesize it was deliberate, not just a limitation: it
guarantees the "no hallucination" principle holds for the Q&A module too,
not just the numeric modules. Wiring in an LLM to produce a more natural
answer *grounded in* the same retrieved chunks (with the same citations
attached) is a clearly-scoped "Later" upgrade — see the TODO-style note in
`policy_rag.py`'s module docstring.

**Later:**
1. Swap `TfidfVectorizer` for `sentence-transformers` + `Chroma` (needs
   network access to pull the embedding model).
2. Replace the sample corpus with real, sourced government documents, and
   add a job that periodically re-checks source pages against
   `last_verified` to flag staleness.
3. Optionally add an LLM answer-generation step on top of retrieval
   (with an API key), keeping the same citation/source structure.

## 3. Agentic AI Orchestration (Policy / Specification / Battery / Cost / Recommendation agents)

| | Synopsis | This MVP |
|---|---|---|
| Architecture | An orchestrator coordinates 5 specialized agents | Backend routes call 4 service modules directly |
| Coordination | Agent-to-agent handoff / planning | None — a single Python function (`recommend.generate_recommendations`) calls the other services in sequence |

**Why this shape:** building a real orchestration layer before the
underlying capabilities exist would mean orchestrating stubs. Instead, the
MVP focuses on making each capability (spec lookup, TCO math, SOH
estimate, policy retrieval) solid and independently callable, with a
**clean service-layer boundary**: every module in `backend/app/services/`
is a plain Python module with no FastAPI/HTTP imports, callable directly
by anything — including a future orchestrator agent — without going
through HTTP.

Conceptually, today's implicit "orchestrator" is just
`recommend.generate_recommendations()`, and the implicit "agents" are:

- Specification Agent → `ev_catalog.py`
- Cost Agent → `tco_calculator.py`
- Battery Agent → `soh_estimator.py`
- Policy Agent → `policy_rag.py`
- Recommendation Agent → `recommend.py`

**Later:** introduce a real orchestrator (e.g. a lightweight agent
framework, or a single LLM with tool-calling access to these same service
functions as "tools") that can plan multi-step queries across modules
(e.g. "compare the TCO of my top 2 SOH-healthy options under ₹15L")
instead of the single fixed recommendation flow implemented today.

## 4. ML-based Battery SOH Estimation

| | Synopsis | This MVP |
|---|---|---|
| Data | Real fleet / indirect usage data | Synthetic data (`ml/generate_synthetic_data.py`) |
| Features | age, mileage, charging behaviour, climate | Same four features, same categories |
| Model | Not specified in detail | `RandomForestRegressor` (scikit-learn) |
| Validation | Presumably against real held-out fleet data | Train/test split on synthetic data only (R² ≈ 0.85, MAE < 1 pt on synthetic test set — **not** a claim about real-world accuracy) |

**Why this shape:** no real fleet/BMS-adjacent dataset was available for
this MVP, so a synthetic generator encodes plausible, hand-authored
degradation relationships (calendar aging, cycling aging, fast-charge
stress, climate multiplier) with noise, and the model is trained on that.
This proves out the full pipeline — feature schema, training script, saved
artifact, serving endpoint — without overclaiming real-world predictive
accuracy.

**Later:** replace `ml/generate_synthetic_data.py`'s output with a real
(anonymized) dataset of vehicles with known SOH labels; the training
script (`ml/train_soh_model.py`) and serving code
(`app/services/soh_estimator.py`) should need only column-name-level
changes, not a redesign.

## 5. Explainable AI (SHAP) for SOH predictions

| | Synopsis | This MVP |
|---|---|---|
| XAI method | SHAP | Not implemented — stub only |

`app/services/soh_estimator.py::explain_soh()` is a stub function that
returns `{"status": "not_implemented"}`. Its docstring includes the
concrete `shap.TreeExplainer` code that would replace it, including the
detail that matters for *this* model: because the trained pipeline is
`ColumnTransformer → RandomForestRegressor`, the explainer needs to be
built on `pipeline.named_steps["model"]` using the *already-transformed*
(one-hot-encoded) feature matrix, then the SHAP values need to be mapped
back to human-readable feature names for the API response.

**Later:** implement the explainer as sketched, and extend
`/soh/explain` (already routed, currently calling the stub) to return
per-feature contribution values the frontend can render as a small bar
chart.

## 6. Deterministic TCO Calculator

| | Synopsis | This MVP |
|---|---|---|
| Scope | Purchase, subsidy, running, maintenance, insurance, resale | All six, fully implemented |
| Implementation | Deterministic | Fully deterministic pure functions (`tco_calculator.py`), 20 unit tests |

This module is essentially **built to full synopsis scope** already,
just with illustrative constants (`data/tco_assumptions.json`) rather than
sourced, current figures. The math (subsidy rules, declining-value
insurance, straight-line resale with a floor, standard loan amortization)
is real and correct; what's marked "Later" is only the *input data*, not
the calculation logic.

**Later:** replace the constants in `data/tco_assumptions.json` with
sourced, current, state-by-state figures (including the road tax/
registration exemptions noted but not yet modeled — see
`data/policy_corpus/ev_registration_road_tax.md`).

## 7. Personalized Recommendations (Weighted Scoring / MCDM)

| | Synopsis | This MVP |
|---|---|---|
| Method | Weighted scoring / MCDM | Weighted-sum scoring over min-max normalized criteria |
| Transparency | Not specified | Weights are shown and adjustable by the user in the UI |

**Why this shape:** a transparent, adjustable weighted-sum is the simplest
MCDM-family method and satisfies the MVP brief's request for "a simple,
transparent formula (show the weights and let the user adjust them)". It
normalizes cost (TCO, lower is better), range, projected battery health,
and charging speed, each to `[0, 1]`, then combines them by user-set
weights (normalized to sum to 1 internally).

**Later:** upgrade to a fuller MCDM method (e.g. TOPSIS or AHP-derived
weights) if the simple weighted-sum proves too coarse, and extend the
criteria set as more knowledge-base fields are added (e.g. service network
size, model year, real resale-market data).

## 8. Database

| | Synopsis | This MVP |
|---|---|---|
| Storage | SQLite (MVP), Postgres (later) | Flat JSON/CSV files under `data/` and `ml/` |

Nothing in the MVP writes data back at runtime (all requests are
read-and-compute), so a database wasn't strictly needed yet. The
service-layer boundary is exactly where a SQLite-backed store would slot
in — `ev_catalog.py`, `tco_calculator.py`'s assumption loader, and
`policy_rag.py`'s corpus loader would each swap their `open()`/`json.load()`
calls for SQLite queries without changing their public function
signatures, so the routes and frontend wouldn't need to change at all.

## 9. Not built (out of scope for this pass)

- Production authentication
- Deployment configuration (Docker stubs are fine per the brief, but none
  were added since they weren't required to run the MVP)
- Monitoring/observability
