# backend/models/validation_result.py

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class VerificationStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    NEEDS_REVIEW = "needs_review"


class QualityResult(BaseModel):
    overall_score: float = 0.0
    is_acceptable: bool = False
    checks: Dict[str, Any] = Field(default_factory=dict)
    # ← FIXED: feedback is Dict[str, str] not str
    feedback: Dict[str, str] = Field(default_factory=dict)
    processing_time: float = 0.0

    @property
    def status(self) -> str:
        if self.is_acceptable and self.overall_score >= 70:
            return "accepted"
        if self.overall_score >= 50:
            return "warning"
        return "rejected"


class OCRResult(BaseModel):
    raw_text: str = ""
    confidence: float = 0.0
    language_detected: str = "unknown"
    processing_time: float = 0.0
    # Document authenticity
    is_valid_document: bool = True
    rejection_reason: Optional[str] = None
    # Raw fields from LLM (passed to field_extractor)
    extracted_fields_raw: dict = Field(default_factory=dict)


class ExtractedFields(BaseModel):
    document_type: str = "unknown"
    # Common
    name: Optional[str] = None
    name_local: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    # Bank passbook
    account_number: Optional[str] = None
    ifsc_code: Optional[str] = None
    bank_name: Optional[str] = None
    branch_name: Optional[str] = None
    # Aadhaar
    aadhaar_number: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    pincode: Optional[str] = None
    # Land record
    survey_number: Optional[str] = None
    village: Optional[str] = None
    taluka: Optional[str] = None
    district: Optional[str] = None
    area_hectares: Optional[str] = None
    land_type: Optional[str] = None
    # Catch-all
    raw_fields: Dict[str, Any] = Field(default_factory=dict)


class MatchResult(BaseModel):
    field: str
    extracted: Optional[str] = None
    database: Optional[str] = None
    score: float = 0.0
    match_type: str = "no_match"


class FuzzyMatchReport(BaseModel):
    farmer_id: Optional[str] = None
    farmer_name: Optional[str] = None
    lookup_method: str = "none"
    field_scores: Dict[str, float] = Field(default_factory=dict)
    overall_score: float = 0.0
    verdict: str = "no_match"
    message: str = ""


class FraudResult(BaseModel):
    risk_score: float = 0.0
    risk_level: str = "low"
    is_suspicious: bool = False
    flags: List[str] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)
    processing_time: float = 0.0


class VerificationResult(BaseModel):
    request_id: str = ""
    document_type: str = "unknown"
    farmer_id: Optional[str] = None
    status: VerificationStatus = VerificationStatus.PENDING
    quality: Optional[QualityResult] = None
    ocr: Optional[OCRResult] = None
    extracted_fields: Optional[ExtractedFields] = None
    match_report: Optional[FuzzyMatchReport] = None
    fraud: Optional[FraudResult] = None
    message: str = ""
    processing_time: float = 0.0