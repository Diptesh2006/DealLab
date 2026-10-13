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

## Demo Dataset

A synthetic ACME Enterprise SaaS/API contract package is available in `demo/acme-enterprise`.
It includes PDF/text contracts, an amendment, an approved exception note, cost assumptions, scenario inputs, and deterministic benchmark outputs.

## API

- `GET /api/health`: verifies service and database readiness.
- `POST /api/contracts/analyze-text`: stores contract text, extracts commercial terms, runs deterministic stress scenarios, records an audit event, and returns deal health.
- `POST /api/economics/evaluate`: evaluates one reviewed scenario through deterministic Python formulas.
- `POST /api/stress-tests/evaluate`: generates the default stress-test scenario set, evaluates each scenario through the deterministic economics engine, and returns deal health.
- `POST /api/deals/optimize`: creates bounded commercial change candidates, evaluates combinations through the stress-test engine, and returns ranked optimization options.
- `POST /api/deals/prepare-revised-terms`: prepares a structured commercial recommendation artifact for human approval without modifying legal documents.
- `POST /api/deals/{deal_id}/billing/razorpay/prepare`: after an explicit human approval action, creates Razorpay **Test Mode** customer, plan, and subscription objects for the fixed recurring base charge and stores their IDs against the deal.

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

## Razorpay Test Mode

Set backend-only credentials in `.env` before using **Prepare Billing Setup**:

```env
RAZORPAY_KEY_ID=rzp_test_...
RAZORPAY_KEY_SECRET=...
```

The browser never receives the secret, and the backend rejects non-test keys. The integration maps only a fixed monthly or yearly recurring base charge. Metered overages, price caps, discounts, support limits, renewal escalation, SLA credits, and contract clauses are not represented as Razorpay-enforced contract terms; they remain in approved commercial and billing operations. Missing credentials return a clear `503` error without affecting contract analysis, stress testing, or optimization.

## 2-Minute Judge Demo

1. Start the backend and frontend, then open `http://localhost:3000`. Confirm the backend status reads ready.
2. Click **Load Demo Deal**. DealLab parses the synthetic ACME master agreement, amendment, and approved exception from PDF, stores the deal, and opens the Deal Terms Review table.
3. Point out the confirmed annual price, included usage, overage ceiling, temporary discount, unlimited support interpretation, and the amendment-driven first renewal uplift of `0%`. Unknown non-economic clauses remain visibly marked for review.
4. Review the loaded company assumptions, then click **Approve for Simulation** and **Run Stress Test**. The Deal Health dashboard shows scenario coverage, expected margin, downside margin, annual exposure, and critical failure modes.
5. Open the high-adoption and support-heavy scenario rows to show the deterministic financial breakdown and source labels. Use the failure-mode cards to connect the clause, scenario, calculation, and commercial consequence.
6. Click **Optimize Deal**. Compare Current Deal and Optimized Deal, with the changed terms, scenario coverage, annual exposure, customer impact, and trust trace shown side by side.
7. Click **Prepare Revised Terms**. Review the human-approval-only commercial recommendation; no contract document is changed.
8. With `RAZORPAY_KEY_ID=rzp_test_...` and `RAZORPAY_KEY_SECRET` configured on the backend, click **Prepare Billing Setup**. The preview shows the Test Mode fixed recurring billing configuration and IDs, while identifying usage, discount, support, SLA, and legal terms Razorpay does not enforce. Without keys, the clear credentials error demonstrates that the core DealLab workflow remains independent.
9. Click **Reset Workspace** to return to a clean new-deal screen for another run.
