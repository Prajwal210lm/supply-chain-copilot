# Supply Chain Copilot

[![CI](https://github.com/Prajwal210lm/supply-chain-copilot/actions/workflows/ci.yml/badge.svg)](https://github.com/Prajwal210lm/supply-chain-copilot/actions/workflows/ci.yml)

**The answer is in the data. Getting it out takes days.**

When on-time-in-full slips at a distributor like Mawarid, the demand planner's question —
*why?* — becomes a ticket, an Excel pull, and a meeting sometime next week. This project
closes that gap: a conversational interface over the operational data where a model turns a
plain-English question into a typed, inspectable query spec — never SQL — and deterministic
code compiles it, executes it against a read-only database, and narrates the result under a
render gate that withholds any number it can't trace back to that computation. Built around a
fictional GCC distributor (Mawarid Distribution); all data synthetic.

**Live:** [supply-chain-copilot-nine.vercel.app](https://supply-chain-copilot-nine.vercel.app) ·
API: [supply-chain-copilot-production.up.railway.app](https://supply-chain-copilot-production.up.railway.app/api/health)

## Headline numbers

Measured over four independent runs of the 80-question golden set ($8.04 of tokens), before deploy:

| Slice | Accuracy |
|---|---|
| Clean questions | **96.7%** (stable across all four runs) |
| Near-miss disambiguation | **93.3%** (range 86.7–93.3%) |
| Multi-turn follow-ups | **100%** |
| Adversarial & injection | **100%** (deploy-blocking gate) |
| Unnecessary clarifications | **0%** |

Two known misses are disclosed on the site rather than averaged away — see the Measurement
section on the live page.

## The pipeline

```
question ──▶ interpret ──▶ validate ──▶ compile ──▶ execute ──▶ narrate ──▶ render gate
             (model)       6 checks    param. SQL   read-only    (model)    every number
             emits a       V1–V6                    database                traced
             typed spec
```

Two model calls; everything else is deterministic code. The model never writes SQL — it can
only emit a typed `QuerySpec` (metric, window, dimension, filters) that six validators check
against the catalog, which makes prompt injection a type error rather than a filtered attack.
The model never computes a number — a compiler turns the validated spec into parameterized
SQL, and change decompositions carry an exact-residual gate: if member contributions don't sum
to the total change, the breakdown is withheld and only totals show. The model never shows an
unverifiable number — narration passes a render gate that requires every figure to be a
placeholder traced to the computed result; a bare digit gets the whole paragraph withheld
while the chart, which never depended on the model, still renders.

## Quickstart

```bash
git clone https://github.com/Prajwal210lm/supply-chain-copilot.git
cd supply-chain-copilot

# Backend
python -m venv .venv
.venv\Scripts\activate          # Windows   (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
pytest                          # fully mocked, no API key needed
uvicorn copilot.api:app --port 8000

# Frontend (second terminal)
cd frontend
npm install
npm run dev                     # http://localhost:3000
```

Everything works without a key: tests are mocked, and `GET /api/demo` serves a saved
five-turn conversation produced by real pipeline runs. Setting `ANTHROPIC_API_KEY` and
`API_SECRET` (see `.env.example`) enables live questions against `POST /api/ask` — not yet
wired to the frontend's input, which ships in a later iteration.

## Architecture

```
copilot/
  spec.py            Pydantic QuerySpec models — the only shape the model can emit
  stage1.py           NL -> QuerySpec: locked system prompt, catalog rendered from registry.py
  validate.py         V1-V6: structural, compatibility, decomposability, window, resolution, caps
  resolve.py           Entity resolution (fuzzy match against the catalog, calibrated thresholds)
  compile.py           Spec -> parameterized SQL, two-channel rule enforced by AST-grep test
  decompose.py         Contribution math + the exact-residual gate
  results.py           The result contract every narration/chart addresses by dot-path
  narrate.py            Result -> paragraph, render-gated (R1-R4)
  chart.py              Deterministic chart-type selection from spec shape
  pipeline.py            End-to-end orchestration: interpret -> compile -> execute -> narrate
  api.py                  FastAPI surface: health, catalog, demo, ask (secret-gated, rate-limited)
data/
  mawarid.duckdb           Seeded synthetic database, read-only at request time
  demo_conversation.json    Saved output of five real pipeline runs — the deploy's demo path
eval/
  golden_set.yaml            80 hand-written questions, frozen before Stage 1 existed
  harness.py                  Live-API evaluation runner (never wired into CI)
frontend/                      Next.js app: the conversation, architecture, and measurement
```

## Deployment

Backend on Railway (Docker, read-only DuckDB baked into the image, no volume). Frontend on
Vercel (root directory `frontend/`). `FRONTEND_ORIGIN` on the backend and
`NEXT_PUBLIC_API_URL` on the frontend point at each other; CORS is pinned to the exact origin,
no wildcard. `POST /api/ask` fails closed (503) if either `ANTHROPIC_API_KEY` or `API_SECRET`
is unset, gates on the secret header (403), and rate-limits per IP and per day (429).

## The series

- [P1 — Liquidity Lens](https://supply-chain-liquidity-lens.vercel.app)
- [P2 — Supplier Resilience Radar](https://supplier-resilience-radar.vercel.app)
- [P3 — OTIF Root-Cause Engine](https://otif-root-cause-engine.vercel.app)
- P4 — Supply Chain Copilot (this repo)

All data synthetic. Mawarid Distribution is fictional.
