from pathlib import Path
from tempfile import NamedTemporaryFile
import json

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from backend.app.audit.evidence import record_event
from backend.app.core.config import get_settings
from backend.app.db.connection import get_connection
from backend.app.models.api import ContractAnalysisResponse, ContractTextRequest, HealthResponse
from backend.app.models.deal import DealAnalysis
from backend.app.models.intelligence import (
    DealDocument,
    DealIntelligenceResponse,
    DocumentType,
    EffectiveTerm,
    ManualTermEditRequest,
    ManualTermEditResponse,
    ReviewStatus,
)
from backend.app.optimization.engine import health_score, identify_fragile_terms, recommend_changes
from backend.app.services.contract_ingestion import extract_text_from_pdf, normalize_contract_text
from backend.app.services.commercial_intelligence import SourceDocument, derive_effective_terms
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


@router.post("/deals/analyze", response_model=DealIntelligenceResponse)
async def analyze_deal(
    customer_name: str = Form(...),
    deal_name: str = Form(...),
    target_gross_margin: float = Form(...),
    internal_cost_assumptions: str | None = Form(default=None),
    main_contract: UploadFile = File(...),
    amendments: list[UploadFile] | None = File(default=None),
    exception_notes: list[UploadFile] | None = File(default=None),
) -> DealIntelligenceResponse:
    documents = await _read_ordered_documents(main_contract, amendments or [], exception_notes or [])
    effective_terms = derive_effective_terms(
        [
            SourceDocument(
                filename=document["filename"],
                document_type=document["document_type"],
                precedence_order=document["precedence_order"],
                text=document["raw_text"],
            )
            for document in documents
        ]
    )

    with get_connection() as connection:
        deal_cursor = connection.execute(
            """
            INSERT INTO deals (customer_name, deal_name, target_gross_margin, internal_cost_assumptions)
            VALUES (?, ?, ?, ?)
            """,
            (customer_name, deal_name, target_gross_margin, internal_cost_assumptions),
        )
        deal_id = int(deal_cursor.lastrowid)

        persisted_documents: list[DealDocument] = []
        for document in documents:
            document_cursor = connection.execute(
                """
                INSERT INTO deal_documents (deal_id, filename, document_type, precedence_order, raw_text)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    deal_id,
                    document["filename"],
                    document["document_type"],
                    document["precedence_order"],
                    document["raw_text"],
                ),
            )
            persisted_documents.append(
                DealDocument(
                    id=int(document_cursor.lastrowid),
                    filename=document["filename"],
                    document_type=DocumentType(document["document_type"]),
                    precedence_order=document["precedence_order"],
                )
            )

        persisted_terms = [_insert_effective_term(connection, deal_id, term) for term in effective_terms]

    record_event(
        "deal",
        deal_id,
        "analyze_deal",
        json.dumps(
            {
                "document_count": len(persisted_documents),
                "term_count": len(persisted_terms),
                "target_gross_margin": target_gross_margin,
            }
        ),
    )

    return DealIntelligenceResponse(
        deal_id=deal_id,
        customer_name=customer_name,
        deal_name=deal_name,
        target_gross_margin=target_gross_margin,
        documents=persisted_documents,
        effective_terms=persisted_terms,
    )


@router.patch("/deals/{deal_id}/terms/{term_id}", response_model=ManualTermEditResponse)
def update_effective_term(deal_id: int, term_id: int, payload: ManualTermEditRequest) -> ManualTermEditResponse:
    with get_connection() as connection:
        existing = connection.execute(
            "SELECT * FROM effective_terms WHERE id = ? AND deal_id = ?",
            (term_id, deal_id),
        ).fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail="Effective term not found")

        connection.execute(
            """
            UPDATE effective_terms
            SET normalized_value = ?, unit = ?, review_status = ?, ambiguous = 0, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND deal_id = ?
            """,
            (payload.normalized_value, payload.unit, ReviewStatus.confirmed.value, term_id, deal_id),
        )
        updated = connection.execute(
            "SELECT * FROM effective_terms WHERE id = ? AND deal_id = ?",
            (term_id, deal_id),
        ).fetchone()

    record_event(
        "effective_term",
        term_id,
        "manual_edit",
        json.dumps(
            {
                "deal_id": deal_id,
                "field_name": existing["field_name"],
                "previous_value": existing["normalized_value"],
                "new_value": payload.normalized_value,
                "previous_unit": existing["unit"],
                "new_unit": payload.unit,
                "reason": payload.reason,
            }
        ),
    )
    return ManualTermEditResponse(term=_row_to_effective_term(updated))


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


async def _read_ordered_documents(
    main_contract: UploadFile,
    amendments: list[UploadFile],
    exception_notes: list[UploadFile],
) -> list[dict[str, object]]:
    ordered_uploads: list[tuple[UploadFile, str]] = [(main_contract, DocumentType.master_agreement.value)]
    ordered_uploads.extend((file, DocumentType.amendment.value) for file in amendments)
    ordered_uploads.extend((file, DocumentType.approved_exception.value) for file in exception_notes)

    documents: list[dict[str, object]] = []
    for index, (file, document_type) in enumerate(ordered_uploads):
        text = await _read_upload_text(file)
        if not text:
            raise HTTPException(status_code=422, detail=f"No readable text found in {file.filename}")
        documents.append(
            {
                "filename": file.filename or f"document-{index + 1}",
                "document_type": document_type,
                "precedence_order": index,
                "raw_text": normalize_contract_text(text),
            }
        )
    return documents


async def _read_upload_text(file: UploadFile) -> str:
    filename = file.filename or ""
    suffix = Path(filename).suffix.lower()
    content = await file.read()

    if suffix == ".pdf":
        with NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(content)
            temp_path = Path(temp_file.name)
        try:
            return extract_text_from_pdf(temp_path)
        finally:
            temp_path.unlink(missing_ok=True)

    return content.decode("utf-8", errors="ignore")


def _insert_effective_term(connection, deal_id: int, term: EffectiveTerm) -> EffectiveTerm:
    cursor = connection.execute(
        """
        INSERT INTO effective_terms (
            deal_id, field_name, normalized_value, unit, effective_from, source_document,
            source_page, evidence_excerpt, confidence, extraction_type, review_status, ambiguous
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            deal_id,
            term.field_name,
            term.normalized_value,
            term.unit,
            term.effective_from,
            term.source_document,
            term.source_page,
            term.evidence_excerpt,
            term.confidence,
            term.extraction_type.value,
            term.review_status.value,
            int(term.ambiguous),
        ),
    )
    return term.model_copy(update={"id": int(cursor.lastrowid)})


def _row_to_effective_term(row) -> EffectiveTerm:
    return EffectiveTerm(
        id=row["id"],
        field_name=row["field_name"],
        normalized_value=row["normalized_value"],
        unit=row["unit"],
        effective_from=row["effective_from"],
        source_document=row["source_document"],
        source_page=row["source_page"],
        evidence_excerpt=row["evidence_excerpt"],
        confidence=row["confidence"],
        extraction_type=row["extraction_type"],
        review_status=row["review_status"],
        ambiguous=bool(row["ambiguous"]),
    )
