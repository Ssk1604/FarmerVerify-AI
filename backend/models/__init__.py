# backend/models/__init__.py

from backend.models.validation_result import (
    QualityResult,
    OCRResult,
    ExtractedFields,
    MatchResult,
    FuzzyMatchReport,
    FraudResult,
    VerificationStatus,
    VerificationResult,
)

from backend.models.farmer import Farmer
from backend.models.document import Document, DocumentType, DocumentStatus

__all__ = [
    "QualityResult",
    "OCRResult",
    "ExtractedFields",
    "MatchResult",
    "FuzzyMatchReport",
    "FraudResult",
    "VerificationStatus",
    "VerificationResult",
    "Farmer",
    "Document",
    "DocumentType",
    "DocumentStatus",
]