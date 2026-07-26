"""
FarmerVerify AI — Document Data Models
Defines structures for document upload, processing, and storage.
"""
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum





class DocumentType(str, Enum):
    BANK_PASSBOOK = "bank_passbook"
    LAND_RECORD = "land_record"
    AADHAAR = "aadhaar_card"       # canonical name used throughout pipeline
    VOTER_ID = "voter_id"
    OTHER = "other"


class DocumentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    QUALITY_FAILED = "quality_failed"
    OCR_COMPLETE = "ocr_complete"
    VALIDATION_PENDING = "validation_pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVIEW_NEEDED = "review_needed"
    FRAUD_ALERT = "fraud_alert"


class DocumentUploadRequest(BaseModel):
    """
    What we receive when farmer uploads a document.
    
    Example:
    {
        "farmer_phone": "9999999999",
        "document_type": "bank_passbook",
        "language": "hi"
    }
    """
    
    farmer_phone: str = Field(
        description="Farmer's phone number"
    )
    
    document_type: DocumentType = Field(
        default=DocumentType.BANK_PASSBOOK,
        description="Type of document being uploaded"
    )
    
    language: str = Field(
        default="hi",
        description="Document language (hi/mr/en)"
    )


class Document(BaseModel):
    """
    Complete document record stored in database.
    
    This tracks everything about a document from upload to approval.
    """
    
    id: str = Field(
        description="Unique document ID (e.g., DOC_2026_001247)"
    )
    
    farmer_id: Optional[str] = Field(
        default=None,
        description="Linked farmer ID"
    )
    
    farmer_phone: str = Field(
        description="Farmer's phone number"
    )
    
    document_type: DocumentType = Field(
        description="Type of document"
    )
    
    image_path: str = Field(
        description="Path to uploaded image file"
    )
    
    status: DocumentStatus = Field(
        default=DocumentStatus.PENDING,
        description="Current processing status"
    )
    
    quality_score: Optional[float] = Field(
        default=None,
        description="Image quality score (0-100)"
    )
    
    quality_issues: List[str] = Field(
        default=[],
        description="List of quality issues found"
    )
    
    ocr_text: Optional[str] = Field(
        default=None,
        description="Raw text extracted by OCR"
    )
    
    extracted_fields: Optional[dict] = Field(
        default=None,
        description="Structured fields extracted from OCR text"
    )
    
    validation_confidence: Optional[float] = Field(
        default=None,
        description="Overall validation confidence (0-100)"
    )
    
    fraud_risk_score: Optional[float] = Field(
        default=None,
        description="Fraud risk score (0-100)"
    )
    
    language_detected: Optional[str] = Field(
        default=None,
        description="Language detected in document"
    )
    
    processing_time: Optional[float] = Field(
        default=None,
        description="Total processing time in seconds"
    )
    
    uploaded_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Upload timestamp"
    )
    
    processed_at: Optional[datetime] = Field(
        default=None,
        description="Processing completion timestamp"
    )
    
    reviewed_by: Optional[str] = Field(
        default=None,
        description="Staff member who reviewed (if manual review)"
    )
    
    notes: Optional[str] = Field(
        default=None,
        description="Any additional notes"
    )