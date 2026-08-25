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

Example:

```bash
curl -X POST http://localhost:8000/api/contracts/analyze-text \
  -H "Content-Type: application/json" \
  -d "{\"filename\":\"sample.txt\",\"text\":\"Customer: Acme Corp. ACV $500,000. Contract term 24 months. Discount 30%. Variable cost 42%. Support cost $80,000. Payment terms Net 90. Usage commitment $200,000. Liability cap 2x.\"}"
```

## Architecture Principle

LLMs may interpret language, identify ambiguity, propose scenarios, explain risk, and recommend alternative structures. They must not perform core financial arithmetic. The deterministic simulation engine owns revenue, cost, margin, downside exposure, thresholds, scoring, and comparisons.
