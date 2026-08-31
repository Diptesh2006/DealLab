# DealLab

AI deal engineering for enterprise contracts.

DealLab helps B2B Deal Desk, Revenue Operations, and Commercial Finance teams evaluate whether a proposed enterprise contract is economically safe before signature. The MVP separates language interpretation from financial arithmetic: AI-assisted extraction and explanation live in service boundaries, while revenue, cost, margin, exposure, scoring, and before/after comparisons are deterministic backend responsibilities.

## Stack

- Frontend: Next.js 14, TypeScript, Tailwind CSS, Recharts-ready
- Backend: FastAPI, Pydantic
- Database: SQLite via `DATABASE_URL`, isolated for future PostgreSQL/Supabase replacement
- AI: OpenAI API boundary prepared through service modules
- PDF parsing: PyMuPDF

## Project Structure

```text
backend/
  app/
    api/              FastAPI routes
    audit/            Evidence and audit events
    core/             Configuration
    db/               SQLite connection and schema
    models/           Pydantic request, response, and deal models
    optimization/     Fragility detection and recommendations
    services/         Ingestion, extraction, scenario generation
    simulation/       Deterministic economic engine
frontend/
  src/
    app/              Next.js app router pages
    components/       UI components
    lib/              API client helpers
```

## Run Locally

1. Create environment files:

```bash
cp .env.example .env
```

2. Start the backend:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cd ..
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

3. Start the frontend in another terminal:

```bash
cd frontend
npm install
npm run dev
```

4. Open `http://localhost:3000`.

The frontend calls `GET http://localhost:8000/api/health` and displays live backend/database readiness.

## API

- `GET /api/health`: verifies service and database readiness.
- `POST /api/contracts/analyze-text`: stores contract text, extracts commercial terms, runs deterministic stress scenarios, records an audit event, and returns deal health.
- `POST /api/economics/evaluate`: evaluates one reviewed scenario through deterministic Python formulas.
- `POST /api/stress-tests/evaluate`: generates the default stress-test scenario set, evaluates each scenario through the deterministic economics engine, and returns deal health.
- `POST /api/deals/optimize`: creates bounded commercial change candidates, evaluates combinations through the stress-test engine, and returns ranked optimization options.

Example:

```bash
curl -X POST http://localhost:8000/api/contracts/analyze-text \
  -H "Content-Type: application/json" \
  -d "{\"filename\":\"sample.txt\",\"text\":\"Customer: Acme Corp. ACV $500,000. Contract term 24 months. Discount 30%. Variable cost 42%. Support cost $80,000. Payment terms Net 90. Usage commitment $200,000. Liability cap 2x.\"}"
```

## Architecture Principle

LLMs may interpret language, identify ambiguity, propose scenarios, explain risk, and recommend alternative structures. They must not perform core financial arithmetic. The deterministic simulation engine owns revenue, cost, margin, downside exposure, thresholds, scoring, and comparisons.

## Stress-Test Health Rating

The MVP generates ten plausible commercial scenarios: conservative adoption, expected adoption, high adoption, support-heavy customer, infrastructure-cost increase, renewal, discount expiry, SLA degradation, high adoption plus high support, and downside commercial scenario.

Each scenario includes usage multiplier, support hours, cost multiplier, renewal year, discount state, SLA performance, customer growth rate, commercial events, and source labels. Synthetic historical data is labeled as `synthetic historical benchmark`.

Health scoring is configurable through `DealHealthConfig`:

- Scenario passes when gross margin is at or above `target_margin_percent`.
- Scenario is a warning when it is below target but less than `critical_margin_gap_percent` below target.
- Scenario is critical when it is at least `critical_margin_gap_percent` below target.
- `Healthy`: pass rate >= `healthy_min_pass_rate`, no critical scenarios, and worst margin no more than `warning_margin_gap_percent` below target.
- `Mostly Healthy`: pass rate >= `mostly_healthy_min_pass_rate` and at most one critical scenario.
- `Commercially Fragile`: pass rate >= `fragile_min_pass_rate`.
- `High Risk`: anything below the fragile threshold.

## Optimization Engine

`Optimize Deal` uses a hybrid architecture boundary:

- AI-facing boundary: identify sensible commercial variables to consider, such as price, usage caps, discounts, support limits, renewal uplift, SLA credits, and minimum commitments.
- Backend optimizer: creates bounded candidate changes, evaluates combinations deterministically, and ranks options.
- Recommendation text: explains the deterministic results rather than inventing new financial outcomes.

The MVP optimizer limits changed clauses to one or two by default. It favors options that increase healthy scenario coverage, expected margin, and downside margin while penalizing base price increases, higher commercial friction, and unnecessary clause changes.
