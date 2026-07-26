"""
document_store.py — JSON-file persistence layer for FarmerVerify AI.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

RESULTS_DIR = Path(__file__).resolve().parent.parent.parent / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

_CC_DOC_TYPES = {"cc_training_photo", "meeting_minutes"}
    

def _result_path(request_id: str) -> Path:
    return RESULTS_DIR / f"{request_id}.json"


def _read_json(path: Path) -> dict | None:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        logger.debug("Could not read %s: %s", path, exc)
        return None


def _write_json(path: Path, data: dict) -> Path:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, default=str)
    return path


def _find_file_for_id(request_id: str) -> Path | None:
    canonical = _result_path(request_id)
    if canonical.exists():
        return canonical
    matches = sorted(RESULTS_DIR.glob(f"{request_id}_*.json"))
    if matches:
        return matches[-1]
    return None


def save_result(request_id: str, doc_type: str, payload: dict) -> Path:
    """
    Persist a verification result to disk.
    NEVER fails silently — logs full traceback on any error.
    """
    import traceback

    payload.setdefault("request_id", request_id)
    payload.setdefault("document_type", doc_type)
    payload.setdefault("created_at", datetime.now(timezone.utc).isoformat())
    payload.setdefault("updated_at", datetime.now(timezone.utc).isoformat())

    path = _result_path(request_id)

    try:
        # First attempt: standard serialization
        _write_json(path, payload)
        logger.info("Saved result %s → %s", request_id, path)
        return path

    except TypeError as e:
        # Non-serializable object in payload — sanitize and retry
        logger.error(
            "save_result: JSON serialization failed for %s: %s\n%s",
            request_id, e, traceback.format_exc(),
        )

        # Deep sanitize: convert everything to basic Python types
        def _sanitize(obj):
            if obj is None:
                return None
            if isinstance(obj, (str, int, float, bool)):
                return obj
            if isinstance(obj, dict):
                return {str(k): _sanitize(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple)):
                return [_sanitize(i) for i in obj]
            # Pydantic model (v2)
            if hasattr(obj, "model_dump"):
                return _sanitize(obj.model_dump())
            # Pydantic model (v1)
            if hasattr(obj, "dict"):
                return _sanitize(obj.dict())
            # Anything else — convert to string
            return str(obj)

        sanitized = _sanitize(payload)
        if not isinstance(sanitized, dict):
            sanitized = {"value": sanitized}
        _write_json(path, sanitized)
        logger.info("Saved result %s (after sanitization) → %s", request_id, path)
        return path

    except Exception as e:
        logger.error(
            "save_result: FATAL ERROR saving %s: %s\n%s",
            request_id, e, traceback.format_exc(),
        )
        raise


def read_result(request_id: str) -> dict | None:
    path = _find_file_for_id(request_id)
    if path is None:
        return None
    data = _read_json(path)
    if data is None:
        return None
    if data.get("is_redirect") is True:
        original_id = data.get("original_request_id")
        if original_id:
            original_path = _find_file_for_id(original_id)
            if original_path:
                original_data = _read_json(original_path)
                if original_data and not original_data.get("is_redirect"):
                    return original_data
        logger.warning(
            "read_result: broken redirect in %s — original not found",
            path.name,
        )
        return None
    return data


get_result = read_result


def update_result(request_id: str, updates: dict) -> dict | None:
    data = read_result(request_id)
    if data is None:
        logger.warning("update_result: %s not found", request_id)
        return None

    data.update(updates)

    new_status  = updates.get("status")
    reviewed_by = updates.get("reviewed_by", "Admin")

    if new_status == "verified":
        data["message"] = (
            f"✅ Your document has been verified and approved by {reviewed_by}. "
            f"Your onboarding is complete!"
        )
        data["messages"] = {
            "en": (
                f"✅ Your document has been verified and approved by {reviewed_by}. "
                f"Your onboarding is complete!"
            ),
            "hi": (
                f"✅ आपका दस्तावेज़ {reviewed_by} द्वारा सत्यापित और स्वीकृत हो गया। "
                f"आपका पंजीकरण पूर्ण!"
            ),
            "mr": (
                f"✅ तुमचा दस्तऐवज {reviewed_by} यांनी सत्यापित आणि मंजूर केला. "
                f"तुमची नोंदणी पूर्ण!"
            ),
        }
    elif new_status == "rejected":
        reason = (
            updates.get("rejection_reason_admin") or
            updates.get("admin_notes") or
            "Please contact the NGO office for details."
        )
        data["message"] = f"❌ Document rejected by {reviewed_by}. {reason}"
        data["messages"] = {
            "en": f"❌ Document rejected by {reviewed_by}. {reason}",
            "hi": f"❌ {reviewed_by} द्वारा दस्तावेज़ अस्वीकृत। {reason}",
            "mr": f"❌ {reviewed_by} यांनी दस्तऐवज नाकारला. {reason}",
        }
    elif new_status == "needs_review":
        data["message"] = "⚠️ Document sent back for manual review."
        data["messages"] = {
            "en": "⚠️ Document sent back for manual review.",
            "hi": "⚠️ दस्तावेज़ पुनः मैन्युअल समीक्षा के लिए भेजा गया।",
            "mr": "⚠️ दस्तऐवज मॅन्युअल पुनरावलोकनासाठी परत पाठवला.",
        }

    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    path = _result_path(request_id)
    _write_json(path, data)
    logger.info("Updated result %s | new_status=%s", request_id, new_status)
    return data


def _load_all_results() -> list[dict]:
    results: list[dict] = []
    for path in RESULTS_DIR.glob("*.json"):
        data = _read_json(path)
        if data is None:
            continue
        if data.get("is_redirect"):
            continue
        if data.get("is_deleted"):
            continue
        results.append(data)
    return results

def get_deleted_results() -> list[dict]:
    """Return only soft-deleted documents (for the Deleted Items view)."""
    results: list[dict] = []
    for path in RESULTS_DIR.glob("*.json"):
        data = _read_json(path)
        if data is None:
            continue
        if data.get("is_redirect"):
            continue
        if data.get("is_deleted"):
            results.append(data)
    return results


def get_all_results(
    limit: int = 200,
    status_filter: str | None = None,
    doc_type_filter: str | None = None,
    search_query: str | None = None,
    sort_by: str = "newest",
    verification_method: str | None = None,
    include_cc: bool = False,
) -> list[dict]:
    results = _load_all_results()

    if include_cc:
        results = [r for r in results if r.get("document_type") in _CC_DOC_TYPES]
    else:
        results = [r for r in results if r.get("document_type") not in _CC_DOC_TYPES]

    if status_filter:
        sf = status_filter.lower()
        results = [r for r in results if str(r.get("status", "")).lower() == sf]

    if doc_type_filter:
        df = doc_type_filter.lower()
        results = [r for r in results if str(r.get("document_type", "")).lower() == df]

    if verification_method:
        vm = verification_method.lower()
        results = [r for r in results if str(r.get("verification_method", "")).lower() == vm]

    if search_query:
        q = search_query.lower()
        def _matches(r: dict) -> bool:
            searchable = " ".join(
                str(r.get(k, ""))
                for k in ("request_id", "farmer_id", "farmer_name", "document_type")
            ).lower()
            return q in searchable
        results = [r for r in results if _matches(r)]

    if sort_by == "oldest":
        results.sort(key=lambda r: r.get("created_at", ""))
    elif sort_by == "score_high":
        results.sort(key=lambda r: r.get("overall_score", 0), reverse=True)
    elif sort_by == "score_low":
        results.sort(key=lambda r: r.get("overall_score", 0))
    else:
        results.sort(key=lambda r: r.get("created_at", ""), reverse=True)

    return results[:limit]


def get_statistics() -> dict:
    """
    Compute real-time statistics reading directly from result files.
    Handles flat records, PDF batch records, and skips redirects/deleted.
    """
    status_counts:   dict[str, int] = {}
    doc_type_counts: dict[str, int] = {}
    processing_times: list[float]   = []
    auto_verified  = 0
    fraud_flagged  = 0
    cc_pending     = 0
    cc_confirmed   = 0
    cc_flagged     = 0
    total          = 0

    for path in RESULTS_DIR.glob("*.json"):
        data = _read_json(path)
        if data is None:
            continue

        # ── Skip redirect stubs ───────────────────────────────────────────
        if data.get("is_redirect"):
            continue

        # ── Skip soft-deleted ─────────────────────────────────────────────
        if data.get("is_deleted"):
            continue

        doc_type = str(data.get("document_type", "unknown")).lower()
        status   = str(data.get("status",        "unknown")).lower()

        # ── CC documents — count separately ──────────────────────────────
        if doc_type in ("cc_training_photo", "meeting_minutes"):
            if status == "needs_review":
                cc_pending += 1
            elif status == "verified":
                cc_confirmed += 1
            elif status == "rejected":
                cc_flagged += 1
            continue  # do not count CC in main total

        # ── Main document counts ──────────────────────────────────────────
        total += 1

        status_counts[status] = status_counts.get(status, 0) + 1
        doc_type_counts[doc_type] = doc_type_counts.get(doc_type, 0) + 1

        # ── Processing time ───────────────────────────────────────────────
        pt = data.get("processing_time") or data.get("total_processing_time")
        if pt is not None:
            try:
                processing_times.append(float(pt))
            except (ValueError, TypeError):
                pass

        # ── Auto verified ─────────────────────────────────────────────────
        method = data.get("verification_method", "")
        score  = float(data.get("onboarding_score", 0) or 0)
        if method in ("auto", "auto_low_confidence") or score >= 80:
            auto_verified += 1

        # ── Fraud flagged ─────────────────────────────────────────────────
        fraud = data.get("fraud") or data.get("fraud_detection") or {}
        if isinstance(fraud, dict):
            risk = float(fraud.get("risk_score", 0) or 0)
            if fraud.get("is_suspicious") or risk >= 70:
                fraud_flagged += 1

    avg_time = round(
        sum(processing_times) / len(processing_times), 1
    ) if processing_times else 0.0

    return {
        "total_documents":     total,
        "status_counts":       status_counts,
        "doc_type_counts":     doc_type_counts,
        "average_score":       0.0,
        "fraud_flagged":       fraud_flagged,
        "auto_verified_count": auto_verified,
        "avg_processing_time": avg_time,
        "last_updated":        datetime.now(timezone.utc).isoformat(),
        "cc_total":            cc_pending + cc_confirmed + cc_flagged,
        "cc_pending":          cc_pending,
        "cc_confirmed":        cc_confirmed,
        "cc_flagged":          cc_flagged,
    }

def _extract_pu_id_from_text(text: str) -> str:
    """Extract PU-ID from raw text using multiple patterns."""
    if not text:
        return ""

    import re

    # ── Pattern 1: Standard format — PU-ID : 33345411062 ─────────────────────
    patterns = [
        r'PU-ID\s*[:\-]\s*(\d{8,15})',
        r'PU\s*ID\s*[:\-]\s*(\d{8,15})',
        r'PU-ID\s*(\d{8,15})',
        # ── Pattern 2: Account number that looks like PU-ID (11-15 digits) ──
        r'\b(3334\d{7,11})\b',          # PU-IDs starting with 3334
        r'\b(\d{11})\b',                # Any 11-digit number — likely PU-ID
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            val = match.group(1).strip()
            if len(val) >= 8:
                return val

    return ""


def _extract_village_from_text(text: str) -> str:
    if not text:
        return ""
    patterns = [
        r"गाव\s*[:\-]\s*([^\(\n]+?)(?:\s*\(|$|\n)",
        r"village\s*[:\-]\s*([^\(\n,]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            val = match.group(1).strip()
            if len(val) > 2:
                return val.upper().replace(" ", "")
    return ""


def _extract_taluka_from_text(text: str) -> str:
    if not text:
        return ""
    patterns = [
        r"तालुका\s*[:\-]\s*([^\n,]+)",
        r"taluka\s*[:\-]\s*([^\n,]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            val = match.group(1).strip()
            if len(val) > 1:
                return val.upper().replace(" ", "")
    return ""


def _get_field_value(extracted_fields: dict, *keys: str) -> str:
    if not extracted_fields:
        return ""
    raw = extracted_fields.get("raw_fields", {}) or {}
    for k in keys:
        val = extracted_fields.get(k)
        if val and str(val).strip().lower() not in ("", "none", "null"):
            return (
                str(val).strip().upper()
                .replace(" ", "").replace("-", "").replace("/", "")
            )
        val = raw.get(k)
        if val and str(val).strip().lower() not in ("", "none", "null"):
            return (
                str(val).strip().upper()
                .replace(" ", "").replace("-", "").replace("/", "")
            )
    return ""


def compute_fingerprint(doc_type: str, extracted_fields: dict | None) -> str | None:
    if not extracted_fields:
        return None

    parts: list[str] = [doc_type.lower()]

    raw_text = (
        extracted_fields.get("raw_text", "")
        or (extracted_fields.get("raw_fields", {}) or {}).get("raw_text", "")
        or ""
    )

    if doc_type == "aadhaar_card":
        val = _get_field_value(extracted_fields, "aadhaar_number")
        if val:
            parts.append(f"aadhaar={val}")

    elif doc_type == "bank_passbook":
        acc  = _get_field_value(extracted_fields, "account_number")
        ifsc = _get_field_value(extracted_fields, "ifsc_code", "ifsc")
        if acc:
            parts.append(f"account={acc}")
        if ifsc:
            parts.append(f"ifsc={ifsc}")

    elif doc_type == "land_record":
        pu_id = _get_field_value(extracted_fields, "pu_id")
        if not pu_id and raw_text:
            pu_id = _extract_pu_id_from_text(raw_text)
        if pu_id:
            parts.append(f"puid={pu_id}")
        else:
            village  = _get_field_value(extracted_fields, "village")
            taluka   = _get_field_value(extracted_fields, "taluka")
            district = _get_field_value(extracted_fields, "district")
            if not village and raw_text:
                village = _extract_village_from_text(raw_text)
            if not taluka and raw_text:
                taluka = _extract_taluka_from_text(raw_text)
            if village:
                parts.append(f"village={village}")
            if taluka:
                parts.append(f"taluka={taluka}")
            if district:
                parts.append(f"district={district}")

    elif doc_type == "voter_id":
        val = _get_field_value(extracted_fields, "epic_number")
        if val:
            parts.append(f"epic={val}")

    elif doc_type == "cc_training_photo":
        lat  = _get_field_value(extracted_fields, "gps_latitude")
        lon  = _get_field_value(extracted_fields, "gps_longitude")
        date = _get_field_value(extracted_fields, "date_visible")
        if lat:
            parts.append(f"lat={lat}")
        if lon:
            parts.append(f"lon={lon}")
        if date:
            parts.append(f"date={date}")

    elif doc_type == "meeting_minutes":
        loc  = _get_field_value(extracted_fields, "meeting_location")
        date = _get_field_value(extracted_fields, "meeting_date")
        rep  = _get_field_value(extracted_fields, "partner_team_member")
        if loc:
            parts.append(f"loc={loc}")
        if date:
            parts.append(f"date={date}")
        if rep:
            parts.append(f"rep={rep}")

    if len(parts) == 1:
        logger.warning(
            "compute_fingerprint: no key fields for doc_type=%s — cannot fingerprint",
            doc_type,
        )
        return None

    raw = "|".join(parts)
    fingerprint = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    logger.debug("Fingerprint | doc_type=%s | parts=%s | hash=%s", doc_type, parts, fingerprint[:16])
    return fingerprint


def find_existing_by_fingerprint(fingerprint: str) -> dict | None:
    """
    Scan results for a matching fingerprint.
    Reads directly from JSON files — does NOT follow redirects.
    Includes soft-deleted records so dedup works even after admin deletion.
    """
    if not fingerprint:
        return None

    for path in RESULTS_DIR.glob("*.json"):
        data = _read_json(path)
        if data is None:
            continue

        # ── Skip redirect stubs — only match canonical records ────────────────
        if data.get("is_redirect"):
            continue

        # ── Skip if fingerprint does not match ────────────────────────────────
        if data.get("fingerprint") != fingerprint:
            continue

        # ── Skip records with no request_id ──────────────────────────────────
        rid = data.get("request_id", "")
        if not rid:
            logger.warning(
                "find_existing_by_fingerprint: match in %s has no request_id — skipping",
                path.name,
            )
            continue

        # ── Return directly — include soft-deleted, skip redirect following ───
        # Using data directly instead of read_result() prevents false misses
        # when soft-deleted records have broken redirect chains
        logger.info(
            "find_existing_by_fingerprint: match | fingerprint=%s | "
            "request_id=%s | is_deleted=%s",
            fingerprint[:16],
            rid,
            data.get("is_deleted", False),
        )
        return data

    return None

def save_redirect(new_id: str, original_id: str) -> Path:
    """Write a redirect stub. Only called when original is confirmed to exist."""
    stub = {
        "request_id":          new_id,
        "is_redirect":         True,
        "original_request_id": original_id,
        "created_at":          datetime.now(timezone.utc).isoformat(),
    }
    path = _result_path(new_id)
    _write_json(path, stub)
    logger.info("Redirect stub: %s → %s", new_id, original_id)
    return path

# Add to the bottom of document_store.py alongside the other aliases
get_deleted = get_deleted_results