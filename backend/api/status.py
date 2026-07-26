# backend/api/status.py
"""
FarmerVerify AI — Status endpoint
GET /status/{document_id}   (prefix /api/v1 added by routes.py)
GET /status                 (list recent results for dev/demo)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from loguru import logger

router = APIRouter(tags=["status"])

# ── Results directory — must match what document_store.py uses ──
RESULTS_DIR = Path(__file__).resolve().parent.parent.parent / "results"


def _find_result_file(document_id: str) -> Optional[Path]:
    """
    Find the JSON result file matching a document_id (request_id).

    document_store.py saves files as:
        results/{request_id}.json  ← FLAT FILE

    So we look for exact filename match first,
    then fall back to startswith for partial matches.
    """
    document_id = document_id.strip().lower()

    if not document_id or len(document_id) < 6:
        return None

    if not RESULTS_DIR.exists():
        return None

    # ── FIX 1: Exact filename match first ──
    exact_path = RESULTS_DIR / f"{document_id}.json"
    if exact_path.exists():
        logger.debug("Exact match found | path={}", exact_path)
        return exact_path

    # ── FIX 2: Partial match fallback (startswith on filename stem) ──
    matches = sorted(
        [
            f for f in RESULTS_DIR.glob("*.json")
            if f.stem.lower().startswith(document_id)
        ],
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )

    if matches:
        logger.debug("Partial match found | path={}", matches[0])
        return matches[0]

    return None


def _load_result(file_path: Path) -> dict:
    """Load and return a JSON result file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/status/{document_id}")
async def get_document_status(document_id: str) -> JSONResponse:
    """
    Retrieve the verification status of a previously uploaded document.

    The document_id is the Reference ID shown to the user (12-char hex).
    It matches the request_id generated during upload.
    """
    logger.info("Status lookup | document_id={}", document_id)

    file_path = _find_result_file(document_id)

    if not file_path:
        logger.info("Status lookup not found | document_id={}", document_id)
        raise HTTPException(
            status_code=404,
            detail={
                "en": f"No document found with Reference ID '{document_id}'.",
                "hi": f"संदर्भ ID '{document_id}' से कोई दस्तावेज़ नहीं मिला।",
                "mr": f"संदर्भ ID '{document_id}' ने कोणताही दस्तऐवज सापडला नाही.",
            },
        )

    try:
        result = _load_result(file_path)
        logger.info(
            "Status lookup found | document_id={} | file={} | status={}",
            document_id,
            file_path.name,
            result.get("status", "unknown"),
        )
        return JSONResponse(status_code=200, content=result)

    except Exception as e:
        logger.error(
            "Failed to read result file | document_id={} | file={} | error={}",
            document_id,
            file_path,
            e,
        )
        raise HTTPException(
            status_code=500,
            detail="Error reading verification result. Please try again.",
        )


@router.get("/status")
async def list_recent(
    limit: int = Query(
        default=20, ge=1, le=100, description="Max results to return"
    ),
) -> JSONResponse:
    """
    Return the most recent verification results (for dev/demo convenience).
    Lists document IDs, status, document type, and timestamps.
    """
    if not RESULTS_DIR.exists():
        return JSONResponse(
            status_code=200,
            content={"count": 0, "results": []},
        )

    # ── Flat JSON files sorted by modification time newest first ──
    files = sorted(
        RESULTS_DIR.glob("*.json"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )[:limit]

    results = []
    for file in files:
        try:
            data = _load_result(file)
            results.append(
                {
                    "request_id": data.get("request_id", file.stem),
                    "status": data.get("status", "unknown"),
                    "document_type": data.get("document_type", "unknown"),
                    "farmer_id": data.get("farmer_id"),
                    "file": file.name,
                    "message": data.get("message", ""),
                }
            )
        except Exception as e:
            logger.warning(
                "Skipping corrupt result file: {} | error={}", file.name, e
            )

    return JSONResponse(
        status_code=200,
        content={
            "count": len(results),
            "results": results,
        },
    )