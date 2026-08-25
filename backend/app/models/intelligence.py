from enum import Enum

from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    master_agreement = "master_agreement"
    amendment = "amendment"
    approved_exception = "approved_exception"


class ExtractionType(str, Enum):
    explicit = "explicit"
    inferred = "inferred"
    unknown = "unknown"


class ReviewStatus(str, Enum):
    confirmed = "confirmed"
    inferred = "inferred"
    requires_assumption = "requires_assumption"
    requires_human_review = "requires_human_review"


class EffectiveTerm(BaseModel):
    id: int | None = None
    field_name: str
    normalized_value: str
    unit: str
    effective_from: str | None = None
    source_document: str | None = None
    source_page: int | None = Field(default=None, ge=1)
    evidence_excerpt: str | None = None
    confidence: float = Field(ge=0, le=1)
    extraction_type: ExtractionType
    review_status: ReviewStatus
    ambiguous: bool


class DealDocument(BaseModel):
    id: int | None = None
    filename: str
    document_type: DocumentType
    precedence_order: int


class DealIntelligenceResponse(BaseModel):
    deal_id: int
    customer_name: str
    deal_name: str
    target_gross_margin: float
    documents: list[DealDocument]
    effective_terms: list[EffectiveTerm]


class ManualTermEditRequest(BaseModel):
    normalized_value: str = Field(min_length=1)
    unit: str = Field(min_length=1)
    reason: str = Field(default="Manual commercial review edit", min_length=1)


class ManualTermEditResponse(BaseModel):
    term: EffectiveTerm
