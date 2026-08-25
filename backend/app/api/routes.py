from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, File, UploadFile

from backend.app.audit.evidence import record_event
from backend.app.core.config import get_settings
from backend.app.db.connection import get_connection
from backend.app.models.api import ContractAnalysisResponse, ContractTextRequest, HealthResponse
from backend.app.models.deal import DealAnalysis
from backend.app.optimization.engine import health_score, identify_fragile_terms, recommend_changes
from backend.app.services.contract_ingestion import extract_text_from_pdf, normalize_contract_text
from backend.app.services.scenario_generation import generate_stress_scenarios
from backend.app.services.term_extraction import extract_commercial_terms
from backend.app.simulation.engine import evaluate_deal

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    with get_connection() as connection:
        connection.execute("SELECT 1")
    return HealthResponse(status="ok", service=get_settings().app_name, database="ready")


@router.post("/contracts/analyze-text", response_model=ContractAnalysisResponse)
def analyze_contract_text(payload: ContractTextRequest) -> ContractAnalysisResponse:
    return _analyze_contract_text(payload.text, payload.filename)


@router.post("/contracts/analyze-pdf", response_model=ContractAnalysisResponse)
async def analyze_contract_pdf(file: UploadFile = File(...)) -> ContractAnalysisResponse:
    suffix = Path(file.filename or "contract.pdf").suffix or ".pdf"
    with NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(await file.read())
        temp_path = Path(temp_file.name)

    try:
        text = extract_text_from_pdf(temp_path)
    finally:
        temp_path.unlink(missing_ok=True)

    return _analyze_contract_text(text, file.filename)


def _analyze_contract_text(text: str, filename: str | None) -> ContractAnalysisResponse:
    normalized_text = normalize_contract_text(text)
    terms = extract_commercial_terms(normalized_text)
    scenarios = generate_stress_scenarios(terms)
    results = evaluate_deal(terms, scenarios)
    fragile_terms = identify_fragile_terms(terms, results)
    recommendations = recommend_changes(terms, results)
    score = health_score(results, fragile_terms)

    with get_connection() as connection:
        contract_cursor = connection.execute(
            "INSERT INTO contracts (filename, raw_text) VALUES (?, ?)",
            (filename, normalized_text),
        )
        contract_id = int(contract_cursor.lastrowid)
        terms_cursor = connection.execute(
            """
            INSERT INTO deal_terms (
                contract_id, customer_name, annual_contract_value, term_months,
                discount_percent, usage_commitment, variable_cost_percent, support_cost,
                payment_terms_days, auto_renewal, liability_cap_multiplier
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                contract_id,
                terms.customer_name,
                terms.annual_contract_value,
                terms.term_months,
                terms.discount_percent,
                terms.usage_commitment,
                terms.variable_cost_percent,
                terms.support_cost,
                terms.payment_terms_days,
                int(terms.auto_renewal),
                terms.liability_cap_multiplier,
            ),
        )
        deal_terms_id = int(terms_cursor.lastrowid)
        connection.execute(
            """
            INSERT INTO simulation_runs (deal_terms_id, health_score, recommendation_summary)
            VALUES (?, ?, ?)
            """,
            (deal_terms_id, score, " ".join(recommendations)),
        )

    record_event("contract", contract_id, "analyze_text", "Terms extracted, simulated, and stored.")

    return ContractAnalysisResponse(
        contract_id=contract_id,
        deal_terms_id=deal_terms_id,
        analysis=DealAnalysis(
            terms=terms,
            scenarios=results,
            health_score=score,
            fragile_terms=fragile_terms,
            recommendations=recommendations,
        ),
    )
