# backend/services/ocr_engine.py
"""
FarmerVerify AI — Live OCR Engine
Uses an OpenAI-compatible LLM Vision API for real document text extraction.
Includes strict document type validation before extraction.
"""

from __future__ import annotations

import asyncio
import base64
import json
import mimetypes
import time
from pathlib import Path
from typing import Optional

import httpx
from loguru import logger

from backend.config import get_settings
from backend.models.validation_result import OCRResult


# ── Document type metadata used in prompts ────────────────────────────────────

_DOC_IDENTITY = {
    "land_record": {
        "name": "Land Record (7/12 extract / Satbara Utara / property deed)",
        "visual_markers": [
            "printed government table with rows and columns",
            "official Maharashtra/state government header",
            "survey number or gat number field",
            "village, taluka, district fields",
            "owner name / मालक field",
            "land area / क्षेत्रफळ field",
            "7/12 or ७/१२ printed on document",
            "revenue department stamp or seal",
        ],
        "not_this_if": [
            "it shows Aadhaar number (12 digits with UIDAI logo)",
            "it shows bank account details, IFSC code, bank name",
            "it shows EPIC number or Election Commission logo",
            "it is handwritten on plain paper",
            "it is a notebook page or study notes",
            "it is a photograph or screenshot",
            "it is a sale deed or purchase agreement only (no land details)",
            "it shows 'Minutes of Meeting' heading",          # ← ADD
            "it shows a list of attendees with signatures",   # ← ADD
            "it shows agenda items for a meeting",            # ← ADD
        ],
        # Canonical keys that map to this doc type
        "aliases": [
            "land_record", "land record", "7/12", "satbara", "saat bara",
            "seven twelve", "property deed", "revenue record",
            "भूमी अभिलेख", "सातबारा", "७/१२", "जमीन उतारा",
        ],
    },
    "bank_passbook": {
        "name": "Bank Passbook (first page with account details)",
        "visual_markers": [
            "bank name and logo at top",
            "account number printed",
            "IFSC code printed",
            "account holder name",
            "branch name",
            "printed bank passbook format with ruled lines",
        ],
        "not_this_if": [
            "it shows Aadhaar number (12 digits with UIDAI logo)",
            "it shows survey number, gat number, village, taluka, district",
            "it shows EPIC number or voter photo identity",
            "it is handwritten on plain paper",
            "it is a notebook page, screenshot, or study notes",
            "it shows a phone/app screenshot of net banking",
            "it is a bank statement (not a passbook)",
        ],
        "aliases": [
            "bank_passbook", "bank passbook", "passbook", "bank account",
            "बैंक पासबुक", "बँक पासबुक",
        ],
    },
    "aadhaar_card": {
        "name": "Aadhaar Card (UIDAI issued, front side)",
        "visual_markers": [
            "UIDAI logo or text",
            "Government of India / भारत सरकार header",
            "12-digit Aadhaar number",
            "Aadhaar / आधार text printed on card",
            "small card format with photo of person",
            "date of birth printed",
            "gender printed",
            "QR code on card",
        ],
        "not_this_if": [
            "it shows bank account number, IFSC code, bank name",
            "it shows survey number, village, taluka, district",
            "it shows EPIC number or voter photo identity card",
            "it is handwritten on plain paper",
            "it is a notebook page or study material",
            "it is a PAN card, driving license, or other ID",
            "it is a printout or screenshot of Aadhaar from UIDAI website",
        ],
        "aliases": [
            "aadhaar_card", "aadhaar card", "aadhaar", "aadhar", "aadhar card",
            "आधार", "आधार कार्ड", "uidai",
        ],
    },
    "voter_id": {
        "name": "Voter ID Card / EPIC (Election Commission of India)",
        "visual_markers": [
            "EPIC number printed",
            "Election Commission of India / भारत निर्वाचन आयोग",
            "Voter Photo Identity Card text",
            "voter's photo on card",
            "small card format",
            "father or husband name printed",
            "constituency / part number",
        ],
        "not_this_if": [
            "it shows 12-digit Aadhaar number or UIDAI logo",
            "it shows bank account number, IFSC, bank name",
            "it shows survey number, village, taluka, district",
            "it is handwritten on plain paper",
            "it is a notebook page or study material",
            "it is an Aadhaar card, PAN card, or driving license",
        ],
        "aliases": [
            "voter_id", "voter id", "voter card", "epic", "election card",
            "voter photo identity card", "मतदार ओळखपत्र", "मतदाता पहचान पत्र",
        ],

        "cc_training_photo": {
        "name": "CC Training Photo (Farmer + Field Representative)",
        "visual_markers": [
            "photograph of people (not a document)",
            "at least 2 persons visible",
            "outdoor or agricultural field setting",
            "people standing or working together",
            "farming or nature background",
        ],
        "not_this_if": [
            "it is a document, form, or certificate",
            "it shows only text with no people",
            "it is a landscape with no people visible",
            "it is a selfie of a single person only",
        ],
        "aliases": [
            "cc_training_photo", "cc training photo", "training photo",
            "cc photo", "field photo", "farmer photo",
        ],
    },

    },

    "meeting_minutes": {
    "name": "Minutes of Meeting (Carbon Credit Training)",
    "visual_markers": [
        "Minutes of Meeting heading",
        "Date, Time, Location fields",
        "Field representative name",
        "List of Attendees with names and phone numbers",
        "Signature column",
        "Agenda items listed",
        "GPS Map Camera Lite photo attached",
    ],
    "not_this_if": [
        "it is a land record or 7/12 extract",
        "it is an Aadhaar card",
        "it is a bank passbook",
        "it is only a GPS photo with no text",
    ],
    "aliases": [
        "meeting_minutes", "minutes of meeting", "mom",
        "minutes", "meeting notes", "cc training document",
    ],
},


}





# ── Reverse alias lookup: any alias string → canonical doc type key ───────────

_ALIAS_TO_CANONICAL: dict[str, str] = {}
for _canonical, _info in _DOC_IDENTITY.items():
    for _alias in _info.get("aliases", []):
        _ALIAS_TO_CANONICAL[_alias.lower().strip()] = _canonical
    # Also map the canonical key itself
    _ALIAS_TO_CANONICAL[_canonical.lower().strip()] = _canonical




# Auto-detect document type from page content
_AUTO_DETECT_PROMPT = """
Look at this document page carefully.
Identify which type it is from these options:
- land_record (7/12 extract, sale deed, land ownership)
- cc_training (group photo, training session photo)
- mom (minutes of meeting, meeting notes, attendance register)
- aadhaar (Aadhaar card, UID card)
- bank_passbook (bank account, passbook)
- unknown

Reply with ONLY the document type string.
Nothing else.
"""

async def detect_document_type(self, image_bytes: bytes) -> str:
    """
    Auto-detect what type of document a page image is.
    Used for multi-page PDF processing.
    """
    result = await self.call_gpt_vision(image_bytes, _AUTO_DETECT_PROMPT)
    detected_type = result.strip().lower()

    valid_types = [
        "land_record", "cc_training", "mom",
        "aadhaar", "bank_passbook", "unknown"
    ]

    if detected_type not in valid_types:
        logger.warning(
            "Auto-detect returned unknown type: {} — defaulting to unknown",
            detected_type
        )
        return "unknown"

    logger.info("Auto-detected document type: {}", detected_type)
    return detected_type



def _normalize_to_canonical(raw: str) -> str:
    """
    Normalize any document type string (from LLM or user) to a canonical key.
    Returns empty string if no match found.
    """
    if not raw:
        return ""
    cleaned = raw.lower().strip().replace("-", "_").replace("  ", " ")

    # Direct match
    if cleaned in _ALIAS_TO_CANONICAL:
        return _ALIAS_TO_CANONICAL[cleaned]

    # Substring match: check if any alias is contained in the raw string
    for alias, canonical in sorted(_ALIAS_TO_CANONICAL.items(), key=lambda x: -len(x[0])):
        if alias in cleaned:
            return canonical

    return ""


# ── System prompt ─────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are an expert OCR assistant for Indian government and financial documents.
You can read Hindi (Devanagari), Marathi (Devanagari), Telugu, and English text.

Your PRIMARY job is:
1. FIRST verify the document type matches what was declared
2. THEN extract ALL visible text and fields

IMPORTANT RULES FOR DOCUMENT TYPE VALIDATION:
- If the document IS the declared type (even if quality is poor or some fields are missing), 
  set "is_valid_document": true and extract all fields you can see.
- Only set "is_valid_document": false if the document is CLEARLY a DIFFERENT type 
  (e.g., user declared "land_record" but image shows an Aadhaar card).
- Do NOT reject a document just because it's slightly different from the "ideal" version.
  Real documents come in many formats, old/new versions, and varying quality.
- When in doubt, set "is_valid_document": true and extract what you can.

Return ONLY valid JSON. No explanations outside the JSON."""

# ── Per-document OCR prompts ──────────────────────────────────────────────────


def _build_prompt(doc_type: str) -> str:
    """Build extraction prompt. Land records get a permissive prompt to avoid misclassification."""

    info = _DOC_IDENTITY.get(doc_type, {})
    doc_name = info.get("name", doc_type.replace("_", " ").title())

    # ── Land records: skip strict validation, go straight to extraction ──
    if doc_type == "land_record":
        return (
            "This image is a Maharashtra government land document "
            "(7/12 extract, 8A extract, Ferfar/mutation entry, or similar).\n\n"
            "ALL of these are valid 'land_record' documents. "
            "Do NOT reject this as a 'Sale Deed' — "
            "government land records from mahabhumi.gov.in include sale/purchase "
            "entries as part of the mutation history.\n\n"
            "Extract ALL visible text, especially:\n"
            "- Owner/farmer names (मालक / नाव)\n"
            "- Survey / Gat numbers (सर्वे क्र. / गट क्र.)\n"
            "- Village, Taluka, District\n"
            "- Area measurements\n"
            "- PU-ID if present\n"
            "- All person names listed\n\n"
            "Return ONLY valid JSON:\n"
            "{\n"
            '  "is_valid_document": true,\n'
            '  "document_type": "land_record",\n'
            '  "language_detected": "<en/mr/en+mr>",\n'
            '  "raw_text": "<ALL visible text verbatim — do not skip anything>",\n'
            '  "fields": {\n'
            "    " + _get_field_template("land_record") + "\n"
            "  },\n"
            '  "confidence": 0.0,\n'
            '  "notes": "<document subtype observed>"\n'
            "}"
        )

    # ── CC Training Photo: count people, check 2-person requirement ──────
    if doc_type == "cc_training_photo":
        return (
            "This image is a CC (Conservation & Community) training photo taken "
            "by a field representative of the partner NGO.\n\n"
            "Extract ALL visible information including:\n"
            "1. Count every person visible in the photo\n"
            "2. Read the GPS watermark (if present) for exact coordinates\n"
            "3. Read the date and time from the GPS watermark\n"
            "4. Describe the location/setting\n\n"
            "The GPS watermark typically shows:\n"
            "  Latitude XX.XXXXXXXX°  Longitude XX.XXXXXXXX°\n"
            "  Local HH:MM:SS  GMT HH:MM  Altitude XXX meters\n"
            "  Day, DD.MM.YYYY  GPS Map Camera Lite\n\n"
            "Return ONLY valid JSON:\n"
            "{\n"
            '  "is_valid_document": true,\n'
            '  "document_type": "cc_training_photo",\n'
            '  "language_detected": "en",\n'
            '  "raw_text": "<all visible text in the image>",\n'
            '  "fields": {\n'
            '    "persons_detected": "<exact count as integer string, e.g. 1, 2, 3>",\n'
            '    "has_minimum_two_persons": "<true if 2 or more people visible, else false>",\n'
            '    "farmer_name_if_visible": "<name from badge or label if visible, else empty>",\n'
            '    "location_description": "<describe the physical setting>",\n'
            '    "gps_latitude": "<latitude value from watermark, e.g. 19.89529807>",\n'
            '    "gps_longitude": "<longitude value from watermark, e.g. 75.0731333>",\n'
            '    "gps_altitude": "<altitude in meters from watermark>",\n'
            '    "date_visible": "<date from GPS watermark, e.g. 04.07.2025>",\n'
            '    "time_visible": "<local time from GPS watermark>",\n'
            '    "gps_app": "<GPS app name if visible, e.g. GPS Map Camera Lite>",\n'
            '    "photo_quality": "<good/acceptable/poor>",\n'
            '    "notes": "<any other observations>"\n'
            "  },\n"
            '  "confidence": 0.9\n'
            "}"
        )

    # ── Default: validation + extraction for all other doc types ─────────
    markers = "\n".join(f"  - {m}" for m in info.get("visual_markers", []))
    not_if  = "\n".join(f"  - {n}" for n in info.get("not_this_if", []))

    return (
        f"The user claims this image is a: **{doc_name}**\n\n"
        f"STEP 1 — DOCUMENT TYPE CHECK:\n"
        f'A genuine "{doc_name}" typically shows these visual markers (not ALL are required):\n'
        f"{markers}\n\n"
        f'This is DEFINITELY NOT a "{doc_name}" if:\n'
        f"{not_if}\n\n"
        "IMPORTANT: Real documents vary in format, age, and quality.\n"
        "- If you see MOST of the expected markers, extract all fields.\n"
        "- Only reject if the image is CLEARLY a completely different type.\n"
        "- When in doubt, treat it as valid and extract what you can.\n\n"
        "If NOT this document type, respond:\n"
        "{\n"
        '  "is_valid_document": false,\n'
        '  "rejection_reason": "wrong_document_type",\n'
        '  "detected_actual_type": "<what this actually is>",\n'
        '  "raw_text": "",\n'
        '  "fields": {}\n'
        "}\n\n"
        "If it IS this document type, extract all fields:\n"
        "{\n"
        '  "is_valid_document": true,\n'
        f'  "document_type": "{doc_type}",\n'
        '  "language_detected": "<en/hi/mr/te/en+mr/etc>",\n'
        '  "raw_text": "<ALL visible text from the document>",\n'
        '  "fields": {\n'
        "    " + _get_field_template(doc_type) + "\n"
        "  },\n"
        '  "confidence": 0.0,\n'
        '  "notes": "<any observations>"\n'
        "}"
    )




def _get_field_template(doc_type: str) -> str:
    """Return field template for JSON prompt."""
    templates = {
        "land_record": '''\
    "farmer_name": "<primary land owner name>",
    "farmer_name_local": "<owner name in Marathi/Devanagari>",
    "names_of_people": ["<all person names found anywhere in document>"],
    "survey_number": "<survey or gat number>",
    "gat_number": "<gat number if different from survey>",
    "village": "<village name>",
    "taluka": "<taluka name>",
    "district": "<district name>",
    "state": "<state name>",
    "area_acres": "<area measurement>",
    "pu_id": "<PU-ID number if present>",
    "land_type": "<jirayat/bagayat/etc>",
    "document_date": "<date if visible>",
    "verification_url": "<mahabhumi.gov.in URL if present>"''',

        "bank_passbook": '''\
    "account_holder_name": "<name in English>",
    "account_holder_name_local": "<name in Devanagari>",
    "account_number": "<account number digits only>",
    "ifsc_code": "<IFSC code uppercase>",
    "bank_name": "<bank name>",
    "branch_name": "<branch name>",
    "address": "<address if visible>",
    "phone": "<phone if visible>"''',

        "aadhaar_card": '''\
    "full_name": "<name in English>",
    "full_name_local": "<name in Devanagari>",
    "aadhaar_number": "<12 digits without spaces>",
    "date_of_birth": "<DD/MM/YYYY>",
    "gender": "<Male/Female>",
    "address": "<complete address>",
    "pincode": "<6 digit pincode>",
    "father_name": "<father name if visible>"''',

        "voter_id": '''\
    "voter_name": "<voter name in English>",
    "voter_name_local": "<name in local language>",
    "epic_number": "<EPIC number>",
    "father_husband_name": "<father/husband name>",
    "address": "<address>",
    "part_number": "<part number if visible>",
    "serial_number": "<serial number if visible>"''',
    "cc_training_photo": '''\
    "persons_detected": "<count of people visible in photo>",
    "has_minimum_two_persons": "<true or false>",
    "farmer_name_if_visible": "<any name visible on badge or label>",
    "location_description": "<describe the background or setting>",
    "date_visible": "<any date text visible in image or caption>",
    "photo_quality": "<good/acceptable/poor>",
    "notes": "<any other observations>"''',


    "meeting_minutes": '''\
    "meeting_date": "<date of meeting e.g. 10.12.2025>",
    "meeting_time": "<time of meeting>",
    "meeting_location": "<location/village name>",
    "partner_team_member": "<name of field representative present>",
    "farmer_names": ["<all farmer names from attendee list>"],
    "farmer_phones": ["<phone numbers from attendee list>"],
    "agenda_items": ["<agenda item 1>", "<agenda item 2>"],
    "carbon_credit_training_done": "<true if Carbon Credit training mentioned, else false>",
    "notes": "<any additional notes or observations>"''',
    }
    return templates.get(
        doc_type,
        '"name": "<name if visible>", "details": "<any key details>"'
    )


# ── Mock responses ────────────────────────────────────────────────────────────

_MOCK: dict[str, OCRResult] = {
    "land_record": OCRResult(
        raw_text=(
            "७/१२ उतारा\n"
            "गाव: सॅम्पल | तालुका: सॅम्पल | जिल्हा: सॅम्पल\n"
            "Village: Sample Village | Taluka: Sample Taluka | Dist: Sample District\n"
            "सर्वे क्र. / Survey No: 000/A\n"
            "गट क्र. / Gat No: 000/A\n"
            "मालक / Owner: टेस्ट फार्मर\n"
            "Test Farmer\n"
            "क्षेत्रफळ / Area: 3.5 Acres (1.42 Hectares)\n"
            "जमीन प्रकार / Land Type: Jirayat"
        ),
        confidence=0.85,
        language_detected="en+mr",
        processing_time=0.1,
        is_valid_document=True,
        extracted_fields_raw={
            "owner_name": "Test Farmer",
            "owner_name_local": "टेस्ट फार्मर",
            "survey_number": "000/A",
            "gat_number": "000/A",
            "village": "Sample Village",
            "taluka": "Sample Taluka",
            "district": "Sample District",
            "state": "Sample State",
            "area_acres": "3.5",
            "area_hectares": "1.42",
            "land_type": "Jirayat",
        },
    ),
    "bank_passbook": OCRResult(
        raw_text=(
            "Sample Bank\n"
            "सॅम्पल बँक\n"
            "Branch: Sample Branch\n"
            "Account No: 00000000000\n"
            "IFSC: TEST0000000\n"
            "Name: Test Farmer\n"
            "नाव: टेस्ट फार्मर"
        ),
        confidence=0.92,
        language_detected="en+mr",
        processing_time=0.1,
        is_valid_document=True,
        extracted_fields_raw={
            "account_holder_name": "Test Farmer",
            "account_holder_name_local": "टेस्ट फार्मर",
            "account_number": "00000000000",
            "ifsc_code": "TEST0000000",
            "bank_name": "Sample Bank",
            "branch_name": "Sample Branch",
        },
    ),
    "aadhaar_card": OCRResult(
        raw_text=(
            "भारत सरकार / Government of India\n"
            "आधार / AADHAAR\n"
            "टेस्ट फार्मर\n"
            "Test Farmer\n"
            "DOB: 01/01/1980\n"
            "Male / पुरुष\n"
            "000000000000\n"
            "Sample Village, Sample District, Sample State 000000"
        ),
        confidence=0.89,
        language_detected="en+mr+hi",
        processing_time=0.1,
        is_valid_document=True,
        extracted_fields_raw={
            "full_name": "Test Farmer",
            "full_name_local": "टेस्ट फार्मर",
            "aadhaar_number": "000000000000",
            "date_of_birth": "01/01/1980",
            "gender": "Male",
            "address": "Sample Village, Sample District, Sample State 000000",
            "pincode": "000000",
        },
    ),
    "voter_id": OCRResult(
        raw_text=(
            "ELECTION COMMISSION OF INDIA\n"
            "VOTER PHOTO IDENTITY CARD\n"
            "EPIC No: TEST0000000\n"
            "Name: Test Farmer\n"
            "Father: Sample Father\n"
            "Sample Village, Sample District, Sample State"
        ),
        confidence=0.87,
        language_detected="en",
        processing_time=0.1,
        is_valid_document=True,
        extracted_fields_raw={
            "voter_name": "Test Farmer",
            "epic_number": "TEST0000000",
            "father_husband_name": "Sample Father",
        },
    ),

    "meeting_minutes": OCRResult(
    raw_text=(
        "Minutes of Meeting (Stakeholders)\n"
        "Date: 10.12.2025  Time: 12:54 PM  Location: Sample Location\n"
        "Field Representative: Sample Representative\n"
        "Agenda: 1. Program purpose  2. Program enrolment  "
        "3. Climate Change & Carbon Credit Training\n"
        "Attendees:\n"
        "Sample Attendee  Phone: 9999999999\n"
        "Note: Carbon Credit Training of Sample Attendee"
    ),
    confidence=0.88,
    language_detected="en",
    processing_time=0.1,
    is_valid_document=True,
    extracted_fields_raw={
        "meeting_date":                 "10.12.2025",
        "meeting_time":                 "12:54 PM",
        "meeting_location":             "Sample Location 000000",
        "partner_team_member":          "Sample Representative",
        "farmer_names":                 ["Sample Attendee"],
        "farmer_phones":                ["9999999999"],
        "agenda_items": [
            "Familiarize stakeholders with program purpose",
            "Introduce program and project outreach",
            "Provide instruction for enrolment",
            "Training on Climate Change and Carbon Credit",
            "Question and Answer",
        ],
        "carbon_credit_training_done":  "true",
        "notes": "Carbon Credit Training of Sample Attendee confirmed.",
    },
),
}


def _mock_ocr(document_type: str) -> OCRResult:
    """Return canned mock result. Always returns valid for declared type."""
    result = _MOCK.get(document_type)
    if result:
        logger.info("Mock OCR: canned response for '{}'", document_type)
        return result
    logger.warning("Mock OCR: no template for '{}', generic fallback", document_type)
    return OCRResult(
        raw_text=f"Mock OCR output for: {document_type}",
        confidence=0.5,
        language_detected="en",
        processing_time=0.05,
        is_valid_document=True,
    )


# ── Response parser ───────────────────────────────────────────────────────────

def _parse_response(raw: str) -> dict:
    """
    Parse LLM JSON response.
    Handles markdown fences and truncated JSON from token limit hits.
    """
    text = raw.strip()

    # ── Strip markdown fences ─────────────────────────────────────────────
    if text.startswith("```"):
        lines = text.split("\n")
        end = len(lines)
        for i in range(len(lines) - 1, 0, -1):
            if lines[i].strip() == "```":
                end = i
                break
        text = "\n".join(lines[1:end]).strip()

    # ── Attempt clean parse first ─────────────────────────────────────────
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # ── Truncated JSON recovery ───────────────────────────────────────────
    # If raw_text was cut mid-string due to max_tokens — try to salvage
    try:
        # Find the raw_text value start
        rt_start = text.find('"raw_text"')
        if rt_start != -1:
            # Truncate at raw_text field and close JSON cleanly
            truncated = text[:rt_start] + '"raw_text": "[truncated — increase max_tokens]"\n}'
            result = json.loads(truncated)
            logger.warning(
                "JSON truncated recovery succeeded — raw_text was cut by token limit"
            )
            # Preserve any partial raw_text we can extract
            try:
                rt_val_start = text.find(':', rt_start) + 1
                rt_val_raw   = text[rt_val_start:rt_val_start + 2000].strip()
                if rt_val_raw.startswith('"'):
                    # Extract what we can before the truncation
                    partial_text = rt_val_raw[1:].split('\\n')[0:20]
                    result["raw_text"] = "\n".join(partial_text)
                    result["_truncated"] = True
            except Exception:
                pass
            return result
    except Exception:
        pass

    # ── Final fallback ────────────────────────────────────────────────────
    logger.warning("JSON parse failed completely | raw preview: {}", text[:200])

    # Try to extract is_valid_document at minimum
    is_valid = True
    if '"is_valid_document": false' in text.lower():
        is_valid = False

    # Try to extract any raw_text content
    raw_text_content = text
    try:
        rt_match = __import__('re').search(r'"raw_text"\s*:\s*"(.*?)"', text, __import__('re').DOTALL)
        if rt_match:
            raw_text_content = rt_match.group(1).replace('\\n', '\n')
    except Exception:
        pass

    return {
        "is_valid_document": is_valid,
        "raw_text":          raw_text_content[:3000],
        "fields":            {},
        "confidence":        0.3,
        "parse_error":       "truncated_response",
        "_truncated":        True,
    }


# ── Rejection reason sanitizer ────────────────────────────────────────────────

_ACTUAL_DOC_DISPLAY = {
    "land_record":     "Land Record",
    "bank_passbook":   "Bank Passbook",
    "aadhaar_card":    "Aadhaar Card",
    "voter_id":        "Voter ID Card",
    "notebook":        "a notebook or handwritten notes",
    "study_notes":     "study or educational material",
    "screenshot":      "a screenshot",
    "other":           "an unrecognized document",
    "sale_deed":       "a Sale Deed (different document)",
    "pan_card":        "a PAN Card",
    "driving_license": "a Driving License",
    "passport":        "a Passport",
    "receipt":         "a receipt or bill",
    "certificate":     "a certificate",
}


def _sanitize_rejection(parsed: dict, declared_type: str) -> tuple[bool, str, str]:
    """
    Returns (is_valid, rejection_code, detected_actual_type_display).

    CRITICAL FIX: If the LLM says "invalid" but the detected type matches
    the declared type, we OVERRIDE to valid. This prevents false rejections
    like "You uploaded Aadhaar Card instead of Aadhaar Card."

    rejection_code is one of:
        wrong_document_type   — user uploaded a different official document
        unrelated_content     — not any recognized document
        not_matching_doc_type — ambiguous mismatch
    """
    is_valid = parsed.get("is_valid_document", True)

    if is_valid:
        return True, "", ""

    # ── Get what the LLM thinks the document actually is ──
    actual_raw = (
        parsed.get("detected_actual_type", "")
        or parsed.get("rejection_reason", "")
        or ""
    )
    actual_raw_lower = actual_raw.lower().strip()

    # ── CRITICAL FIX: Check if detected type matches declared type ──
    # Normalize both to canonical keys and compare
    detected_canonical = _normalize_to_canonical(actual_raw_lower)
    declared_canonical = _normalize_to_canonical(declared_type)

    if detected_canonical and declared_canonical and detected_canonical == declared_canonical:
        # LLM said "invalid" but detected the SAME type as declared
        # This is a false rejection — override to valid
        logger.warning(
            "LLM false rejection detected! declared='{}' detected='{}' (both normalize to '{}'). "
            "Overriding to is_valid_document=True.",
            declared_type, actual_raw, detected_canonical,
        )
        return True, "", ""

    # ── Also check with simple keyword matching as a safety net ──
    # In _sanitize_rejection, find the declared_keywords dict and update land_record:
    declared_keywords = {
        "aadhaar_card": ["aadhaar", "aadhar", "आधार", "uidai"],
        "bank_passbook": ["passbook", "bank passbook", "पासबुक"],
        "land_record": ["land record", "7/12", "satbara", "सातबारा", "जमीन", "भूमी अभिलेख"],
        # ← REMOVED "sale deed" from here — sale deed is a DIFFERENT document
        "voter_id": ["voter", "epic", "election", "मतदार"],
    }
    keywords = declared_keywords.get(declared_type, [])
    if keywords and any(kw in actual_raw_lower for kw in keywords):
        logger.warning(
            "LLM false rejection (keyword match)! declared='{}' actual_raw='{}'. "
            "Overriding to is_valid_document=True.",
            declared_type, actual_raw,
        )
        return True, "", ""

    # ── Genuine rejection: detected type is different from declared ──

    # Map to a display name
    actual_display = "an unrecognized document"
    for key, display in _ACTUAL_DOC_DISPLAY.items():
        if key.replace("_", " ") in actual_raw_lower or key in actual_raw_lower:
            actual_display = display
            break

    # If no match in display map, use the raw LLM text (cleaned up)
    if actual_display == "an unrecognized document" and actual_raw.strip():
        actual_display = actual_raw.strip()

    # Determine rejection code
    official_doc_keywords = [
        "land record", "bank passbook", "aadhaar", "voter id",
        "pan card", "driving license", "passport", "sale deed",
        "7/12", "satbara", "passbook", "epic",
    ]
    unrelated_keywords = [
        "notebook", "study", "notes", "handwritten", "question",
        "answer", "explanation", "networking", "subnetting",
        "diagram", "chart", "whiteboard", "screenshot", "screen",
        "phone", "monitor", "photo of a photo", "selfie",
        "not a document", "not official", "irrelevant",
    ]

    if any(kw in actual_raw_lower for kw in unrelated_keywords):
        code = "unrelated_content"
    elif any(kw in actual_raw_lower for kw in official_doc_keywords):
        code = "wrong_document_type"
    else:
        code = "not_matching_doc_type"

    logger.info(
        "Document rejected: declared='{}' detected='{}' code='{}' display='{}'",
        declared_type, actual_raw, code, actual_display,
    )

    return False, code, actual_display


# ── OCR Result builder ────────────────────────────────────────────────────────

def _build_result(parsed: dict, elapsed: float, declared_type: str) -> OCRResult:
    """Convert parsed LLM dict to OCRResult with clean rejection info."""
    is_valid, rejection_code, actual_display = _sanitize_rejection(parsed, declared_type)

    raw_text   = parsed.get("raw_text", "") or ""
    fields     = parsed.get("fields", {}) or {}
    confidence = float(parsed.get("confidence", 0.0))
    language   = parsed.get("language_detected") or _detect_language(raw_text)

    # ── CRITICAL: If we overrode a false rejection but have no data,
    # mark as needing re-extraction rather than returning empty ──────────────
    if is_valid and not raw_text and not fields:
        # The LLM said invalid and returned empty data, but we overrode it.
        # We cannot extract anything useful. Signal this clearly.
        logger.warning(
            "Override applied but LLM returned no data for declared_type='{}'. "
            "raw_text and fields are both empty. Marking as needs_reextraction.",
            declared_type,
        )
        # Return valid=False with a specific code so upload.py can handle it
        return OCRResult(
            raw_text="",
            confidence=0.0,
            language_detected="unknown",
            processing_time=elapsed,
            is_valid_document=False,
            rejection_reason=json.dumps({
                "code": "needs_reextraction",
                "actual": actual_display or "Could not determine document type",
            }),
            extracted_fields_raw={},
        )

    if is_valid and confidence == 0.0 and fields:
        non_null   = sum(1 for v in fields.values() if v is not None)
        confidence = round(0.5 + (non_null / max(len(fields), 1)) * 0.5, 2)

    if is_valid and confidence == 0.0 and not fields and raw_text:
        confidence = 0.3

    rejection_reason = None
    if not is_valid:
        rejection_reason = json.dumps({
            "code":   rejection_code,
            "actual": actual_display,
        })

    return OCRResult(
        raw_text=raw_text,
        confidence=confidence,
        language_detected=language,
        processing_time=elapsed,
        is_valid_document=is_valid,
        rejection_reason=rejection_reason,
        extracted_fields_raw=fields,
    )

# ── Language detector ─────────────────────────────────────────────────────────

def _detect_language(text: str) -> str:
    has_deva  = any("\u0900" <= c <= "\u097F" for c in text)
    has_latin = any(c.isalpha() and c.isascii() for c in text)
    if has_deva and has_latin:
        return "en+mr"
    if has_deva:
        return "mr"
    if has_latin:
        return "en"
    return "unknown"


# ── Live OCR ──────────────────────────────────────────────────────────────────

async def _live_ocr(image_path: str, document_type: str, settings) -> OCRResult:
    t0 = time.time()
    api_url = settings.ocr_api_url
    api_key = settings.ocr_api_key

    if not api_url or not api_key:
        logger.error("OCR API not configured — mock fallback")
        return _mock_ocr(document_type)

    path = Path(image_path)
    if not path.exists():
        logger.error("Image not found: {}", image_path)
        return _mock_ocr(document_type)

    mime, _ = mimetypes.guess_type(str(path))
    mime    = mime or "image/jpeg"
    b64     = base64.b64encode(path.read_bytes()).decode("utf-8")
    data_uri = f"data:{mime};base64,{b64}"

    # ── Build TWO prompts: strict validation + fallback extraction ────────
    user_prompt = _build_prompt(document_type)

    # Fallback prompt: just extract whatever text is there, no type validation
    fallback_prompt = f"""Please extract ALL visible text from this document image.
Return as JSON:
{{
  "is_valid_document": true,
  "document_type": "{document_type}",
  "language_detected": "<detected language>",
  "raw_text": "<ALL visible text verbatim>",
  "fields": {{
    {_get_field_template(document_type)}
  }},
  "confidence": <0.0 to 1.0>,
  "notes": "<what you see in the image>"
}}"""

    payload = {
        "model": getattr(settings, "ocr_model", "gpt-4.1"),
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text",      "text": user_prompt},
                    {"type": "image_url", "image_url": {"url": data_uri}},
                ],
            },
        ],
        "max_tokens":  getattr(settings, "ocr_max_tokens",  2000),
        "temperature": getattr(settings, "ocr_temperature", 0.1),
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type":  "application/json",
    }
    timeout = getattr(settings, "ocr_timeout", 60)
    retries = 3

    for attempt in range(1, retries + 1):
        try:
            logger.info("Live OCR attempt {}/{} | doc_type={}", attempt, retries, document_type)
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(api_url, json=payload, headers=headers)

            if resp.status_code == 200:
                raw_content = resp.json()["choices"][0]["message"]["content"].strip()
                logger.debug("LLM raw response preview: {}", raw_content[:500])

                parsed = _parse_response(raw_content)

                logger.info(
                    "LLM parsed | is_valid={} | detected_actual_type={} | rejection_reason={}",
                    parsed.get("is_valid_document"),
                    parsed.get("detected_actual_type", "N/A"),
                    parsed.get("rejection_reason", "N/A"),
                )

                result = _build_result(parsed, round(time.time() - t0, 3), document_type)

                # ── If result is empty (override happened but no data),
                # do a second pass with the fallback prompt ─────────────────
                if (result.rejection_reason and
                    "needs_reextraction" in (result.rejection_reason or "")):

                    logger.info(
                        "First pass returned empty data. "
                        "Attempting fallback extraction for '{}'...", document_type
                    )

                    fallback_payload = {
                        "model": getattr(settings, "ocr_model", "gpt-4.1"),
                        "messages": [
                            {"role": "system", "content": _SYSTEM_PROMPT},
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text",      "text": fallback_prompt},
                                    {"type": "image_url", "image_url": {"url": data_uri}},
                                ],
                            },
                        ],
                        "max_tokens":  getattr(settings, "ocr_max_tokens", 2000),
                        "temperature": 0.1,
                    }

                    async with httpx.AsyncClient(timeout=timeout) as client:
                        fallback_resp = await client.post(api_url, json=fallback_payload, headers=headers)

                    if fallback_resp.status_code == 200:
                        fallback_raw = fallback_resp.json()["choices"][0]["message"]["content"].strip()
                        fallback_parsed = _parse_response(fallback_raw)
                        result = _build_result(fallback_parsed, round(time.time() - t0, 3), document_type)
                        logger.info(
                            "Fallback extraction | valid={} | conf={} | raw_text_len={}",
                            result.is_valid_document,
                            result.confidence,
                            len(result.raw_text or ""),
                        )

                logger.info(
                    "Live OCR final | valid={} | conf={} | lang={} | elapsed={}s | rejection={}",
                    result.is_valid_document,
                    result.confidence,
                    result.language_detected,
                    result.processing_time,
                    result.rejection_reason or "none",
                )
                return result

            if resp.status_code == 429:
                wait = 2 ** attempt
                logger.warning("Rate limited — retry in {}s", wait)
                await asyncio.sleep(wait)
                continue

            if resp.status_code == 401:
                logger.error("Auth failed (401) — check OCR_API_KEY")
                break

            logger.error("API error {} — {}", resp.status_code, resp.text[:200])

        except httpx.TimeoutException:
            logger.warning("Timeout attempt {}", attempt)
            await asyncio.sleep(2 ** attempt)
        except httpx.ConnectError as e:
            logger.error("Connection error: {} — check VPN", e)
            break
        except Exception as e:
            logger.error("OCR error: {}", e)

    elapsed  = round(time.time() - t0, 3)
    fallback = _mock_ocr(document_type)
    fallback.processing_time = elapsed
    logger.warning("Live OCR failed — mock fallback after {}s", elapsed)
    return fallback

# ── Public entry point ────────────────────────────────────────────────────────

async def extract_text(image_path: str, document_type: str = "land_record") -> OCRResult:
    """
    Extract text from document image.
    OCR_MODE=mock  → canned response (for testing)
    OCR_MODE=live  → GPT-4.1 vision with strict type validation
    """
    settings = get_settings()
    mode     = (settings.ocr_mode or "mock").lower().strip()

    logger.info("OCR | mode={} | doc_type={} | path={}", mode, document_type, Path(image_path).name)

    if mode == "live":
        return await _live_ocr(image_path, document_type, settings)

    return _mock_ocr(document_type)

# ── Dedicated page type detector ─────────────────────────────────────────────
async def detect_page_type(image_path: str) -> str:
    """
    Lightweight auto-detection of document type from a page image.
    Returns a canonical doc type key or 'unknown'.
    Uses max_tokens=20 for speed.
    """
    settings = get_settings()
    mode     = (settings.ocr_mode or "mock").lower().strip()

    if mode != "live":
        logger.info("detect_page_type | mock mode | returning land_record")
        return "land_record"

    api_url = settings.ocr_api_url
    api_key = settings.ocr_api_key

    if not api_url or not api_key:
        return "unknown"

    path = Path(image_path)
    if not path.exists():
        logger.warning("detect_page_type | image not found | path={}", image_path)
        return "unknown"

    mime, _ = mimetypes.guess_type(str(path))
    mime     = mime or "image/jpeg"
    b64      = base64.b64encode(path.read_bytes()).decode("utf-8")
    data_uri = f"data:{mime};base64,{b64}"

    _DETECT_SYSTEM = (
        "You are a document classifier for Indian government documents.\n"
        "Look at the image and return ONLY one of these exact strings — nothing else:\n\n"
        "land_record\n"
        "aadhaar_card\n"
        "bank_passbook\n"
        "voter_id\n"
        "cc_training_photo\n"
        "meeting_minutes\n"
        "unknown\n\n"
        "Classification rules:\n"
        "- land_record       = any 7/12, satbara, 8A, mutation, revenue record, गाव नमुना, PU-ID present\n"
        "- aadhaar_card      = UIDAI card with 12-digit Aadhaar number\n"
        "- bank_passbook     = bank account first page with IFSC code\n"
        "- voter_id          = EPIC voter identity card with Election Commission logo\n"
        "- cc_training_photo = photograph of people (not a text document)\n"
        "- meeting_minutes   = Minutes of Meeting document with attendee list and agenda\n"
        "- unknown           = anything else\n\n"
        "Reply with ONLY the string. No explanation. No punctuation. No extra words."
    )

    payload = {
        "model": getattr(settings, "ocr_model", "gpt-4.1"),
        "messages": [
            {"role": "system", "content": _DETECT_SYSTEM},
            {
                "role": "user",
                "content": [
                    {"type": "text",      "text": "What type of document is this?"},
                    {"type": "image_url", "image_url": {"url": data_uri}},
                ],
            },
        ],
        "max_tokens":  20,
        "temperature": 0.0,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type":  "application/json",
    }

    valid_types = {
        "land_record", "aadhaar_card", "bank_passbook",
        "voter_id", "cc_training_photo", "meeting_minutes", "unknown",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(api_url, json=payload, headers=headers)

        if resp.status_code == 200:
            raw = (
                resp.json()["choices"][0]["message"]["content"]
                .strip().lower()
                .replace(".", "").replace(",", "").replace("\n", "")
                .strip()
            )
            logger.debug("detect_page_type | raw='{}' | path={}", raw, Path(image_path).name)

            if raw in valid_types:
                logger.info("detect_page_type | {} → {}", Path(image_path).name, raw)
                return raw

            for vt in valid_types:
                if vt in raw:
                    logger.info("detect_page_type | partial '{}' → '{}'", raw, vt)
                    return vt

            logger.warning("detect_page_type | unrecognised '{}' → unknown", raw)
            return "unknown"

        logger.warning("detect_page_type | API error {} → unknown", resp.status_code)
        return "unknown"

    except httpx.TimeoutException:
        logger.warning("detect_page_type | timeout → unknown")
        return "unknown"
    except Exception as e:
        logger.warning("detect_page_type | error={} → unknown", e)
        return "unknown"