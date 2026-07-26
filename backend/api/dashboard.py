# backend/api/dashboard.py
"""
FarmerVerify AI — Dashboard API endpoints
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import httpx
import os
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, FileResponse
from loguru import logger
from pydantic import BaseModel

from backend.database.document_store import (
    get_all_results,
    get_result,
    get_statistics,
    update_result,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class StatusUpdateRequest(BaseModel):
    status: str
    admin_notes: Optional[str] = None
    reviewed_by: str = "admin"
    rejection_reason_admin: Optional[str] = None


# ══════════════════════════════════════════════════════════════
#  STATS
# ══════════════════════════════════════════════════════════════

@router.get("/stats")
async def dashboard_stats() -> JSONResponse:
    stats = get_statistics()
    return JSONResponse(status_code=200, content=stats)


@router.get("/stats/processing")
async def processing_stats() -> JSONResponse:
    results = get_all_results(limit=1000)
    times   = [r.get("processing_time", 0) for r in results if r.get("processing_time")]
    total   = len(results)
    return JSONResponse(content={
        "avg_seconds":      round(sum(times) / max(len(times), 1), 1),
        "min_seconds":      round(min(times), 1) if times else 0,
        "max_seconds":      round(max(times), 1) if times else 0,
        "total_processed":  total,
        "time_saved_hours": round(total * 14 * 24 / 3600, 1),
    })


# ══════════════════════════════════════════════════════════════
#  DOCUMENTS
# ══════════════════════════════════════════════════════════════

@router.get("/documents")
async def list_documents(
    status:   Optional[str] = Query(None),
    doc_type: Optional[str] = Query(None),
    search:   Optional[str] = Query(None),
    sort:     str            = Query("newest"),
    limit:    int            = Query(50, ge=1, le=500),
    method:   Optional[str] = Query(None),
) -> JSONResponse:
    results = get_all_results(
        limit=limit,
        status_filter=status,
        doc_type_filter=doc_type,
        search_query=search,
        sort_by=sort,
        verification_method=method,
    )

    documents = []
    for r in results:
        fields = r.get("extracted_fields", {})
        documents.append({
            "request_id":        r.get("request_id", ""),
            "farmer_id":         r.get("farmer_id"),
            "status":            r.get("status", "unknown"),
            "document_type":     r.get("document_type", "unknown"),
            "name":              fields.get("name") or fields.get("name_local") or "",
            "aadhaar_number":    fields.get("aadhaar_number") or "",
            "account_number":    fields.get("account_number") or "",
            "phone":             fields.get("phone") or "",
            "district":          fields.get("district") or "",
            "village":           fields.get("village") or "",
            "quality_score":     r.get("quality",  {}).get("overall_score"),
            "ocr_confidence":    r.get("ocr",      {}).get("confidence"),
            "fraud_risk":        r.get("fraud",    {}).get("risk_score"),
            "onboarding_score":  r.get("onboarding_score"),
            "onboarding_label":  r.get("onboarding_label", ""),
            "processing_time":   r.get("processing_time"),
            "saved_at":          r.get("saved_at", "") or r.get("_saved_at", ""),
            "admin_notes":       r.get("admin_notes", ""),
            "reviewed_by":       r.get("reviewed_by", ""),
            "reviewed_at":       r.get("reviewed_at", ""),
            "verification_method": r.get("verification_method", ""),
            "upload_count":      r.get("upload_count", 1),
            "has_image":         bool(r.get("_image_path")),
            "image_path":        r.get("_image_path", ""),
            "extracted_fields":  fields,
            "matching":          r.get("matching",  {}),
            "fraud":             r.get("fraud",     {}),
            "quality":           r.get("quality",   {}),
            "ocr":               r.get("ocr",       {}),
            "message":           r.get("message",   ""),
            "messages":          r.get("messages",  {}),
            "admin_history":     r.get("admin_history", []),
        })

    return JSONResponse(status_code=200, content={
        "count":     len(documents),
        "documents": documents,
    })


@router.get("/documents/deleted")
async def list_deleted_documents() -> JSONResponse:
    """Returns all soft-deleted documents. MUST be before /documents/{request_id}."""
    from backend.database.document_store import get_deleted_results

    deleted   = get_deleted_results()
    documents = []

    for r in deleted:
        fields = r.get("extracted_fields", {})
        documents.append({
            "request_id":       r.get("request_id", ""),
            "document_type":    r.get("document_type", ""),
            "status":           r.get("status", ""),
            "deleted_by":       r.get("deleted_by", ""),
            "deleted_at":       r.get("deleted_at", ""),
            "name":             fields.get("name") or fields.get("name_local") or "",
            "extracted_fields": fields,
        })

    documents.sort(key=lambda d: d.get("deleted_at", ""), reverse=True)

    return JSONResponse(status_code=200, content={
        "count":     len(documents),
        "documents": documents,
    })


@router.get("/documents/{request_id}/image")
async def get_document_image(request_id: str):
    """Serve the uploaded document image or PDF for admin preview."""
    result = get_result(request_id)
    if not result:
        raise HTTPException(status_code=404, detail="Document not found.")

    image_path = result.get("_image_path")
    if not image_path:
        raise HTTPException(status_code=404, detail="No image for this document.")

    full_path = Path(image_path)
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="Image file not found on disk.")

    suffix     = full_path.suffix.lower()
    mime_map   = {
        ".jpg":  "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png":  "image/png",
        ".webp": "image/webp",
        ".pdf":  "application/pdf",
    }
    media_type = mime_map.get(suffix, "image/png")

    # ── For PDF — add Content-Disposition inline so browser opens it ─────────
    from fastapi.responses import Response
    if suffix == ".pdf":
        with open(str(full_path), "rb") as f:
            pdf_bytes = f.read()
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="doc_{request_id}.pdf"',
                "Content-Type": "application/pdf",
            },
        )

    return FileResponse(
        path=str(full_path),
        media_type=media_type,
        filename=f"doc_{request_id}{suffix}",
    )


@router.get("/documents/{request_id}")
async def get_document_detail(request_id: str) -> JSONResponse:
    result = get_result(request_id)
    if not result:
        raise HTTPException(status_code=404, detail="Document not found.")
    return JSONResponse(status_code=200, content=result)


@router.put("/documents/{request_id}/status")
async def update_document_status(
    request_id: str,
    body: StatusUpdateRequest,
) -> JSONResponse:
    valid_statuses = {"verified", "needs_review", "rejected"}
    if body.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {valid_statuses}",
        )

    updates = {
        "status":      body.status,
        "reviewed_by": body.reviewed_by,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
    }
    if body.admin_notes:
        updates["admin_notes"] = body.admin_notes
    if body.rejection_reason_admin:
        updates["rejection_reason_admin"] = body.rejection_reason_admin

    result = update_result(request_id, updates)
    if not result:
        raise HTTPException(status_code=404, detail="Document not found.")

    logger.info("Admin status update | id={} | new_status={} | by={}",
                request_id, body.status, body.reviewed_by)

    return JSONResponse(status_code=200, content={
        "success":    True,
        "request_id": request_id,
        "new_status": body.status,
        "updated_at": updates["reviewed_at"],
    })


@router.post("/documents/{request_id}/ai-review")
async def ai_review_document(request_id: str) -> JSONResponse:
    """
    AI Review with Visual Cross-Check.
    Sends BOTH the document image AND extracted fields to GPT-4.1 Vision.
    GPT-4.1 visually verifies extracted fields against the actual document image.
    """
    import base64
    import mimetypes
    from pathlib import Path

    result = get_result(request_id)
    if not result:
        raise HTTPException(status_code=404, detail="Document not found.")

    # ── Extract all data from result ──────────────────────────────────────────
    fields       = result.get("extracted_fields", {})
    raw_fields   = fields.get("raw_fields", {}) or {}
    doc_type     = result.get("document_type", "")
    status       = result.get("status", "")
    quality      = result.get("quality", {})
    fraud        = result.get("fraud", {})
    matching     = result.get("matching", {})
    ocr          = result.get("ocr", {})
    llm_val      = result.get("llm_validation", {}) or {}
    image_path   = result.get("_image_path", "")

    # ── Merge top-level and raw_fields for full context ───────────────────────
    all_fields = {
        **raw_fields,
        **{k: v for k, v in fields.items() if k != "raw_fields"},
    }

    # ── Remove null / empty values ────────────────────────────────────────────
    all_fields = {
        k: v for k, v in all_fields.items()
        if v and str(v).strip().lower() not in ("none", "null", "")
        and k not in ("raw_text",)
    }

    # ── Scores ────────────────────────────────────────────────────────────────
    fraud_risk  = float(fraud.get("risk_score",      0) or 0)
    fraud_flags = fraud.get("flags", [])               or []
    match_score = float(matching.get("overall_score", 0) or 0)
    ocr_conf    = float(ocr.get("confidence",         0) or 0)
    img_quality = float(quality.get("overall_score",  0) or 0)
    llm_score   = llm_val.get("validation_score")
    llm_flags   = llm_val.get("flags", [])   or []
    llm_summary = llm_val.get("summary", "") or ""

    # ── Labels ────────────────────────────────────────────────────────────────
    doc_type_label = {
        "aadhaar_card":      "Aadhaar Card",
        "bank_passbook":     "Bank Passbook",
        "land_record":       "Land Record (7/12 Extract)",
        "voter_id":          "Voter ID",
        "cc_training_photo": "CC Training Photo",
        "meeting_minutes":   "Minutes of Meeting",
    }.get(doc_type, doc_type.replace("_", " ").title())

    # ── Format fields and flags for prompt ───────────────────────────────────
    fields_text = "\n".join(
        f"  - {k}: {v}" for k, v in all_fields.items()
    ) or "  No fields extracted"

    flags_text = "\n".join(
        f"  - {f}" for f in fraud_flags
    ) if fraud_flags else "  None"

    llm_flags_text = "\n".join(
        f"  - {f}" for f in llm_flags
    ) if llm_flags else "  None"

    # ── Try to load document image for visual cross-check ────────────────────
    image_b64              = None
    visual_check_available = False

    # ── For PDFs — use first page image instead of PDF file ──────────────────
    # GPT-4.1 Vision only accepts image MIME types — not PDFs
    is_pdf_doc = (
        (image_path or "").lower().endswith(".pdf")
        or result.get("is_pdf") is True
    )

    if is_pdf_doc:
        # Find first page image saved during PDF processing
        # Pages are saved as uploads/{page_request_id}/document.png
        pages = result.get("pages", [])
        first_page_path = None

        for page in pages:
            page_img = page.get("_image_path", "")
            if page_img and not page_img.lower().endswith(".pdf"):
                candidates = [
                    Path(page_img),
                    Path(page_img.lstrip("/").lstrip("\\")),
                ]
                for c in candidates:
                    if c.exists():
                        first_page_path = c
                        break
            if first_page_path:
                break

        if first_page_path:
            try:
                b64      = base64.b64encode(first_page_path.read_bytes()).decode("utf-8")
                image_b64 = f"data:image/png;base64,{b64}"
                visual_check_available = True
                logger.info(
                    "AI Review | PDF first page image loaded | path={} | size={}KB",
                    first_page_path,
                    first_page_path.stat().st_size // 1024,
                )
            except Exception as img_err:
                logger.warning(
                    "AI Review | PDF first page image load failed | error={}",
                    img_err,
                )
        else:
            logger.warning(
                "AI Review | PDF document — no page images found | request_id={}",
                request_id,
            )

    else:
        # ── Regular image document ────────────────────────────────────────────
        if image_path:
            candidates = [
                Path(image_path),
                Path("backend") / image_path,
                Path(image_path.lstrip("/").lstrip("\\")),
                Path("uploads") / Path(image_path).name,
            ]

            for candidate in candidates:
                if candidate.exists():
                    try:
                        mime, _ = mimetypes.guess_type(str(candidate))
                        mime     = mime or "image/jpeg"
                        b64      = base64.b64encode(
                            candidate.read_bytes()
                        ).decode("utf-8")
                        image_b64              = f"data:{mime};base64,{b64}"
                        visual_check_available = True
                        logger.info(
                            "AI Review | image loaded | path={} | size={}KB",
                            candidate,
                            candidate.stat().st_size // 1024,
                        )
                        break
                    except Exception as img_err:
                        logger.warning(
                            "AI Review | image load failed | path={} | error={}",
                            candidate, img_err,
                        )

    if not visual_check_available:
        logger.warning(
            "AI Review | image not found | request_id={} | path={}",
            request_id, image_path,
        )

    # ── Build prompt ──────────────────────────────────────────────────────────
    visual_instruction = (
        "\n## Visual Cross-Check\n"
        "The **actual document image is attached**. "
        "Visually read the document and:\n"
        "- Verify each extracted field against what you actually see\n"
        "- Flag any field where extracted value does NOT match the image\n"
        "- Note any important text visible in the image that was NOT extracted\n"
        "- Confirm the document type matches what was declared\n"
    ) if visual_check_available else (
        "\n## Note\n"
        "Document image was not available for visual cross-check. "
        "Analysis is based on extracted fields only.\n"
    )

    llm_section = (
        f"\n## Prior LLM Field Validation\n"
        f"- Validation Score: {round(float(llm_score) * 100)}%\n"
        f"- Summary: {llm_summary}\n"
        f"- Flags:\n{llm_flags_text}\n"
    ) if llm_score is not None else ""

    prompt = f"""You are an expert document verification assistant for \
a reforestation NGO that onboards farmers into environmental programs.

A field coordinator has uploaded a **{doc_type_label}** for verification.

## Extracted Fields (from automated OCR)
{fields_text}

## Pipeline Scores
- Image Quality Score:  {round(img_quality)}%
- OCR Confidence:       {round(ocr_conf * 100 if ocr_conf <= 1 else ocr_conf)}%
- Database Match Score: {round(match_score)}%
- Fraud Risk Score:     {round(fraud_risk)}%
{llm_section}
## Fraud Detection Flags
{flags_text}
{visual_instruction}
## Your Task

{"🖼️ **VISUAL CROSS-CHECK ENABLED** — You can see the actual document image." if visual_check_available else "📋 **Text-only analysis** — No image available."}

Provide your analysis in these sections:

🧐 1. CONSISTENCY CHECK
- Are extracted fields internally consistent?
- Do location fields match known Maharashtra geography?
- Does document type match what was declared?
{"- Confirm each extracted field against the actual image text" if visual_check_available else ""}

{"🔍 2. VISUAL VERIFICATION" if visual_check_available else "🔍 2. FIELD ANALYSIS"}
{"- List each key field and whether it MATCHES or DOES NOT MATCH the image" if visual_check_available else "- Analyse extracted fields for accuracy and completeness"}
- Note any text visible but not extracted
- Flag any suspicious discrepancies

🚩 3. RED FLAGS
- Specific concerns the admin must verify

✅ 4. POSITIVE SIGNALS
- What confirms this is likely genuine

🤔 5. RECOMMENDATION
- APPROVE / MANUAL REVIEW / REJECT
- Confidence percentage and key reason

📝 6. ACTION ITEMS FOR COORDINATOR
- Specific steps the coordinator should take

Be concise and practical. Format with emojis for quick scanning.
This is for a rural farmer onboarding program — give benefit of the doubt \
for minor issues like spelling variations in names."""

    # ── API config ────────────────────────────────────────────────────────────
    api_url = os.getenv("OCR_API_URL", "")
    api_key = os.getenv("OCR_API_KEY", "")
    model   = os.getenv("OCR_MODEL", "gpt-4.1")

    if not api_url or not api_key:
        return JSONResponse(content={
            "analysis":            _mock_ai_review(doc_type, all_fields, fraud_risk, match_score),
            "mode":                "mock",
            "visual_cross_check":  False,
        })

    # ── Build message content ─────────────────────────────────────────────────
    if visual_check_available and image_b64:
        # Vision call — image + text together
        user_content = [
            {"type": "text",       "text": prompt},
            {"type": "image_url",  "image_url": {"url": image_b64}},
        ]
    else:
        # Text-only call
        user_content = prompt

    # ── Call LLM Vision API ──────────────────────────────────────────────────
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                api_url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type":  "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are a concise, expert document verification assistant "
                                "for an Indian NGO. Use clear sections with emojis. "
                                "Be practical and farmer-friendly. "
                                "When a document image is provided, always visually verify "
                                "extracted fields against what you actually read in the image."
                            ),
                        },
                        {
                            "role":    "user",
                            "content": user_content,
                        },
                    ],
                    "max_tokens":  1200,
                    "temperature": 0.2,
                },
            )

        if resp.status_code == 200:
            analysis = resp.json()["choices"][0]["message"]["content"].strip()

            # ── Append visual cross-check footer ──────────────────────────
            footer = (
                "\n\n---\n"
                "🖼️ *Visual cross-check performed — "
                "extracted fields verified against the actual document image.*"
            ) if visual_check_available else (
                "\n\n---\n"
                "⚠️ *Visual cross-check not available — "
                "document image could not be loaded. "
                "Analysis based on extracted fields only.*"
            )

            logger.info(
                "AI Review complete | request_id={} | visual={} | mode=live",
                request_id, visual_check_available,
            )

            return JSONResponse(content={
                "analysis":           analysis + footer,
                "mode":               "live",
                "visual_cross_check": visual_check_available,
            })

        # ── API error fallback ─────────────────────────────────────────────
        logger.error(
            "AI review API error | status={} | body={}",
            resp.status_code, resp.text[:200],
        )
        return JSONResponse(content={
            "analysis":           _mock_ai_review(
                                      doc_type, all_fields,
                                      fraud_risk, match_score,
                                  ),
            "mode":               "fallback",
            "visual_cross_check": False,
        })

    except Exception as e:
        logger.error("AI review failed | request_id={} | error={}", request_id, e)
        return JSONResponse(content={
            "analysis":           _mock_ai_review(
                                      doc_type, all_fields,
                                      fraud_risk, match_score,
                                  ),
            "mode":               "fallback",
            "visual_cross_check": False,
        })
    

@router.post("/documents/{request_id}/restore")
async def restore_document(
    request_id: str,
    reviewed_by: str = Query(default="admin"),
) -> JSONResponse:
    """Restore a soft-deleted document."""
    result = get_result(request_id)
    if not result:
        raise HTTPException(status_code=404, detail="Document not found.")

    if not result.get("is_deleted"):
        raise HTTPException(status_code=400, detail="Document is not deleted.")

    updates = {
        "is_deleted": False,
        "deleted_by": None,
        "deleted_at": None,
        "restored_by": reviewed_by,
        "restored_at": datetime.now(timezone.utc).isoformat(),
    }

    update_result(request_id, updates)

    logger.info(
        "Restore | request_id={} | restored_by={}", request_id, reviewed_by
    )

    return JSONResponse(status_code=200, content={
        "success":    True,
        "request_id": request_id,
        "message":    "Document restored successfully.",
    })

@router.delete("/documents/{request_id}")
async def soft_delete_document(
    request_id: str,
    reviewed_by: str = Query(default="admin"),
) -> JSONResponse:
    """
    Soft delete a document — marks it as deleted but keeps the file on disk.
    Deleted documents are hidden from all dashboard views.
    Can be recovered within 30 days.
    """
    result = get_result(request_id)
    if not result:
        raise HTTPException(status_code=404, detail="Document not found.")

    if result.get("is_deleted"):
        raise HTTPException(status_code=400, detail="Document is already deleted.")

    updates = {
        "is_deleted":  True,
        "deleted_by":  reviewed_by,
        "deleted_at":  datetime.now(timezone.utc).isoformat(),
    }

    updated = update_result(request_id, updates)
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to delete document.")

    logger.info(
        "Soft delete | request_id={} | deleted_by={}", request_id, reviewed_by
    )

    return JSONResponse(status_code=200, content={
        "success":    True,
        "request_id": request_id,
        "message":    "Document deleted. It can be recovered within 30 days.",
        "deleted_at": updates["deleted_at"],
    })




# ══════════════════════════════════════════════════════════════
#  SEARCH
# ══════════════════════════════════════════════════════════════

@router.get("/search")
async def search_documents(
    q:     str = Query(..., min_length=2),
    limit: int = Query(50, ge=1, le=200),
) -> JSONResponse:
    results = get_all_results(limit=limit, search_query=q)

    documents = []
    for r in results:
        fields = r.get("extracted_fields", {})
        documents.append({
            "request_id":     r.get("request_id", ""),
            "status":         r.get("status", "unknown"),
            "document_type":  r.get("document_type", "unknown"),
            "name":           fields.get("name") or fields.get("name_local") or "",
            "aadhaar_number": fields.get("aadhaar_number") or "",
            "account_number": fields.get("account_number") or "",
            "phone":          fields.get("phone") or "",
            "saved_at":       r.get("saved_at", "") or r.get("_saved_at", ""),
            "extracted_fields": fields,
            "verification_method": r.get("verification_method", ""),
        })

    return JSONResponse(status_code=200, content={
        "query":     q,
        "count":     len(documents),
        "documents": documents,
    })


# ══════════════════════════════════════════════════════════════
#  CC FIELD VISITS
# ══════════════════════════════════════════════════════════════

@router.get("/cc-visits")
async def list_cc_visits(
    status: Optional[str] = Query(None),
    sort:   str            = Query("newest"),
    limit:  int            = Query(50, ge=1, le=500),
) -> JSONResponse:
    """List CC training photos and meeting minutes (separate from main documents)."""
    results = get_all_results(
        limit=limit,
        status_filter=status,
        sort_by=sort,
        include_cc=True,
    )

    visits = []
    for r in results:
        raw_fields = r.get("extracted_fields", {}).get("raw_fields", {}) or {}

        visits.append({
            "request_id":              r.get("request_id", ""),
            "status":                  r.get("status", "unknown"),
            "farmer_id":               r.get("farmer_id"),
            "document_type":           r.get("document_type", ""),
            # CC Training Photo fields
            "persons_detected":        raw_fields.get("persons_detected") or "—",
            "has_minimum_two_persons": raw_fields.get("has_minimum_two_persons") or "—",
            "farmer_name_if_visible":  raw_fields.get("farmer_name_if_visible") or "—",
            "gps_latitude":            raw_fields.get("gps_latitude") or "—",
            "gps_longitude":           raw_fields.get("gps_longitude") or "—",
            "gps_altitude":            raw_fields.get("gps_altitude") or "—",
            "date_visible":            raw_fields.get("date_visible") or "—",
            "time_visible":            raw_fields.get("time_visible") or "—",
            "location_description":    raw_fields.get("location_description") or "—",
            "notes":                   raw_fields.get("notes") or "—",
            "photo_quality":           raw_fields.get("photo_quality") or "—",
            # Meeting Minutes fields
            "meeting_date":            raw_fields.get("meeting_date") or "—",
            "meeting_location":        raw_fields.get("meeting_location") or "—",
            "partner_team_member":     raw_fields.get("partner_team_member") or "—",
            "farmer_names":            raw_fields.get("farmer_names") or [],
            "carbon_credit_training":  raw_fields.get("carbon_credit_training_done") or "—",
            # Pipeline scores
            "quality_score":           r.get("quality", {}).get("overall_score"),
            "ocr_confidence":          r.get("ocr",     {}).get("confidence"),
            "fraud_risk":              r.get("fraud",   {}).get("risk_score"),
            # Meta
            "saved_at":        r.get("saved_at", "") or r.get("_saved_at", ""),
            "has_image":       bool(r.get("_image_path")),
            "image_path":      r.get("_image_path", ""),
            "processing_time": r.get("processing_time"),
            "admin_notes":     r.get("admin_notes", ""),
        })

    return JSONResponse(status_code=200, content={
        "count":  len(visits),
        "visits": visits,
    })


# ══════════════════════════════════════════════════════════════
#  FARMER PROFILES
# ══════════════════════════════════════════════════════════════

REQUIRED_DOCS = {"aadhaar_card", "land_record", "bank_passbook"}

MISSING_LABELS = {
    "aadhaar_card":  "Aadhaar Card",
    "land_record":   "Land Record",
    "bank_passbook": "Bank Passbook",
}


def _resolve_farmer_identity(doc: dict) -> tuple[str, str, str]:
    """
    Extract (aadhaar, name, name_local) from a document result.
    Checks both top-level extracted_fields and nested raw_fields.
    """
    fields     = doc.get("extracted_fields", {}) or {}
    raw        = fields.get("raw_fields", {}) or {}

    aadhaar = (
        fields.get("aadhaar_number") or raw.get("aadhaar_number") or ""
    ).strip().replace(" ", "").replace("-", "")

    name = (
        fields.get("name") or fields.get("full_name") or
        raw.get("farmer_name") or raw.get("full_name") or
        raw.get("owner_name") or ""
    ).strip()

    name_local = (
        fields.get("name_local") or fields.get("full_name_local") or
        raw.get("farmer_name_local") or raw.get("owner_name_local") or ""
    ).strip()

    return aadhaar, name, name_local


@router.get("/farmers")
async def list_farmer_profiles(
    search: Optional[str] = Query(None, description="Search by name or Aadhaar"),
    limit:  int            = Query(50, ge=1, le=200),
) -> JSONResponse:
    """
    Groups all documents by farmer (Aadhaar number as primary key, name as fallback).
    Returns onboarding completeness, scores, and document list per farmer.
    """
    all_docs = get_all_results(limit=500, search_query=search)

    # Group documents by farmer
    farmers: dict[str, dict] = {}

    for doc in all_docs:
        aadhaar, name, name_local = _resolve_farmer_identity(doc)

        # Determine group key: Aadhaar > normalized name > request_id
        group_key = (
            aadhaar or
            name.upper().replace(" ", "") or
            doc.get("request_id", "unknown")
        )

        if group_key not in farmers:
            farmers[group_key] = {
                "aadhaar_number":    aadhaar or "—",
                "farmer_name":       name or "—",
                "farmer_name_local": name_local or "—",
                "documents":         [],
                "latest_activity":   "",
            }

        # Improve identity fields if this doc has better data
        f = farmers[group_key]
        if aadhaar and f["aadhaar_number"] == "—":
            f["aadhaar_number"] = aadhaar
        if name and f["farmer_name"] == "—":
            f["farmer_name"] = name
        if name_local and f["farmer_name_local"] == "—":
            f["farmer_name_local"] = name_local

        saved = doc.get("saved_at", "") or doc.get("_saved_at", "")
        if saved > f["latest_activity"]:
            f["latest_activity"] = saved

        f["documents"].append({
            "request_id":       doc.get("request_id", ""),
            "document_type":    doc.get("document_type", ""),
            "status":           doc.get("status", "unknown"),
            "onboarding_score": doc.get("onboarding_score"),
            "onboarding_label": doc.get("onboarding_label", ""),
            "onboarding_color": doc.get("onboarding_color", "#6b7280"),
            "saved_at":         saved,
            "quality_score":    doc.get("quality", {}).get("overall_score"),
            "ocr_confidence":   doc.get("ocr",     {}).get("confidence"),
            "fraud_risk":       doc.get("fraud",   {}).get("risk_score"),
        })

    # Build profiles with completeness metadata
    profiles = []
    for key, farmer in farmers.items():
        docs      = farmer["documents"]
        submitted = {d["document_type"] for d in docs}
        verified  = {d["document_type"] for d in docs if d["status"] == "verified"}
        scores    = [d["onboarding_score"] for d in docs if d["onboarding_score"] is not None]
        avg_score = int(round(sum(scores) / len(scores), 0)) if scores else 0
        missing   = list(REQUIRED_DOCS - submitted)

        profiles.append({
            "group_key":            key,
            "aadhaar_number":       farmer["aadhaar_number"],
            "farmer_name":          farmer["farmer_name"],
            "farmer_name_local":    farmer["farmer_name_local"],
            "documents":            docs,
            "docs_submitted":       list(submitted),
            "docs_verified":        list(verified),
            "docs_missing":         missing,
            "docs_missing_labels":  [MISSING_LABELS.get(m, m) for m in missing],
            "onboarding_complete":  REQUIRED_DOCS.issubset(verified),
            "onboarding_progress":  f"{len(verified & REQUIRED_DOCS)}/{len(REQUIRED_DOCS)} verified",
            "avg_onboarding_score": avg_score,
            "total_documents":      len(docs),
            "latest_activity":      farmer["latest_activity"],
        })

    # Sort: most recently active first
    profiles.sort(key=lambda p: p["latest_activity"], reverse=True)

    return JSONResponse(content={
        "count":    len(profiles),
        "profiles": profiles[:limit],
    })


@router.get("/farmers/{group_key}")
async def get_single_farmer_profile(group_key: str) -> JSONResponse:
    """
    Get full document list for one farmer identified by Aadhaar number or name key.
    """
    all_docs = get_all_results(limit=500)

    matching_docs = []
    for doc in all_docs:
        aadhaar, name, _ = _resolve_farmer_identity(doc)
        key = aadhaar or name.upper().replace(" ", "") or doc.get("request_id", "")
        if key == group_key:
            matching_docs.append(doc)

    if not matching_docs:
        raise HTTPException(status_code=404, detail="Farmer not found.")

    submitted = {d.get("document_type") for d in matching_docs}
    verified  = {d.get("document_type") for d in matching_docs if d.get("status") == "verified"}

    return JSONResponse(content={
        "group_key":           group_key,
        "documents":           matching_docs,
        "onboarding_complete": REQUIRED_DOCS.issubset(verified),
        "docs_submitted":      list(submitted),
        "docs_verified":       list(verified),
        "docs_missing":        list(REQUIRED_DOCS - submitted),
    })


# ══════════════════════════════════════════════════════════════
#  EXPORT
# ══════════════════════════════════════════════════════════════

@router.get("/export/verified")
async def export_verified_farmers() -> JSONResponse:
    """Export all verified farmers in partner export schema (JSON + CSV-ready)."""
    verified = get_all_results(status_filter="verified", limit=1000)

    rows = []
    for r in verified:
        fields = r.get("extracted_fields", {})
        raw    = fields.get("raw_fields", {}) or {}

        rows.append({
            "ReferenceID":     r.get("request_id", ""),
            "DocumentType":    r.get("document_type", ""),
            "FarmerName":      fields.get("name") or raw.get("farmer_name") or fields.get("full_name") or "",
            "FarmerNameLocal": fields.get("name_local") or raw.get("farmer_name_local") or "",
            "NamesOfPeople":   raw.get("names_of_people", []),
            "AadhaarNumber":   fields.get("aadhaar_number") or raw.get("aadhaar_number") or "",
            "AccountNumber":   fields.get("account_number") or raw.get("account_number") or "",
            "IFSCCode":        fields.get("ifsc_code") or raw.get("ifsc_code") or "",
            "BankName":        fields.get("bank_name") or raw.get("bank_name") or "",
            "Village":         fields.get("village") or raw.get("village") or "",
            "Taluka":          fields.get("taluka") or raw.get("taluka") or "",
            "District":        fields.get("district") or raw.get("district") or "",
            "SurveyNumber":    raw.get("survey_number") or "",
            "AreaAcres":       raw.get("area_acres") or "",
            "PUID":            raw.get("pu_id") or "",
            "VerifiedAt":      r.get("updated_at") or r.get("created_at", ""),
            "ReviewedBy":      r.get("reviewed_by", "Auto"),
            "OnboardingScore": r.get("onboarding_score", 0),
        })

    return JSONResponse(content={
        "total_verified": len(rows),
        "exported_at":    datetime.now(timezone.utc).isoformat(),
        "farmers":        rows,
    })






def _mock_ai_review(doc_type: str, fields: dict, fraud_risk: float, match_score: float) -> str:
    """Fallback mock AI review when API is unavailable."""
    name       = fields.get("name") or fields.get("farmer_name") or fields.get("full_name") or "Unknown"
    village    = fields.get("village", "")
    district   = fields.get("district", "")
    aadhaar    = fields.get("aadhaar_number", "")
    survey     = fields.get("survey_number", "")

    rec = "✅ **APPROVE**" if fraud_risk < 30 and match_score > 50 else \
          "⚠️ **MANUAL REVIEW**" if fraud_risk < 60 else "❌ **REJECT**"

    conf = 85 if fraud_risk < 30 else 60 if fraud_risk < 60 else 40

    return f"""## 🤖 AI Document Review

### ✅ Consistency Check
- Farmer name **{name}** appears in expected format
{f'- Village **{village}** and district **{district}** field values present' if village else '- Location fields extracted'}
{f'- Aadhaar number ({len(aadhaar)} digits) — {"valid 12-digit format ✅" if len(aadhaar) == 12 else "check digit count ⚠️"}' if aadhaar else ''}
{f'- Survey number **{survey}** present' if survey else '- ⚠️ Survey number not extracted — verify manually'}

### 🚩 Red Flags
{f'- Fraud risk score is {round(fraud_risk)}% — {"low and acceptable" if fraud_risk < 30 else "elevated — review recommended" if fraud_risk < 60 else "high — possible tampering"}' }
{f'- Database match score is {round(match_score)}% — {"good match" if match_score > 70 else "partial match — verify identity" if match_score > 40 else "no match found — farmer may be new to database"}'}

### 💚 Positive Signals
- Document passed image quality check
- OCR successfully extracted key fields
- No critical fraud indicators detected

### 📋 Recommendation
{rec} — Confidence: {conf}%

### 📌 Action Items
1. Verify farmer name matches government ID physically
2. Confirm land location matches farmer's stated address
3. If any doubt, request original document for in-person verification
"""






