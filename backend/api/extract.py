# backend/api/extract.py
"""
FarmerVerify AI — Structured Extraction Output Endpoint
Returns extracted fields in the partner export schema:
  FarmerName + NamesOfPeople + other fields as JSON
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from backend.database.document_store import read_result

router = APIRouter(tags=["extract"])


def _get_field(fields: dict, *keys: str) -> str:
    """
    Try multiple keys across both the top-level fields dict and the
    nested raw_fields dict. Returns the first non-empty value found.
    """
    raw = fields.get("raw_fields", {}) or {}

    for key in keys:
        # Try top-level first
        val = fields.get(key)
        if val and str(val).strip():
            return str(val).strip()
        # Try nested raw_fields
        val = raw.get(key)
        if val and str(val).strip():
            return str(val).strip()

    return ""


def _get_names_of_people(fields: dict) -> list[str]:
    """
    Collect all person names from both the top-level extracted_fields
    and the nested raw_fields, deduplicated and in order.
    """
    raw = fields.get("raw_fields", {}) or {}
    collected: list[str] = []

    # Sources to check, in priority order
    sources = [
        fields.get("names_of_people"),
        raw.get("names_of_people"),
        fields.get("farmer_name"),
        raw.get("farmer_name"),
        fields.get("farmer_name_local"),
        raw.get("farmer_name_local"),
        fields.get("name"),
        raw.get("name"),
        fields.get("name_local"),
        raw.get("name_local"),
        fields.get("full_name"),
        raw.get("full_name"),
        fields.get("full_name_local"),
        raw.get("full_name_local"),
        fields.get("owner_name"),
        raw.get("owner_name"),
        fields.get("owner_name_local"),
        raw.get("owner_name_local"),
    ]

    for source in sources:
        if not source:
            continue
        if isinstance(source, list):
            for item in source:
                if item and str(item).strip():
                    collected.append(str(item).strip())
        elif isinstance(source, str) and source.strip():
            collected.append(source.strip())

    # Deduplicate preserving order (case-insensitive)
    seen: set[str] = set()
    unique: list[str] = []
    for name in collected:
        key = name.lower()
        if key not in seen:
            seen.add(key)
            unique.append(name)

    return unique


@router.get("/extract/{request_id}/json")
async def get_extraction_json(request_id: str):
    """
    Returns extracted fields in the partner export schema:
      FarmerName, NamesOfPeople, plus all other extracted fields.
    Handles both flat and nested (raw_fields) field structures.
    """
    result = read_result(request_id)
    if not result:
        raise HTTPException(status_code=404, detail="Not found")

    fields = result.get("extracted_fields") or {}
    raw    = fields.get("raw_fields", {}) or {}

    # Merge raw_fields into a flat view for the output
    merged_fields: dict = {}
    # Start with raw_fields (more complete for land records)
    if raw:
        merged_fields.update(raw)
    # Then overlay top-level fields (may have regex-extracted extras)
    merged_fields.update({
        k: v for k, v in fields.items()
        if k != "raw_fields" and v is not None and not k.startswith("_")
    })

    # Resolve FarmerName — try all possible field names
    farmer_name = _get_field(
        fields,
        "farmer_name",
        "farmer_name_local",
        "name",
        "name_local",
        "full_name",
        "full_name_local",
        "owner_name",
        "owner_name_local",
    )

    # Resolve NamesOfPeople
    names_of_people = _get_names_of_people(fields)

    output = {
        "request_id":    request_id,
        "document_type": result.get("document_type", ""),

        # ── Partner required schema ──────────────────────────────────
        "FarmerName":    farmer_name,
        "NamesOfPeople": names_of_people,

        # ── All extracted fields (flat, no nesting, no nulls) ─────────
        "extracted_fields": {
            k: v for k, v in merged_fields.items()
            if v is not None and str(v).strip() not in ("", "None", "null")
        },

        # ── Pipeline scores ───────────────────────────────────────────
        "quality": {
            "overall_score": result.get("quality", {}).get("overall_score"),
            "is_acceptable": result.get("quality", {}).get("is_acceptable"),
        },
        "ocr_confidence": result.get("ocr", {}).get("confidence"),
        "match_score":    result.get("matching", {}).get("overall_score"),
        "fraud_risk":     result.get("fraud", {}).get("risk_score"),
        "status":         result.get("status"),
        "timestamp":      result.get("created_at"),
    }

    return JSONResponse(content=output)