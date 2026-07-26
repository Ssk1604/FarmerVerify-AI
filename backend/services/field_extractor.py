# backend/services/field_extractor.py

from __future__ import annotations

import re
from typing import Optional

from loguru import logger

from backend.models.validation_result import ExtractedFields, OCRResult


# ── Compiled regex patterns ───────────────────────────────────────────────────

# Account number: 9-18 digits, may have spaces/dashes
_RE_ACCOUNT = re.compile(r'\b\d[\d\s\-]{7,16}\d\b')

# Aadhaar: exactly 12 digits, possibly with spaces (XXXX XXXX XXXX)
_RE_AADHAAR = re.compile(r'\b\d{4}\s?\d{4}\s?\d{4}\b')

# IFSC: 4 letters + 0 + 6 alphanumeric
_RE_IFSC = re.compile(r'\b[A-Z]{4}0[A-Z0-9]{6}\b')

# Phone: 10 digits starting with 6-9
_RE_PHONE = re.compile(r'\b[6-9]\d{9}\b')

# Pincode: 6 digits
_RE_PINCODE = re.compile(r'\b[1-9]\d{5}\b')

# Survey/Gat number: capture the VALUE after keyword and separator
# Matches: "Survey No: 142/A" → "142/A"
# Matches: "सर्वे क्र. / Survey No: 142/A" → "142/A"
_RE_SURVEY = re.compile(
    r'(?:'
    r'survey\s*no|'
    r'gat\s*no|'
    r'सर्वे\s*क्र|'
    r'गट\s*क्र|'
    r'survey\s*number|'
    r'gut\s*number'
    r')'
    r'\s*[:/.\s]+\s*'       # separator (colon, slash, space, dot)
    r'([\d/A-Za-z]{1,12})',  # ← capture the VALUE, not the keyword
    re.IGNORECASE,
)
# Village
_RE_VILLAGE = re.compile(
    r'(?:village|gaon|gram|गाव|ग्राम)\s*[:/]\s*([\u0900-\u097FA-Za-z\s]{2,30}?)(?:\s*[|,\n]|$)',
    re.IGNORECASE,
)

# Taluka
_RE_TALUKA = re.compile(
    r'(?:taluka|tehsil|tal|तालुका|तहसील)\s*[:/\.]\s*([\u0900-\u097FA-Za-z\s]{2,30}?)(?:\s*[|,\n]|$)',
    re.IGNORECASE,
)

# District
_RE_DISTRICT = re.compile(
    r'(?:district|dist|jilha|जिल्हा|जिला)\s*[:/\.]\s*([\u0900-\u097FA-Za-z\s]{2,30}?)(?:\s*[|,\n]|$)',
    re.IGNORECASE,
)

# Area in hectares or acres
_RE_AREA = re.compile(
    r'([\d]+\.?\d*)\s*(?:hectare|हेक्टर|acre|एकर|ha)\b',
    re.IGNORECASE,
)

# Name patterns (English) — covers Owner, Name, Account Holder, Naam, Malik
_RE_NAME_EN = re.compile(
    r'(?:owner|name|account\s*holder|holder\s*name|naam|malik|मालक\s*/\s*owner)\s*[:/]\s*([A-Z][A-Za-z\s\.]{2,45}?)(?:\n|$)',
    re.IGNORECASE,
)

# Name in Devanagari — captures after keyword
_RE_NAME_DEV = re.compile(
    r'(?:नाव|नाम|मालक|खातेदार|खाताधारक)\s*[:/]\s*([\u0900-\u097F][\u0900-\u097F\s]{1,40}?)(?:\n|$)',
)

# Bare Devanagari name line (name line followed by English transliteration)
# Pattern: Devanagari name on one line, English name on next line
_RE_DEV_NAME_LINE = re.compile(
    r'^([\u0900-\u097F]{2,}(?:\s[\u0900-\u097F]+){1,5})\s*$',
    re.MULTILINE,
)

# English name standalone line (Title Case, 2-5 words)
_RE_EN_NAME_LINE = re.compile(
    r'^([A-Z][a-z]+(?:\s[A-Z][a-z]+){1,4})\s*$',
    re.MULTILINE,
)

# DOB
_RE_DOB = re.compile(
    r'(?:DOB|D\.O\.B|Date\s*of\s*Birth|जन्म\s*तारीख|जन्मतिथि)\s*[:/]?\s*(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4})',
    re.IGNORECASE,
)

# Gender
_RE_GENDER = re.compile(r'\b(Male|Female|पुरुष|महिला|स्त्री)\b', re.IGNORECASE)

# Bank name
_RE_BANK = re.compile(
    r'\b((?:State Bank|Bank of|Gramin Bank|Maharashtra Bank|Central Bank|Punjab National|'
    r'Canara Bank|Union Bank|Vidarbha|HDFC|ICICI|Axis|Kotak|IndusInd|'
    r'बँक|ग्रामीण बँक|बैंक)\s*(?:of\s+)?[A-Za-z\s]*)',
    re.IGNORECASE,
)

# Branch
_RE_BRANCH = re.compile(
    r'(?:branch|shakha|शाखा|शखा)\s*[:/]\s*([A-Za-z\u0900-\u097F\s]{2,30}?)(?:\n|,|$)',
    re.IGNORECASE,
)


# ── Normalizers ───────────────────────────────────────────────────────────────

def _clean(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    v = str(value).strip().strip('|').strip()
    return v or None


def _norm_account(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    digits = re.sub(r'[\s\-]', '', raw)
    return digits if (9 <= len(digits) <= 18 and digits.isdigit()) else None


def _norm_aadhaar(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    digits = re.sub(r'[\s\-]', '', raw)
    return digits if (len(digits) == 12 and digits.isdigit()) else None


def _norm_ifsc(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    code = raw.strip().upper()
    return code if re.match(r'^[A-Z]{4}0[A-Z0-9]{6}$', code) else None


def _norm_name(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    name = re.sub(r'\s+', ' ', raw).strip()
    # Skip strings that are clearly not names (all caps keywords, too short)
    if len(name) < 4:
        return None
    # Skip if it looks like an address or keyword
    skip_words = {'owner', 'name', 'malik', 'naam', 'holder', 'survey', 'village'}
    if name.lower() in skip_words:
        return None
    # Title-case ASCII names
    if all(c.isascii() or c.isspace() or c == '.' for c in name):
        name = name.title()
    return name or None


# ── Extraction ────────────────────────────────────────────────────────────────

def _regex_extract(text: str) -> dict:
    """Extract all fields from raw OCR text using regex."""
    found: dict = {}

    # --- Name (English) ---
    m = _RE_NAME_EN.search(text)
    if m:
        candidate = _norm_name(m.group(1))
        if candidate:
            found['name'] = candidate

    # Fallback: look for standalone English Title Case name line
    if 'name' not in found:
        matches = _RE_EN_NAME_LINE.findall(text)
        # Filter out short or keyword-only matches
        for candidate in matches:
            normed = _norm_name(candidate)
            if normed and len(normed.split()) >= 2:
                found['name'] = normed
                break

    # --- Name (Devanagari) ---
    m = _RE_NAME_DEV.search(text)
    if m:
        found['name_local'] = m.group(1).strip()
    elif not found.get('name_local'):
        dev_matches = _RE_DEV_NAME_LINE.findall(text)
        if dev_matches:
            # Take the first multi-word Devanagari line
            for candidate in dev_matches:
                if len(candidate.split()) >= 2:
                    found['name_local'] = candidate.strip()
                    break

    # --- Survey number ---
    m = _RE_SURVEY.search(text)
    if m:
        val = m.group(1).strip()
        # Reject if it's just the word "Survey" (keyword bleed)
        if val.lower() not in ('survey', 'no', 'number', 'gat'):
            found['survey_number'] = val

    # --- Village ---
    m = _RE_VILLAGE.search(text)
    if m:
        found['village'] = _clean(m.group(1))

    # --- Taluka ---
    m = _RE_TALUKA.search(text)
    if m:
        found['taluka'] = _clean(m.group(1))

    # --- District ---
    m = _RE_DISTRICT.search(text)
    if m:
        found['district'] = _clean(m.group(1))

    # --- Area ---
    m = _RE_AREA.search(text)
    if m:
        found['area_hectares'] = m.group(1)

    # --- Account number ---
    m = _RE_ACCOUNT.search(text)
    if m:
        found['account_number'] = m.group(0).replace(' ', '')

    # --- Aadhaar ---
    m = _RE_AADHAAR.search(text)
    if m:
        found['aadhaar_number'] = m.group(0).replace(' ', '')

    # --- IFSC ---
    m = _RE_IFSC.search(text)
    if m:
        found['ifsc_code'] = m.group(0).upper()

    # --- Phone ---
    m = _RE_PHONE.search(text)
    if m:
        found['phone'] = m.group(0)

    # --- Pincode ---
    m = _RE_PINCODE.search(text)
    if m:
        found['pincode'] = m.group(0)

    # --- DOB ---
    m = _RE_DOB.search(text)
    if m:
        found['date_of_birth'] = m.group(1)

    # --- Gender ---
    m = _RE_GENDER.search(text)
    if m:
        g = m.group(1).lower()
        found['gender'] = 'Male' if g in ('male', 'पुरुष') else 'Female'

    # --- Bank name ---
    m = _RE_BANK.search(text)
    if m:
        found['bank_name'] = _clean(m.group(1))

    # --- Branch ---
    m = _RE_BRANCH.search(text)
    if m:
        found['branch_name'] = _clean(m.group(1))

    return found


# ── Public function ───────────────────────────────────────────────────────────

def extract_fields(ocr_result: OCRResult, document_type: str) -> ExtractedFields:
    """
    Extract structured fields from OCR result.
    
    Priority:
    1. Use LLM-extracted fields (from live OCR) — highest accuracy
    2. Fall back to regex extraction from raw_text
    3. Normalize and validate all fields
    """
    raw_text = ocr_result.raw_text or ""
    llm_fields = ocr_result.extracted_fields_raw or {}  # ← From live OCR
    
    logger.info(
        "Extracting fields | doc_type={} | text_len={} | llm_fields={}",
        document_type, len(raw_text), len(llm_fields),
    )

    # Get regex-based fallback fields
    regex_fields = _regex_extract(raw_text)
    
    # Merge: LLM fields take priority, regex fills gaps
    def get(llm_key: str, *regex_keys: str) -> Optional[str]:
        """Get field value: LLM first, then regex fallback."""
        # Try LLM field
        val = llm_fields.get(llm_key)
        if val and str(val).strip():
            return str(val).strip()
        # Try regex fields
        for key in regex_keys:
            val = regex_fields.get(key)
            if val and str(val).strip():
                return str(val).strip()
        return None

    logger.debug(
        "LLM fields: {} | Regex fields: {}",
        list(llm_fields.keys()),
        list(regex_fields.keys()),
    )

    # Build document-specific ExtractedFields
    if document_type == "bank_passbook":
        result = ExtractedFields(
            document_type=document_type,
            name=_norm_name(get("account_holder_name", "name")),
            name_local=_clean(get("account_holder_name_local", "name_local")),
            account_number=_norm_account(get("account_number")),
            ifsc_code=_norm_ifsc(get("ifsc_code")),
            bank_name=_clean(get("bank_name")),
            branch_name=_clean(get("branch_name")),
            address=_clean(get("address")),
            phone=_clean(get("phone")),
            raw_fields={**regex_fields, **llm_fields},
        )

    elif document_type == "land_record":
        result = ExtractedFields(
            document_type=document_type,
            name=_norm_name(get("owner_name", "name")),
            name_local=_clean(get("owner_name_local", "name_local")),
            survey_number=_clean(get("survey_number")),
            village=_clean(get("village")),
            taluka=_clean(get("taluka")),
            district=_clean(get("district")),
            area_hectares=_clean(get("area_hectares")),
            land_type=_clean(get("land_type")),
            raw_fields={**regex_fields, **llm_fields},
        )

    elif document_type == "aadhaar_card":
        result = ExtractedFields(
            document_type=document_type,
            name=_norm_name(get("full_name", "name")),
            name_local=_clean(get("full_name_local", "name_local")),
            aadhaar_number=_norm_aadhaar(get("aadhaar_number")),
            date_of_birth=_clean(get("date_of_birth")),
            gender=_clean(get("gender")),
            address=_clean(get("address")),
            pincode=_clean(get("pincode")),
            raw_fields={**regex_fields, **llm_fields},
        )

    else:
        result = ExtractedFields(
            document_type=document_type,
            name=_norm_name(get("owner_name", "account_holder_name", "full_name", "name")),
            name_local=_clean(get("owner_name_local", "account_holder_name_local", "full_name_local", "name_local")),
            raw_fields={**regex_fields, **llm_fields},
        )

    non_null = sum(
        1 for k, v in result.model_dump().items()
        if v is not None and k not in ("document_type", "raw_fields")
    )
    logger.info(
        "Field extraction complete | doc_type={} | fields_found={} | source={}",
        document_type, non_null,
        "llm+regex" if llm_fields else "regex_only",
    )
    return result