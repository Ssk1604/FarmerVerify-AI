"""
FarmerVerify AI — Manual validation endpoint
POST /validate   (prefix /api/v1 added by routes.py)

Used by NGO staff to override or confirm automated results.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.utils import get_logger
from backend.api.status import _document_store, save_result

router = APIRouter(tags=["validate"])     # ← NO prefix
logger = get_logger("validate")


class ManualValidationRequest(BaseModel):
    document_id: str
    decision: str           # "approve" | "reject" | "request_reupload"
    reviewer_name: str = "staff"
    notes: str = ""


@router.post("/validate")
async def manual_validate(req: ManualValidationRequest):
    """
    NGO staff can manually approve, reject, or request re-upload
    for a document that went to REVIEW status.
    """
    logger.info(
        "Manual validation",
        document_id=req.document_id,
        decision=req.decision,
        reviewer=req.reviewer_name,
    )

    if req.decision not in ("approve", "reject", "request_reupload"):
        raise HTTPException(
            status_code=400,
            detail="decision must be one of: approve, reject, request_reupload",
        )

    existing = _document_store.get(req.document_id)

    if not existing:
        raise HTTPException(
            status_code=404,
            detail=f"Document '{req.document_id}' not found.",
        )

    # Update the stored result
    status_map = {
        "approve": "verified",
        "reject": "rejected",
        "request_reupload": "reupload_requested",
    }
    existing["status"] = status_map[req.decision]
    existing["manual_review"] = {
        "reviewer": req.reviewer_name,
        "decision": req.decision,
        "notes": req.notes,
    }
    save_result(req.document_id, existing)

    return JSONResponse(
        status_code=200,
        content={
            "document_id": req.document_id,
            "new_status": existing["status"],
            "message": {
                "en": f"Document has been {req.decision}d by {req.reviewer_name}.",
                "hi": f"दस्तावेज़ {req.reviewer_name} द्वारा {req.decision} किया गया।",
                "mr": f"दस्तऐवज {req.reviewer_name} द्वारे {req.decision} केले.",
            },
        },
    )