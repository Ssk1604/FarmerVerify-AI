"""
Upload endpoint – FarmerVerify AI
POST /upload/document
"""
from __future__ import annotations

import fitz  # PyMuPDF

import os
import time
import uuid
from pathlib import Path
from datetime import datetime, timezone
# ADD this import at top of upload.py
from backend.services.ocr_engine import extract_text, detect_page_type
from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from loguru import logger

from backend.services.quality_checker import check_quality

from backend.services.field_extractor import extract_fields
from backend.services.fuzzy_matcher import match_fields
from backend.services.fraud_detector import detect_fraud
from backend.database.document_store import (
    save_result,
    compute_fingerprint,
    find_existing_by_fingerprint,
    save_redirect,
)

router = APIRouter()

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf", ".webp"}
VALID_DOC_TYPES = {
    "aadhaar_card", "bank_passbook", "land_record",
    "voter_id", "cc_training_photo", "meeting_minutes",
}

_DOC_CONFIG = {
    "aadhaar_card": {
        "label":        {"en": "Aadhaar Card",  "hi": "आधार कार्ड",        "mr": "आधार कार्ड"},
        "quality_fail": {"en": "The Aadhaar card image is too blurry. Please retake in good lighting.",
                         "hi": "छवि बहुत धुंधली है। दोबारा फोटो लें।",
                         "mr": "प्रतिमा अस्पष्ट आहे. पुन्हा फोटो काढा."},
        "wrong_doc":    {"en": "This does not appear to be an Aadhaar card.",
                         "hi": "यह आधार कार्ड नहीं लगता।",
                         "mr": "हे आधार कार्ड नाही."},
        "ocr_fail":     {"en": "Could not read the Aadhaar card. Please upload a clearer image.",
                         "hi": "आधार कार्ड पढ़ा नहीं जा सका।",
                         "mr": "आधार कार्ड वाचता आले नाही."},
        "success":      {"en": "✅ Document submitted and verified automatically.",
                         "hi": "✅ दस्तावेज़ जमा और सत्यापित।",
                         "mr": "✅ दस्तऐवज सादर आणि सत्यापित."},
        "review":       {"en": "📤 Document uploaded successfully! Our team will review and verify it shortly.",
                         "hi": "📤 दस्तावेज़ अपलोड! टीम जल्द समीक्षा करेगी।",
                         "mr": "📤 दस्तऐवज अपलोड! टीम लवकरच पुनरावलोकन करेल."},
        "duplicate":    {"en": "ℹ️ This Aadhaar card has already been submitted.",
                         "hi": "ℹ️ यह आधार कार्ड पहले ही जमा हो चुका है।",
                         "mr": "ℹ️ हे आधार कार्ड आधीच सादर केले गेले आहे."},
        "rejected":     {"en": "❌ Aadhaar card rejected. Please upload a valid document.",
                         "hi": "❌ आधार कार्ड अस्वीकृत।",
                         "mr": "❌ आधार कार्ड नाकारले."},
    },
    "bank_passbook": {
        "label":        {"en": "Bank Passbook", "hi": "बैंक पासबुक",       "mr": "बँक पासबुक"},
        "quality_fail": {"en": "The bank passbook image is too blurry. Please retake.",
                         "hi": "छवि बहुत धुंधली है।", "mr": "प्रतिमा अस्पष्ट आहे."},
        "wrong_doc":    {"en": "This does not appear to be a bank passbook.",
                         "hi": "यह बैंक पासबुक नहीं लगता।", "mr": "हे बँक पासबुक नाही."},
        "ocr_fail":     {"en": "Could not read the passbook. Please upload a clearer image.",
                         "hi": "पासबुक पढ़ा नहीं जा सका।", "mr": "पासबुक वाचता आले नाही."},
        "success":      {"en": "✅ Bank passbook verified.", "hi": "✅ पासबुक सत्यापित।", "mr": "✅ पासबुक सत्यापित."},
        "review":       {"en": "📤 Bank passbook uploaded. Our team will verify shortly.",
                         "hi": "📤 पासबुक अपलोड।", "mr": "📤 पासबुक अपलोड."},
        "duplicate":    {"en": "ℹ️ This bank passbook has already been submitted.",
                         "hi": "ℹ️ यह पासबुक पहले ही जमा हो चुका है।", "mr": "ℹ️ हे पासबुक आधीच सादर केले."},
        "rejected":     {"en": "❌ Bank passbook rejected.", "hi": "❌ पासबुक अस्वीकृत।", "mr": "❌ पासबुक नाकारले."},
    },
    "land_record": {
        "label":        {"en": "Land Record", "hi": "भूमि अभिलेख", "mr": "जमीन नोंद"},
        "quality_fail": {"en": "The land record image is too blurry. Please retake.",
                         "hi": "छवि बहुत धुंधली है।", "mr": "प्रतिमा अस्पष्ट आहे."},
        "wrong_doc":    {"en": "This does not appear to be a land record.",
                         "hi": "यह भूमि अभिलेख नहीं लगता।", "mr": "ही जमीन नोंद नाही."},
        "ocr_fail":     {"en": "Could not read the land record. Please upload a clearer image.",
                         "hi": "भूमि अभिलेख पढ़ा नहीं जा सका।", "mr": "जमीन नोंद वाचता आली नाही."},
        "success":      {"en": "✅ Land record verified.", "hi": "✅ भूमि अभिलेख सत्यापित।", "mr": "✅ जमीन नोंद सत्यापित."},
        "review":       {"en": "📤 Land record uploaded. Our team will verify shortly.",
                         "hi": "📤 भूमि अभिलेख अपलोड।", "mr": "📤 जमीन नोंद अपलोड."},
        "duplicate":    {"en": "ℹ️ This land record has already been submitted.",
                         "hi": "ℹ️ यह भूमि अभिलेख पहले ही जमा हो चुका है।", "mr": "ℹ️ ही जमीन नोंद आधीच सादर केली."},
        "rejected":     {"en": "❌ Land record rejected.", "hi": "❌ भूमि अभिलेख अस्वीकृत।", "mr": "❌ जमीन नोंद नाकारली."},
    },
    "voter_id": {
        "label":        {"en": "Voter ID", "hi": "मतदाता पहचान पत्र", "mr": "मतदार ओळखपत्र"},
        "quality_fail": {"en": "The Voter ID image is too blurry. Please retake.",
                         "hi": "छवि बहुत धुंधली है।", "mr": "प्रतिमा अस्पष्ट आहे."},
        "wrong_doc":    {"en": "This does not appear to be a Voter ID.",
                         "hi": "यह मतदाता पहचान पत्र नहीं लगता।", "mr": "हे मतदार ओळखपत्र नाही."},
        "ocr_fail":     {"en": "Could not read the Voter ID. Please upload a clearer image.",
                         "hi": "मतदाता पहचान पत्र पढ़ा नहीं जा सका।", "mr": "मतदार ओळखपत्र वाचता आले नाही."},
        "success":      {"en": "✅ Voter ID verified.", "hi": "✅ मतदाता पहचान पत्र सत्यापित।", "mr": "✅ मतदार ओळखपत्र सत्यापित."},
        "review":       {"en": "📤 Voter ID uploaded. Our team will verify shortly.",
                         "hi": "📤 मतदाता पहचान पत्र अपलोड।", "mr": "📤 मतदार ओळखपत्र अपलोड."},
        "duplicate":    {"en": "ℹ️ This Voter ID has already been submitted.",
                         "hi": "ℹ️ यह मतदाता पहचान पत्र पहले ही जमा हो चुका है।", "mr": "ℹ️ हे मतदार ओळखपत्र आधीच सादर केले."},
        "rejected":     {"en": "❌ Voter ID rejected.", "hi": "❌ मतदाता पहचान पत्र अस्वीकृत।", "mr": "❌ मतदार ओळखपत्र नाकारले."},
    },
    "cc_training_photo": {
        "label":        {"en": "CC Training Photo", "hi": "CC प्रशिक्षण फोटो", "mr": "CC प्रशिक्षण फोटो"},
        "quality_fail": {"en": "The training photo is too blurry. Please retake.",
                         "hi": "फोटो बहुत धुंधला है।", "mr": "फोटो अस्पष्ट आहे."},
        "wrong_doc":    {"en": "This does not appear to be a CC training photo.",
                         "hi": "यह CC प्रशिक्षण फोटो नहीं लगता।", "mr": "हे CC प्रशिक्षण फोटो नाही."},
        "ocr_fail":     {"en": "Could not process the training photo.",
                         "hi": "फोटो प्रोसेस नहीं हो सका।", "mr": "फोटो प्रक्रिया करता आला नाही."},
        "success":      {"en": "📸 CC Training Photo verified! GPS and attendance confirmed.",
                         "hi": "📸 CC प्रशिक्षण फोटो सत्यापित!", "mr": "📸 CC प्रशिक्षण फोटो सत्यापित!"},
        "review":       {"en": "📤 CC Training Photo uploaded. Our team will verify attendance and GPS.",
                         "hi": "📤 CC फोटो अपलोड।", "mr": "📤 CC फोटो अपलोड."},
        "duplicate":    {"en": "ℹ️ This CC Training Photo has already been submitted.",
                         "hi": "ℹ️ यह CC फोटो पहले ही जमा हो चुका है।", "mr": "ℹ️ हे CC फोटो आधीच सादर केले."},
        "rejected":     {"en": "❌ CC Training Photo rejected. Minimum 2 people must be visible.",
                         "hi": "❌ CC फोटो अस्वीकृत। कम से कम 2 लोग दिखने चाहिए।",
                         "mr": "❌ CC फोटो नाकारला. किमान 2 लोक दिसले पाहिजेत."},
    },
    "meeting_minutes": {
        "label":        {"en": "Minutes of Meeting", "hi": "बैठक के मिनट्स", "mr": "बैठकीचे इतिवृत्त"},
        "quality_fail": {"en": "The document image is too blurry. Please retake.",
                         "hi": "छवि बहुत धुंधली है।", "mr": "प्रतिमा अस्पष्ट आहे."},
        "wrong_doc":    {"en": "This does not appear to be a Minutes of Meeting document.",
                         "hi": "यह बैठक के मिनट्स नहीं लगते।", "mr": "हे बैठकीचे इतिवृत्त नाही."},
        "ocr_fail":     {"en": "Could not process the minutes document.",
                         "hi": "मिनट्स प्रोसेस नहीं हो सके।", "mr": "इतिवृत्त प्रक्रिया करता आले नाही."},
        "success":      {"en": "📋 Minutes of Meeting processed. Attendee details extracted.",
                         "hi": "📋 मिनट्स प्रोसेस हुए।", "mr": "📋 इतिवृत्त प्रक्रिया झाली."},
        "review":       {"en": "📤 Minutes of Meeting uploaded. Team will verify attendance.",
                         "hi": "📤 मिनट्स अपलोड।", "mr": "📤 इतिवृत्त अपलोड."},
        "duplicate":    {"en": "ℹ️ This meeting minutes document has already been submitted.",
                         "hi": "ℹ️ यह मिनट्स पहले ही जमा हो चुके हैं।", "mr": "ℹ️ हे इतिवृत्त आधीच सादर केले."},
        "rejected":     {"en": "❌ Minutes of Meeting rejected.",
                         "hi": "❌ मिनट्स अस्वीकृत।", "mr": "❌ इतिवृत्त नाकारले."},
    },
}


async def split_pdf_to_images(file_bytes: bytes) -> list[bytes]:
    """
    Split a multi-page PDF into individual page images.
    Returns a list of PNG image bytes — one per page.
    """
    pdf_document = fitz.open(stream=file_bytes, filetype="pdf")
    page_images = []

    for page_number in range(len(pdf_document)):
        page = pdf_document[page_number]

        # Render at 2x resolution for OCR accuracy
        mat = fitz.Matrix(2.0, 2.0)
        pix = page.get_pixmap(matrix=mat)

        # Convert to PNG bytes
        img_bytes = pix.tobytes("png")
        page_images.append(img_bytes)

        logger.info(
            "PDF page extracted | page={}/{} | size={}bytes",
            page_number + 1,
            len(pdf_document),
            len(img_bytes)
        )

    pdf_document.close()
    return page_images

def _msg(msg_dict: dict | str, lang: str = "en") -> str:
    """
    Safely extract a message string from a dict or return the string directly.
    Handles both dict[lang -> str] and plain str config values.
    """
    if isinstance(msg_dict, str):
        return msg_dict
    if isinstance(msg_dict, dict):
        return msg_dict.get(lang) or msg_dict.get("en") or ""
    return ""

# ── Helper: Compute onboarding score ─────────────────────────────────────────
def _compute_onboarding_score(
    quality,
    ocr_result,
    extracted_dict: dict,
    matching_dict:  dict,
    fraud_dict:     dict,
    llm_validation: dict | None = None,
) -> dict:
    """
    Compute a 0-100 onboarding readiness score.
    Breakdown:
    - Image quality:        20 pts
    - OCR confidence:       30 pts
    - Fields extracted:     25 pts
    - Fraud check:          15 pts
    - DB match:             10 pts
    - LLM validation bonus:  5 pts (optional)
    """
    score = 0
    breakdown: dict[str, int] = {}

    # ── Quality (20 pts) ──────────────────────────────────────────────────────
    q     = float(getattr(quality, "overall_score", 0) or 0)
    q_pts = round((q / 100) * 20)
    score += q_pts
    breakdown["image_quality"] = q_pts

    # ── OCR confidence (30 pts) ───────────────────────────────────────────────
    conf = float(ocr_result.confidence or 0) if ocr_result else 0
    if conf <= 1.0:
        conf *= 100
    ocr_pts = round((conf / 100) * 30)
    score  += ocr_pts
    breakdown["ocr_confidence"] = ocr_pts

    # ── Fields extracted (25 pts) ─────────────────────────────────────────────
    non_null  = sum(
        1 for k, v in extracted_dict.items()
        if v
        and k not in ("document_type", "raw_fields", "raw_text")
        and str(v).strip().lower() not in ("", "none", "null")
    )
    field_pts = min(25, round(non_null * 3))
    score    += field_pts
    breakdown["fields_extracted"] = field_pts

    # ── Fraud check (15 pts) ──────────────────────────────────────────────────
    fraud_risk_val = float(fraud_dict.get("risk_score", 0) or 0)
    fraud_pts      = round(15 * (1 - fraud_risk_val / 100))
    score         += fraud_pts
    breakdown["fraud_check"] = fraud_pts

    # ── DB match (10 pts) ─────────────────────────────────────────────────────
    match_score = float(matching_dict.get("overall_score", 0) or 0)
    match_pts   = round((match_score / 100) * 10)
    score      += match_pts
    breakdown["database_match"] = match_pts

    # ── LLM validation bonus (up to 5 pts) ───────────────────────────────────
    if llm_validation:
        llm_score = float(llm_validation.get("validation_score") or 0)
        llm_pts   = round(llm_score * 5)
        score    += llm_pts
        breakdown["llm_field_validation"] = llm_pts

    # ── Label and color ───────────────────────────────────────────────────────
    if score >= 80:
        label, color = "Ready for Enrollment", "#2d6a4f"
    elif score >= 60:
        label, color = "Needs Minor Review",   "#e65100"
    elif score >= 40:
        label, color = "Needs Major Review",   "#c62828"
    else:
        label, color = "Unverifiable",          "#6b7280"

    return {
        "onboarding_score": score,
        "label":            label,
        "color":            color,
        "breakdown":        breakdown,
    }

def _to_dict(obj) -> dict:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    if hasattr(obj, "__dict__"):
        return dict(obj.__dict__)
    try:
        return dict(obj)
    except Exception:
        return {}


def _normalise_extracted(raw: dict) -> dict:
    out = dict(raw)
    if "name" not in out or not out["name"]:
        out["name"] = (
            out.get("full_name") or out.get("owner_name") or
            out.get("voter_name") or out.get("account_holder_name") or ""
        )
    if "name_local" not in out or not out["name_local"]:
        out["name_local"] = (
            out.get("full_name_local") or out.get("owner_name_local") or
            out.get("voter_name_local") or out.get("account_holder_name_local") or ""
        )
    return out
# ── Helper: Auto-detect document type from page image ────────────────────────
async def _detect_page_doc_type(image_path: str, prompt: str) -> str:
    """
    Calls GPT-4.1 Vision to auto-detect document type from a page image.
    Returns one of the VALID_DOC_TYPES or 'unknown'.
    """
    try:
        result = await extract_text(image_path, "auto_detect")
        detected = (getattr(result, "detected_doc_type", None) or "unknown").strip().lower()
        if detected in VALID_DOC_TYPES:
            return detected
        return "unknown"
    except Exception as e:
        logger.warning("_detect_page_doc_type failed | error={}", e)
        return "unknown"





# ── Helper: LLM Field Validation ──────────────────────────────────────────────
async def _run_llm_field_validation(
    extracted_fields: dict,
    doc_type: str,
) -> dict:
    """
    Uses GPT-4.1 to validate extracted fields for consistency and accuracy.
    Directly uses settings from get_settings() — same as ocr_engine.py.
    Falls back gracefully — never blocks the pipeline.
    """
    import json as _json
    import re   as _re
    import httpx as _httpx
    from backend.config import get_settings as _get_settings

    _VALIDATION_PROMPT = f"""
You are an expert document validator for Indian government documents.

Document Type: {doc_type}
Extracted Fields:
{_json.dumps(extracted_fields, ensure_ascii=False, indent=2)}

Your job:
1. Check if extracted fields are internally consistent
2. Validate regional data — does this taluka belong to this district in Maharashtra?
3. Check name consistency between local script and English transliteration
4. Flag fields that look like OCR errors
5. Suggest corrections where confident

Respond in this exact JSON format only — no extra text outside the JSON:
{{
  "validation_score": 0.95,
  "is_consistent": true,
  "flags": [],
  "field_corrections": {{}},
  "summary": "One sentence plain English summary for the coordinator"
}}
"""

    try:
        settings = _get_settings()

        api_url = settings.ocr_api_url
        api_key = settings.ocr_api_key
        model   = getattr(settings, "ocr_model", "gpt-4.1")
        timeout = getattr(settings, "ocr_timeout", 60)

        # ── Safety check — if API not configured skip gracefully ──────────────
        if not api_url or not api_key:
            logger.warning(
                "LLM validation skipped — OCR API not configured | doc_type={}",
                doc_type,
            )
            return {
                "validation_score":  None,
                "is_consistent":     None,
                "flags":             [],
                "field_corrections": {},
                "summary":           "LLM validation skipped — API not configured.",
            }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type":  "application/json",
        }

        body = {
            "model": model,
            "messages": [
                {
                    "role":    "system",
                    "content": (
                        "You are an expert document validator for Indian government documents. "
                        "Always respond with valid JSON only. No explanation outside the JSON."
                    ),
                },
                {
                    "role":    "user",
                    "content": _VALIDATION_PROMPT,
                },
            ],
            "max_tokens":  500,
            "temperature": 0.1,
        }

        logger.info(
            "LLM field validation call | doc_type={} | fields_count={}",
            doc_type,
            len(extracted_fields),
        )

        async with _httpx.AsyncClient(timeout=float(timeout)) as client:
            response = await client.post(api_url, headers=headers, json=body)
            response.raise_for_status()

        data        = response.json()
        raw_content = data["choices"][0]["message"]["content"].strip()

        logger.debug(
            "LLM validation raw response | doc_type={} | preview={}",
            doc_type,
            raw_content[:300],
        )

        # ── Strip markdown fences if present ──────────────────────────────────
        if raw_content.startswith("```"):
            lines = raw_content.split("\n")
            end   = len(lines)
            for i in range(len(lines) - 1, 0, -1):
                if lines[i].strip() == "```":
                    end = i
                    break
            raw_content = "\n".join(lines[1:end]).strip()

        # ── Parse JSON safely ─────────────────────────────────────────────────
        json_match = _re.search(r'\{.*\}', raw_content, _re.DOTALL)
        if json_match:
            result = _json.loads(json_match.group())

            validation_score = result.get("validation_score", 0.0)
            is_consistent    = result.get("is_consistent", True)
            flags            = result.get("flags", [])
            corrections      = result.get("field_corrections", {})
            summary          = result.get("summary", "Validation completed.")

            # ── Type safety ───────────────────────────────────────────────────
            validation_score = float(validation_score) if validation_score is not None else 0.0
            is_consistent    = bool(is_consistent)
            flags            = list(flags) if isinstance(flags, list) else []
            corrections      = dict(corrections) if isinstance(corrections, dict) else {}
            summary          = str(summary)

            logger.info(
                "LLM validation complete | doc_type={} | score={} | consistent={} | flags={}",
                doc_type,
                validation_score,
                is_consistent,
                flags,
            )

            return {
                "validation_score":  validation_score,
                "is_consistent":     is_consistent,
                "flags":             flags,
                "field_corrections": corrections,
                "summary":           summary,
            }

        logger.warning(
            "LLM validation — could not parse JSON from response | doc_type={}",
            doc_type,
        )

    except _httpx.TimeoutException:
        logger.warning(
            "LLM validation timed out | doc_type={}",
            doc_type,
        )
    except _httpx.HTTPStatusError as e:
        logger.warning(
            "LLM validation HTTP error | doc_type={} | status={} | detail={}",
            doc_type,
            e.response.status_code,
            e.response.text[:200],
        )
    except _json.JSONDecodeError as e:
        logger.warning(
            "LLM validation JSON decode error | doc_type={} | error={}",
            doc_type,
            e,
        )
    except Exception as e:
        logger.warning(
            "LLM validation failed | doc_type={} | error={}",
            doc_type,
            e,
        )

    # ── Safe fallback — never blocks the pipeline ─────────────────────────────
    return {
        "validation_score":  None,
        "is_consistent":     None,
        "flags":             [],
        "field_corrections": {},
        "summary":           "LLM validation unavailable for this document.",
    }

@router.post("/upload/document")
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = Form(...),
    farmer_id: str = Form(default=""),
    language: str = Form(default="en"),
):
    t0         = time.time()
    request_id = uuid.uuid4().hex[:12]
    lang       = language if language in ("en", "hi", "mr") else "en"
    now_iso    = datetime.now(timezone.utc).isoformat()

    logger.info(
        "Upload started | request_id={} doc_type={} farmer_id={} lang={}",
        request_id, document_type, farmer_id, lang,
    )

    # ── Step 0: Validate ──────────────────────────────────────────────────────
    doc_type = document_type.strip().lower()
    if doc_type not in VALID_DOC_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid document_type '{document_type}'. "
                   f"Must be one of: {', '.join(sorted(VALID_DOC_TYPES))}",
        )
    cfg = _DOC_CONFIG[doc_type]

    ext = Path(file.filename or "unknown.jpg").suffix.lower()

    # ── PDF Detection ─────────────────────────────────────────────────────────
    is_pdf = (
        ext == ".pdf"
        or (file.content_type or "").lower() == "application/pdf"
    )

    if is_pdf and ext not in (".pdf",):
        ext = ".pdf"

    if not is_pdf and ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext}' not allowed.",
        )

    # ── Step 1: Read file content ─────────────────────────────────────────────
    content = await file.read()

    # ══════════════════════════════════════════════════════════════════════════
    # PDF MULTI-PAGE HANDLING
    # ══════════════════════════════════════════════════════════════════════════
    if is_pdf:
        logger.info(
            "PDF detected | request_id={} | filename={} | size={}bytes",
            request_id, file.filename, len(content),
        )

        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise HTTPException(
                status_code=500,
                detail="PDF processing library not installed. Run: pip install pymupdf",
            )

        # ── Split PDF into page images ────────────────────────────────────────
        try:
            pdf_document   = fitz.open(stream=content, filetype="pdf")
            total_pages    = len(pdf_document)
            page_results   = []
            batch_id       = request_id  # use original request_id as batch ID

            logger.info(
                "PDF split | batch_id={} | total_pages={}",
                batch_id, total_pages,
            )

            for page_number in range(total_pages):
                page_request_id = uuid.uuid4().hex[:12]
                page_now_iso    = datetime.now(timezone.utc).isoformat()

                try:
                    # Render page at 2x resolution for OCR accuracy
                    page     = pdf_document[page_number]
                    mat      = fitz.Matrix(2.0, 2.0)
                    pix      = page.get_pixmap(matrix=mat)
                    img_bytes = pix.tobytes("png")

                    logger.info(
                        "PDF page rendered | batch={} | page={}/{} | size={}bytes",
                        batch_id, page_number + 1, total_pages, len(img_bytes),
                    )

                    # ── Save page image ───────────────────────────────────────
                    page_upload_dir = Path("uploads") / page_request_id
                    page_upload_dir.mkdir(parents=True, exist_ok=True)
                    page_file_path  = page_upload_dir / "document.png"
                    page_file_path.write_bytes(img_bytes)
                    page_image_rel  = str(page_file_path).replace("\\", "/")

                    # ── Auto-detect document type for this page ───────────────
                    _AUTO_DETECT_PROMPT = """
Look at this document page carefully.
Identify which ONE type it is from these options ONLY:
- land_record
- cc_training_photo
- mom
- aadhaar
- bank_passbook
- voter_id
- unknown

Reply with ONLY the document type string. Nothing else. No explanation.
"""
                    try:
                        detected_page_type = await detect_page_type(
                            str(page_file_path),
                        )
                        # If unknown — fall back to the user-declared doc_type
                        if detected_page_type == "unknown":
                            logger.warning(
                                "Auto-detect returned unknown | page={} | "
                                "falling back to declared doc_type={}",
                                page_number + 1, doc_type,
                            )
                            detected_page_type = doc_type
                    except Exception as detect_err:
                        logger.warning(
                            "Auto-detect failed | page={} | error={} | "
                            "defaulting to doc_type={}",
                            page_number + 1, detect_err, doc_type,
                        )
                        detected_page_type = doc_type

                    logger.info(
                        "Auto-detected | batch={} | page={} | type={}",
                        batch_id, page_number + 1, detected_page_type,
                    )

                    page_cfg = _DOC_CONFIG.get(detected_page_type, cfg)

                    # ── Quality check for this page ───────────────────────────
                    page_quality = check_quality(str(page_file_path))

                    if not page_quality.is_acceptable:
                        page_result = {
                            "page":          page_number + 1,
                            "request_id":    page_request_id,
                            "batch_id":      batch_id,
                            "document_type": detected_page_type,
                            "farmer_id":     farmer_id or None,
                            "status":        "rejected",
                            "stage":         "quality_check",
                            "rejection_type": "quality",
                            "message":       _msg(page_cfg.get("quality_fail", cfg["quality_fail"]), lang),
                            "messages":      {k: _msg(page_cfg.get("quality_fail", cfg["quality_fail"]), k) for k in ("en", "hi", "mr")},
                            "quality":       {
                                "overall_score": page_quality.overall_score,
                                "is_acceptable": False,
                                "checks":        page_quality.checks,
                                "feedback":      page_quality.feedback,
                            },
                            "extracted_fields": {}, "matching": {}, "fraud": {},
                            "created_at":    page_now_iso,
                            "timestamp":     page_now_iso,
                            "processing_time": round(time.time() - t0, 2),
                            "_image_path":   page_image_rel,
                        }
                        

                        page_results.append(page_result)
                        continue

                    # ── OCR for this page ─────────────────────────────────────
                    page_ocr = await extract_text(str(page_file_path), detected_page_type)

                    if not page_ocr.is_valid_document:
                        rejection_reason = page_ocr.rejection_reason or ""
                        msg_key  = "wrong_doc" if ("wrong" in rejection_reason.lower() or "not" in rejection_reason.lower()) else "ocr_fail"
                        rej_type = "wrong_document" if msg_key == "wrong_doc" else "ocr_failure"
                        page_result = {
                            "page":           page_number + 1,
                            "request_id":     page_request_id,
                            "batch_id":       batch_id,
                            "document_type":  detected_page_type,
                            "farmer_id":      farmer_id or None,
                            "status":         "rejected",
                            "stage":          "ocr",
                            "rejection_type": rej_type,
                            "message":        _msg(page_cfg.get(msg_key, cfg.get(msg_key, "")), lang),
                            "messages":       {k: _msg(page_cfg.get(msg_key, cfg.get(msg_key, "")), k) for k in ("en", "hi", "mr")},
                            "quality":        {
                                "overall_score": page_quality.overall_score,
                                "is_acceptable": True,
                                "checks":        page_quality.checks,
                                "feedback":      page_quality.feedback,
                            },
                            "ocr": {
                                "confidence":        page_ocr.confidence,
                                "is_valid_document": False,
                                "rejection_reason":  rejection_reason,
                            },
                            "extracted_fields": {}, "matching": {}, "fraud": {},
                            "created_at":     page_now_iso,
                            "timestamp":      page_now_iso,
                            "processing_time": round(time.time() - t0, 2),
                            "_image_path":    page_image_rel,
                        }

                        page_results.append(page_result)
                        continue

                    # ── Field extraction for this page ────────────────────────
                    page_extracted      = extract_fields(page_ocr, detected_page_type)
                    page_extracted_dict = _normalise_extracted(_to_dict(page_extracted))
                    if page_ocr.raw_text and "raw_text" not in page_extracted_dict:
                        page_extracted_dict["raw_text"] = page_ocr.raw_text

                    # ── LLM Field Validation for this page ───────────────────
                    page_llm_validation = await _run_llm_field_validation(
                        extracted_fields=page_extracted_dict,
                        doc_type=detected_page_type,
                    )
                    logger.info(
                        "LLM validation | batch={} | page={} | score={} | consistent={} | flags={}",
                        batch_id,
                        page_number + 1,
                        page_llm_validation.get("validation_score"),
                        page_llm_validation.get("is_consistent"),
                        page_llm_validation.get("flags"),
                    )

                    # ── Dedup for this page ───────────────────────────────────
                    page_fingerprint = compute_fingerprint(detected_page_type, page_extracted_dict)
                    if page_fingerprint:
                        existing = find_existing_by_fingerprint(page_fingerprint)
                        if existing:
                            original_id = existing.get("request_id", "")
                            if original_id:
                                logger.warning(
                                    "PDF page DUPLICATE | batch={} | page={} | new={} → original={}",
                                    batch_id, page_number + 1, page_request_id, original_id,
                                )
                                save_redirect(page_request_id, original_id)
                                page_result = {
                                    "page":              page_number + 1,
                                    "request_id":        page_request_id,
                                    "batch_id":          batch_id,
                                    "document_type":     detected_page_type,
                                    "farmer_id":         farmer_id or None,
                                    "status":            "duplicate",
                                    "stage":             "dedup",
                                    "rejection_type":    "duplicate",
                                    "original_request_id": original_id,
                                    "message":           _msg(page_cfg.get("duplicate", cfg.get("duplicate", "")), lang),
                                    "messages":          {k: _msg(page_cfg.get("duplicate", cfg.get("duplicate", "")), k) for k in ("en", "hi", "mr")},
                                    "extracted_fields":  page_extracted_dict,
                                    "llm_validation":    page_llm_validation,
                                    "matching": {}, "fraud": {},
                                    "created_at":        page_now_iso,
                                    "timestamp":         page_now_iso,
                                    "processing_time":   round(time.time() - t0, 2),
                                    "_image_path":       page_image_rel,
                                }
                                page_results.append(page_result)
                                continue

                    if not page_extracted_dict.get("pu_id"):
                        acc_num = page_extracted_dict.get("account_number", "")
                        raw_fields = page_extracted_dict.get("raw_fields", {}) or {}
                        acc_from_raw = raw_fields.get("account_number", "")
                        candidate = acc_num or acc_from_raw or ""
                        if candidate and len(str(candidate).replace(" ", "")) >= 8:
                            page_extracted_dict["pu_id"] = str(candidate).strip()
                            logger.info(
                                "Dedup fallback | using account_number as pu_id | "
                                "value={} | page={} | batch={}",
                                candidate, page_number + 1, batch_id,
                            )

                    page_fingerprint = compute_fingerprint(detected_page_type, page_extracted_dict)        

                    # ── CC Training validation for this page ──────────────────
                    if detected_page_type == "cc_training_photo":
                        cc_raw           = page_extracted_dict.get("raw_fields", {}) or {}
                        persons_detected = str(page_extracted_dict.get("persons_detected") or cc_raw.get("persons_detected") or "0").strip()
                        has_two          = str(page_extracted_dict.get("has_minimum_two_persons") or cc_raw.get("has_minimum_two_persons") or "false").strip().lower()

                        if has_two == "false" or (persons_detected.isdigit() and int(persons_detected) < 2):
                            count_display = persons_detected if persons_detected.isdigit() else "unknown"
                            page_result   = {
                                "page":           page_number + 1,
                                "request_id":     page_request_id,
                                "batch_id":       batch_id,
                                "document_type":  detected_page_type,
                                "farmer_id":      farmer_id or None,
                                "status":         "rejected",
                                "stage":          "cc_validation",
                                "rejection_type": "insufficient_persons",
                                "message":        f"❌ CC Training Photo rejected: Only {count_display} person detected.",
                                "messages": {
                                    "en": f"❌ CC Training Photo rejected: Only {count_display} person detected. Must show farmer AND field representative.",
                                    "hi": f"❌ CC फोटो अस्वीकृत: केवल {count_display} व्यक्ति दिखे।",
                                    "mr": f"❌ CC फोटो नाकारला: फक्त {count_display} व्यक्ती दिसले.",
                                },
                                "quality": {
                                    "overall_score": page_quality.overall_score,
                                    "is_acceptable": True,
                                    "checks":        page_quality.checks,
                                    "feedback":      page_quality.feedback,
                                },
                                "ocr": {
                                    "confidence":        page_ocr.confidence,
                                    "is_valid_document": True,
                                    "raw_text":          (page_ocr.raw_text or "")[:300],
                                },
                                "extracted_fields": page_extracted_dict,
                                "llm_validation":   page_llm_validation,
                                "matching": {}, "fraud": {},
                                "cc_validation": {
                                    "persons_detected":       persons_detected,
                                    "has_minimum_two_persons": has_two,
                                    "validation_failed":      True,
                                    "reason":                 f"Only {count_display} person detected. Minimum 2 required.",
                                },
                                "created_at":      page_now_iso,
                                "timestamp":       page_now_iso,
                                "processing_time": round(time.time() - t0, 2),
                                "_image_path":     page_image_rel,
                            }

                            page_results.append(page_result)
                            continue

                    # ── Matching + Fraud for this page ────────────────────────
                    page_matching      = match_fields(page_extracted, farmer_id=farmer_id if farmer_id else None)
                    page_matching_dict = _to_dict(page_matching)
                    page_fraud         = detect_fraud(page_file_path)
                    page_fraud_dict    = _to_dict(page_fraud)

                    # ── Status for this page ──────────────────────────────────
                    page_fraud_suspicious = page_fraud_dict.get("is_suspicious", False)
                    page_fraud_risk       = float(page_fraud_dict.get("risk_score", 0) or 0)
                    page_overall_score    = float(page_matching_dict.get("overall_score", page_matching_dict.get("score", 0.0)) or 0.0)

                    if page_fraud_suspicious and page_fraud_risk >= 70.0:
                        page_status  = "rejected"
                        page_msg_key = "rejected"
                    elif page_overall_score < 50.0:
                        page_status  = "needs_review"
                        page_msg_key = "review"
                    else:
                        page_status  = "verified"
                        page_msg_key = "success"

                    # ── Onboarding score for this page ────────────────────────
                    page_onboarding = _compute_onboarding_score(
                        page_quality,
                        page_ocr,
                        page_extracted_dict,
                        page_matching_dict,
                        page_fraud_dict,
                        llm_validation=page_llm_validation,
                    )

                    # ── Build page result ─────────────────────────────────────
                    page_result = {
                        "page":           page_number + 1,
                        "request_id":     page_request_id,
                        "batch_id":       batch_id,
                        "document_type":  detected_page_type,
                        "farmer_id":      farmer_id or None,
                        "status":         page_status,
                        "stage":          "complete",
                        "rejection_type": None,
                        "message":        _msg(page_cfg.get(page_msg_key, cfg.get(page_msg_key, "")), lang),
                        "messages":       {k: _msg(page_cfg.get(page_msg_key, cfg.get(page_msg_key, "")), k) for k in ("en", "hi", "mr")},
                        "quality": {
                            "overall_score": page_quality.overall_score,
                            "is_acceptable": True,
                            "checks":        page_quality.checks,
                            "feedback":      page_quality.feedback,
                        },
                        "ocr": {
                            "confidence":        page_ocr.confidence,
                            "language_detected": page_ocr.language_detected,
                            "is_valid_document": True,
                            "raw_text":          (page_ocr.raw_text or "")[:500],
                        },
                        "extracted_fields":   page_extracted_dict,
                        "llm_validation":     page_llm_validation,
                        "matching":           page_matching_dict,
                        "fraud":              page_fraud_dict,
                        "fingerprint":        page_fingerprint,
                        "onboarding_score":   page_onboarding["onboarding_score"],
                        "onboarding_label":   page_onboarding["label"],
                        "onboarding_color":   page_onboarding["color"],
                        "onboarding_breakdown": page_onboarding["breakdown"],
                        "created_at":         page_now_iso,
                        "saved_at":           page_now_iso,
                        "_saved_at":          page_now_iso,
                        "timestamp":          page_now_iso,
                        "processing_time":    round(time.time() - t0, 2),
                        "_image_path":        page_image_rel,
                    }

                    
                    logger.info(
                        "PDF page complete | batch={} | page={} | type={} | status={} | score={}",
                        batch_id, page_number + 1, detected_page_type,
                        page_status, page_onboarding["onboarding_score"],
                    )
                    page_results.append(page_result)

                except Exception as page_err:
                    import traceback
                    logger.error(
                        "PDF page processing failed | batch={} | page={} | error={} | {}",
                        batch_id, page_number + 1, page_err, traceback.format_exc(),
                    )
                    page_results.append({
                        "page":          page_number + 1,
                        "request_id":    uuid.uuid4().hex[:12],
                        "batch_id":      batch_id,
                        "document_type": "unknown",
                        "status":        "error",
                        "message":       f"Page {page_number + 1} could not be processed.",
                        "error":         str(page_err),
                        "timestamp":     datetime.now(timezone.utc).isoformat(),
                    })

            pdf_document.close()

            # ── PDF DEDUP CHECK — use page-level duplicates first ─────────────
            # Strategy 1: Check if any page was already detected as duplicate
            page_level_duplicate = next(
                (r.get("original_request_id") for r in page_results
                 if r.get("status") == "duplicate" and r.get("original_request_id")),
                None,
            )

            # Strategy 2: Check all page fingerprints against existing records
            pdf_fingerprint    = None
            duplicate_original = page_level_duplicate  # use page-level if found

            for page_r in page_results:
                fp = page_r.get("fingerprint")
                if not fp:
                    continue
                if not pdf_fingerprint:
                    pdf_fingerprint = fp  # store first valid fingerprint

                if not duplicate_original:
                    existing = find_existing_by_fingerprint(fp)
                    if existing:
                        original_id = existing.get("request_id", "")
                        if original_id and original_id != batch_id:
                            duplicate_original = original_id
                            logger.warning(
                                "PDF DUPLICATE BLOCKED via fingerprint | "
                                "new={} → original={} | page={} | fp={}",
                                batch_id, original_id,
                                page_r.get("page", "?"),
                                fp[:16],
                            )
                            break

            if duplicate_original:
                save_redirect(batch_id, duplicate_original)
                overall_cfg = _DOC_CONFIG.get(doc_type, _DOC_CONFIG["land_record"])
                logger.warning(
                    "PDF DUPLICATE BLOCKED | batch_id={} → original={}",
                    batch_id, duplicate_original,
                )
                return JSONResponse(
                    status_code=200,
                    content={
                        "batch_id":              batch_id,
                        "request_id":            batch_id,
                        "is_batch":              True,
                        "is_pdf":                True,
                        "status":                "duplicate",
                        "document_type":         doc_type,
                        "original_request_id":   duplicate_original,
                        "message":               _msg(overall_cfg["duplicate"], lang),
                        "messages":              {k: _msg(overall_cfg["duplicate"], k) for k in ("en", "hi", "mr")},
                        "extracted_fields":      {},
                        "total_pages":           total_pages,
                        "pages_processed":       len(page_results),
                        "total_processing_time": round(time.time() - t0, 2),
                    },
                )
            elif pdf_fingerprint:
                logger.info(
                    "PDF dedup: no existing match — new document | batch_id={}",
                    batch_id,
                )
            else:
                logger.warning(
                    "PDF dedup: no fingerprint found in any page | batch_id={}",
                    batch_id,
                )

        except Exception as pdf_err:
            import traceback
            logger.error(
                "PDF processing failed | request_id={} | error={} | {}",
                request_id, pdf_err, traceback.format_exc(),
            )
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process PDF: {str(pdf_err)}",
            )

        # ── Return batch result ───────────────────────────────────────────────
        verified_count     = sum(1 for r in page_results if r.get("status") == "verified")
        needs_review_count = sum(1 for r in page_results if r.get("status") == "needs_review")
        rejected_count     = sum(1 for r in page_results if r.get("status") in ("rejected", "duplicate", "error"))


        # ── Determine overall status ──────────────────────────────────────────
        all_statuses = [r.get("status") for r in page_results]
        if all(s == "verified" for s in all_statuses):
            overall_status  = "verified"
            overall_msg_key = "success"
        else:
            overall_status  = "needs_review"
            overall_msg_key = "review"

        # ── Save original PDF file under batch_id folder ──────────────────────
        pdf_upload_dir = Path("uploads") / batch_id
        pdf_upload_dir.mkdir(parents=True, exist_ok=True)
        pdf_file_path  = pdf_upload_dir / "document.pdf"
        pdf_file_path.write_bytes(content)
        pdf_image_rel  = str(pdf_file_path).replace("\\", "/")

        # ── Use declared doc_type config for messages ─────────────────────────
        overall_cfg = _DOC_CONFIG.get(doc_type, _DOC_CONFIG["land_record"])

        # ── Pick best extracted fields from non-rejected pages ────────────────
        best_extracted = next(
            (r.get("extracted_fields", {}) for r in page_results
             if r.get("status") != "rejected" and r.get("extracted_fields")),
            {},
        )

        # ── Pick best quality from all pages ──────────────────────────────────
        best_quality = max(
            [r.get("quality", {}) for r in page_results],
            key=lambda q: float(q.get("overall_score", 0) or 0),
            default={},
        )

        # ── Pick best OCR confidence from all pages ───────────────────────────
        best_ocr = max(
            [r.get("ocr", {}) for r in page_results],
            key=lambda o: float(o.get("confidence", 0) or 0),
            default={},
        )

        # ── Pick best LLM validation ──────────────────────────────────────────
        best_llm = next(
            (r.get("llm_validation") for r in page_results
             if r.get("llm_validation") and
             r.get("llm_validation", {}).get("validation_score") is not None),
            None,
        )

        # ── Pick best fraud result ────────────────────────────────────────────
        best_fraud = next(
            (r.get("fraud", {}) for r in page_results if r.get("fraud")),
            {},
        )

        # ── Pick best onboarding score from non-rejected pages ────────────────
        scored_pages = [r for r in page_results if r.get("status") != "rejected"]
        best_page    = max(
            scored_pages,
            key=lambda r: r.get("onboarding_score", 0),
            default=page_results[0] if page_results else {},
        )

        # ── Build unified single-record payload ───────────────────────────────
        unified_payload = {
            "request_id":           batch_id,
            "document_type":        doc_type,
            "farmer_id":            farmer_id or None,
            "status":               overall_status,
            "stage":                "complete",
            "rejection_type":       None,
            "is_pdf":               True,
            "total_pages":          total_pages,
            "message":              _msg(overall_cfg[overall_msg_key], lang),
            "messages":             {k: _msg(overall_cfg[overall_msg_key], k) for k in ("en", "hi", "mr")},
            "pages":                page_results,
            "summary": {
                "verified":         verified_count,
                "needs_review":     needs_review_count,
                "rejected":         rejected_count,
            },
            "quality":              best_quality,
            "ocr":                  best_ocr,
            "extracted_fields":     best_extracted,
            "llm_validation":       best_llm,
            "matching":             {},
            "fraud":                best_fraud,
            "fingerprint":          pdf_fingerprint,
            "onboarding_score":     best_page.get("onboarding_score", 0),
            "onboarding_label":     best_page.get("onboarding_label", "Needs Review"),
            "onboarding_color":     best_page.get("onboarding_color", "#e65100"),
            "onboarding_breakdown": best_page.get("onboarding_breakdown", {}),
            "created_at":           now_iso,
            "saved_at":             now_iso,
            "_saved_at":            now_iso,
            "timestamp":            now_iso,
            "_image_path":          pdf_image_rel,
            "processing_time":      round(time.time() - t0, 2),
        }

        # ── Save as single result ─────────────────────────────────────────────
        try:
            save_result(batch_id, doc_type, unified_payload)
            logger.info(
                "PDF unified record saved | batch_id={} | pages={} | status={} | score={}",
                batch_id, total_pages, overall_status,
                unified_payload["onboarding_score"],
            )
        except Exception as save_err:
            import traceback
            logger.error(
                "save_result FAILED for PDF batch {} | {} | {}",
                batch_id, save_err, traceback.format_exc(),
            )

        # ── Return single unified response ────────────────────────────────────
        return JSONResponse(
            status_code=200,
            content={
                "batch_id":             batch_id,
                "request_id":           batch_id,
                "is_batch":             True,
                "is_pdf":               True,
                "source":               "pdf",
                "total_pages":          total_pages,
                "pages_processed":      len(page_results),
                "status":               overall_status,
                "document_type":        doc_type,
                "farmer_id":            farmer_id or None,
                "extracted_fields":     best_extracted,
                "onboarding_score":     unified_payload["onboarding_score"],
                "onboarding_label":     unified_payload["onboarding_label"],
                "onboarding_color":     unified_payload["onboarding_color"],
                "summary": {
                    "verified":         verified_count,
                    "needs_review":     needs_review_count,
                    "rejected":         rejected_count,
                },
                "results":              page_results,
                "message":              _msg(overall_cfg[overall_msg_key], lang),
                "messages":             {k: _msg(overall_cfg[overall_msg_key], k) for k in ("en", "hi", "mr")},
                "total_processing_time": round(time.time() - t0, 2),
            },
        )

    # ══════════════════════════════════════════════════════════════════════════
    # SINGLE IMAGE HANDLING — existing flow unchanged below
    # ══════════════════════════════════════════════════════════════════════════

    # ── Step 1: Save file ─────────────────────────────────────────────────────
    upload_dir = Path("uploads") / request_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path  = upload_dir / f"document{ext}"
    file_path.write_bytes(content)
    image_rel  = str(file_path).replace("\\", "/")
    logger.info("Saved {} bytes → {}", len(content), file_path)

    # ── Step 2: Quality check ─────────────────────────────────────────────────
    quality = check_quality(str(file_path))

    if not quality.is_acceptable:
        payload = {
            "request_id": request_id, "document_type": doc_type,
            "farmer_id": farmer_id or None, "status": "rejected",
            "stage": "quality_check", "rejection_type": "quality",
            "message":  _msg(cfg["quality_fail"], lang),
            "messages": {k: _msg(cfg["quality_fail"], k) for k in ("en", "hi", "mr")},
            "quality":  {"overall_score": quality.overall_score, "is_acceptable": False,
                         "checks": quality.checks, "feedback": quality.feedback},
            "extracted_fields": {}, "matching": {}, "fraud": {},
            "created_at": now_iso, "saved_at": now_iso, "_saved_at": now_iso,
            "timestamp": now_iso, "processing_time": round(time.time() - t0, 2),
            "_image_path": image_rel,
        }
        save_result(request_id, doc_type, payload)
        return JSONResponse(status_code=200, content=payload)

    # ── Step 3: OCR ───────────────────────────────────────────────────────────
    ocr_result = await extract_text(str(file_path), doc_type)

    if not ocr_result.is_valid_document:
        rejection_reason = ocr_result.rejection_reason or ""
        msg_key  = "wrong_doc" if ("wrong" in rejection_reason.lower() or "not" in rejection_reason.lower()) else "ocr_fail"
        rej_type = "wrong_document" if msg_key == "wrong_doc" else "ocr_failure"
        payload  = {
            "request_id": request_id, "document_type": doc_type,
            "farmer_id": farmer_id or None, "status": "rejected",
            "stage": "ocr", "rejection_type": rej_type,
            "message":  _msg(cfg[msg_key], lang),
            "messages": {k: _msg(cfg[msg_key], k) for k in ("en", "hi", "mr")},
            "quality":  {"overall_score": quality.overall_score, "is_acceptable": True,
                         "checks": quality.checks, "feedback": quality.feedback},
            "ocr": {"confidence": ocr_result.confidence, "is_valid_document": False,
                    "rejection_reason": rejection_reason},
            "extracted_fields": {}, "matching": {}, "fraud": {},
            "created_at": now_iso, "saved_at": now_iso, "_saved_at": now_iso,
            "timestamp": now_iso, "processing_time": round(time.time() - t0, 2),
            "_image_path": image_rel,
        }
        return JSONResponse(status_code=200, content=payload)

    # ── Step 4: Doc-type validation (live mode only) ──────────────────────────
    ocr_mode = os.getenv("OCR_MODE", "mock").lower()
    if ocr_mode == "live":
        detected = getattr(ocr_result, "detected_doc_type", None)
        if detected and detected != doc_type:
            payload = {
                "request_id": request_id, "document_type": doc_type,
                "farmer_id": farmer_id or None, "status": "rejected",
                "stage": "doc_type_validation", "rejection_type": "wrong_document",
                "message":  _msg(cfg["wrong_doc"], lang),
                "messages": {k: _msg(cfg["wrong_doc"], k) for k in ("en", "hi", "mr")},
                "quality":  {"overall_score": quality.overall_score, "is_acceptable": True,
                             "checks": quality.checks, "feedback": quality.feedback},
                "ocr": {"confidence": ocr_result.confidence, "is_valid_document": True,
                        "detected_doc_type": detected},
                "extracted_fields": {}, "matching": {}, "fraud": {},
                "created_at": now_iso, "saved_at": now_iso, "_saved_at": now_iso,
                "timestamp": now_iso, "processing_time": round(time.time() - t0, 2),
                "_image_path": image_rel,
            }
            return JSONResponse(status_code=200, content=payload)

    # ── Step 5: Field extraction ──────────────────────────────────────────────
    extracted      = extract_fields(ocr_result, doc_type)
    extracted_dict = _normalise_extracted(_to_dict(extracted))
    if ocr_result.raw_text and "raw_text" not in extracted_dict:
        extracted_dict["raw_text"] = ocr_result.raw_text

    # ── Step 5a: LLM Field Validation ────────────────────────────────────────
    llm_validation = await _run_llm_field_validation(
        extracted_fields=extracted_dict,
        doc_type=doc_type,
    )
    logger.info(
        "LLM validation | request_id={} | score={} | consistent={} | flags={}",
        request_id,
        llm_validation.get("validation_score"),
        llm_validation.get("is_consistent"),
        llm_validation.get("flags"),
    )

    # ── Step 5b: Dedup check ──────────────────────────────────────────────────
    fingerprint = compute_fingerprint(doc_type, extracted_dict)
    logger.info(
        "Dedup | fingerprint={} | doc_type={} | request_id={}",
        fingerprint, doc_type, request_id,
    )

    if fingerprint:
        existing = find_existing_by_fingerprint(fingerprint)
        if existing:
            original_id = existing.get("request_id", "")
            if original_id:
                logger.warning(
                    "DUPLICATE BLOCKED | new={} → original={}",
                    request_id, original_id,
                )
                save_redirect(request_id, original_id)
                payload = {
                    "request_id": request_id, "document_type": doc_type,
                    "farmer_id": farmer_id or None, "status": "duplicate",
                    "stage": "dedup", "rejection_type": "duplicate",
                    "original_request_id": original_id,
                    "message":  _msg(cfg["duplicate"], lang),
                    "messages": {k: _msg(cfg["duplicate"], k) for k in ("en", "hi", "mr")},
                    "quality":  {"overall_score": quality.overall_score, "is_acceptable": True,
                                 "checks": quality.checks, "feedback": quality.feedback},
                    "ocr": {"confidence": ocr_result.confidence, "is_valid_document": True},
                    "extracted_fields": extracted_dict,
                    "llm_validation":   llm_validation,
                    "matching": {}, "fraud": {},
                    "created_at": now_iso, "saved_at": now_iso, "_saved_at": now_iso,
                    "timestamp": now_iso,
                    "processing_time": round(time.time() - t0, 2),
                    "_image_path": image_rel,
                }
                return JSONResponse(status_code=200, content=payload)
            else:
                logger.warning(
                    "Dedup: match has no request_id — treating as new | request_id={}",
                    request_id,
                )
        else:
            logger.info(
                "Dedup: no existing match — new document | request_id={}",
                request_id,
            )

    # ── Step 5c: CC Training Photo validation ─────────────────────────────────
    if doc_type == "cc_training_photo":
        cc_raw           = extracted_dict.get("raw_fields", {}) or {}
        persons_detected = str(extracted_dict.get("persons_detected") or cc_raw.get("persons_detected") or "0").strip()
        has_two          = str(extracted_dict.get("has_minimum_two_persons") or cc_raw.get("has_minimum_two_persons") or "false").strip().lower()
        lat              = cc_raw.get("gps_latitude") or extracted_dict.get("gps_latitude") or ""
        lon              = cc_raw.get("gps_longitude") or extracted_dict.get("gps_longitude") or ""

        logger.info(
            "CC validation | persons={} | has_two={} | request_id={}",
            persons_detected, has_two, request_id,
        )

        if has_two == "false" or (persons_detected.isdigit() and int(persons_detected) < 2):
            count_display        = persons_detected if persons_detected.isdigit() else "unknown"
            cc_rejection_payload = {
                "request_id": request_id, "document_type": doc_type,
                "farmer_id": farmer_id or None, "status": "rejected",
                "stage": "cc_validation", "rejection_type": "insufficient_persons",
                "message": f"❌ CC Training Photo rejected: Only {count_display} person detected. Must show farmer AND field representative.",
                "messages": {
                    "en": f"❌ CC Training Photo rejected: Only {count_display} person detected. Must show farmer AND field representative.",
                    "hi": f"❌ CC फोटो अस्वीकृत: केवल {count_display} व्यक्ति दिखे।",
                    "mr": f"❌ CC फोटो नाकारला: फक्त {count_display} व्यक्ती दिसले.",
                },
                "quality":  {"overall_score": quality.overall_score, "is_acceptable": True,
                             "checks": quality.checks, "feedback": quality.feedback},
                "ocr": {"confidence": ocr_result.confidence, "is_valid_document": True,
                        "raw_text": (ocr_result.raw_text or "")[:300]},
                "extracted_fields": extracted_dict,
                "llm_validation":   llm_validation,
                "matching": {}, "fraud": {},
                "cc_validation": {
                    "persons_detected":        persons_detected,
                    "has_minimum_two_persons": has_two,
                    "gps_latitude":            lat,
                    "gps_longitude":           lon,
                    "validation_failed":       True,
                    "reason": f"Only {count_display} person detected. Minimum 2 required.",
                },
                "created_at": now_iso, "saved_at": now_iso, "_saved_at": now_iso,
                "timestamp": now_iso,
                "processing_time": round(time.time() - t0, 2),
                "_image_path": image_rel,
            }
            save_result(request_id, doc_type, cc_rejection_payload)
            logger.warning(
                "CC validation FAILED | persons={} | request_id={}",
                persons_detected, request_id,
            )
            return JSONResponse(status_code=200, content=cc_rejection_payload)

    # ── Step 6: Fuzzy matching ────────────────────────────────────────────────
    matching      = match_fields(extracted, farmer_id=farmer_id if farmer_id else None)
    matching_dict = _to_dict(matching)

    # ── Step 7: Fraud detection ───────────────────────────────────────────────
    fraud      = detect_fraud(file_path)
    fraud_dict = _to_dict(fraud)

    # ── Step 8: Determine status ──────────────────────────────────────────────
    fraud_suspicious = fraud_dict.get("is_suspicious", False)
    fraud_risk       = float(fraud_dict.get("risk_score", 0) or 0)
    overall_score    = float(matching_dict.get("overall_score", matching_dict.get("score", 0.0)) or 0.0)

    if fraud_suspicious and fraud_risk >= 70.0:
        status  = "rejected"; stage = "fraud_detection"
        rej_type = "fraud_suspected"; msg_key = "rejected"
    elif overall_score < 50.0:
        status  = "needs_review"; stage = "field_matching"
        rej_type = None; msg_key = "review"
    else:
        status  = "verified"; stage = "complete"
        rej_type = None; msg_key = "success"

    # ── Step 9: Build payload ─────────────────────────────────────────────────
    payload = {
        "request_id":     request_id,
        "document_type":  doc_type,
        "farmer_id":      farmer_id or None,
        "status":         status,
        "stage":          stage,
        "rejection_type": rej_type,
        "message":  _msg(cfg[msg_key], lang),
        "messages": {k: _msg(cfg[msg_key], k) for k in ("en", "hi", "mr")},
        "quality": {
            "overall_score": quality.overall_score,
            "is_acceptable": True,
            "checks":        quality.checks,
            "feedback":      quality.feedback,
        },
        "ocr": {
            "confidence":        ocr_result.confidence,
            "language_detected": ocr_result.language_detected,
            "is_valid_document": True,
            "raw_text":          (ocr_result.raw_text or "")[:500],
        },
        "extracted_fields": extracted_dict,
        "llm_validation":   llm_validation,
        "matching":         matching_dict,
        "fraud":            fraud_dict,
        "fingerprint":      fingerprint,
        "created_at":       now_iso,
        "saved_at":         now_iso,
        "_saved_at":        now_iso,
        "timestamp":        now_iso,
        "_image_path":      image_rel,
        "processing_time":  round(time.time() - t0, 2),
    }

    # # ── Onboarding score ──────────────────────────────────────────────────────
    # def _compute_onboarding_score(
    #     quality,
    #     ocr_result,
    #     extracted_dict: dict,
    #     matching_dict:  dict,
    #     fraud_dict:     dict,
    # ) -> dict:
    #     score = 0
    #     breakdown: dict[str, int] = {}

    #     q     = float(getattr(quality, "overall_score", 0) or 0)
    #     q_pts = round((q / 100) * 20)
    #     score += q_pts
    #     breakdown["image_quality"] = q_pts

    #     conf = float(ocr_result.confidence or 0) if ocr_result else 0
    #     if conf <= 1.0:
    #         conf *= 100
    #     ocr_pts = round((conf / 100) * 30)
    #     score  += ocr_pts
    #     breakdown["ocr_confidence"] = ocr_pts

    #     non_null  = sum(
    #         1 for k, v in extracted_dict.items()
    #         if v and k not in ("document_type", "raw_fields", "raw_text")
    #         and str(v).strip().lower() not in ("", "none", "null")
    #     )
    #     field_pts = min(25, round(non_null * 3))
    #     score    += field_pts
    #     breakdown["fields_extracted"] = field_pts

    #     fraud_risk_val = float(fraud_dict.get("risk_score", 0) or 0)
    #     fraud_pts      = round(15 * (1 - fraud_risk_val / 100))
    #     score         += fraud_pts
    #     breakdown["fraud_check"] = fraud_pts

    #     match_score = float(matching_dict.get("overall_score", 0) or 0)
    #     match_pts   = round((match_score / 100) * 10)
    #     score      += match_pts
    #     breakdown["database_match"] = match_pts

    #     # ── LLM validation bonus — up to 5 extra points ───────────────────────
    #     llm_score = float(llm_validation.get("validation_score") or 0)
    #     llm_pts   = round(llm_score * 5)
    #     score    += llm_pts
    #     breakdown["llm_field_validation"] = llm_pts

    #     if score >= 80:
    #         label, color = "Ready for Enrollment", "#2d6a4f"
    #     elif score >= 60:
    #         label, color = "Needs Minor Review",   "#e65100"
    #     elif score >= 40:
    #         label, color = "Needs Major Review",   "#c62828"
    #     else:
    #         label, color = "Unverifiable",          "#6b7280"

    #     return {
    #         "onboarding_score": score,
    #         "label":            label,
    #         "color":            color,
    #         "breakdown":        breakdown,
    #     }

    onboarding = _compute_onboarding_score(
        quality, ocr_result, extracted_dict, matching_dict, fraud_dict,
    )
    payload["onboarding_score"]     = onboarding["onboarding_score"]
    payload["onboarding_label"]     = onboarding["label"]
    payload["onboarding_color"]     = onboarding["color"]
    payload["onboarding_breakdown"] = onboarding["breakdown"]

    # ── Step 10: Save result ──────────────────────────────────────────────────
    try:
        save_result(request_id, doc_type, payload)
    except Exception as save_err:
        import traceback
        logger.error(
            "save_result FAILED for {} | {} | {}",
            request_id, save_err, traceback.format_exc(),
        )

    logger.info(
        "Upload complete | request_id={} status={} score={} time={}s",
        request_id, status, overall_score, payload["processing_time"],
    )

    # ── Step 11: Return ───────────────────────────────────────────────────────
    return JSONResponse(status_code=200, content=payload)
