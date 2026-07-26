# cleanup_duplicates.py — run once: python cleanup_duplicates.py

import sys, os, json, hashlib
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Add project root to path so backend imports work
from backend.database.document_store import (
    RESULTS_DIR,
    compute_fingerprint,
    save_redirect,
)

def cleanup():
    print("Scanning for duplicate land records...")

    seen: dict[str, str] = {}   # fingerprint → first request_id
    duplicates_found = 0
    redirects_created = 0

    # Sort by created_at so the OLDEST is kept as the canonical record
    all_files = sorted(
        [f for f in RESULTS_DIR.glob("*.json") if "redirect" not in f.name],
        key=lambda f: f.stat().st_mtime,
    )

    for fpath in all_files:
        try:
            data = json.loads(fpath.read_text(encoding="utf-8"))
        except Exception:
            continue

        if data.get("is_redirect"):
            continue

        doc_type   = data.get("document_type", "")
        request_id = data.get("request_id", fpath.stem)

        # Get extracted_fields and inject raw_text if available
        extracted = data.get("extracted_fields", {}) or {}
        ocr_info  = data.get("ocr", {}) or {}
        if "raw_text" not in extracted and ocr_info.get("raw_text"):
            extracted["raw_text"] = ocr_info["raw_text"]

        fingerprint = compute_fingerprint(doc_type, extracted)

        if not fingerprint:
            print(f"  SKIP (no fingerprint): {fpath.name}")
            continue

        if fingerprint in seen:
            original_id = seen[fingerprint]
            print(f"  DUPLICATE: {request_id} → original: {original_id}")
            # Write redirect stub
            redirect_path = RESULTS_DIR / f"{request_id}.json"
            stub = {
                "request_id":          request_id,
                "is_redirect":         True,
                "original_request_id": original_id,
            }
            redirect_path.write_text(json.dumps(stub, indent=2), encoding="utf-8")
            redirects_created += 1
            duplicates_found  += 1
        else:
            seen[fingerprint] = request_id
            print(f"  KEEP:      {request_id} ({doc_type})")

    print(f"\nDone. Duplicates found: {duplicates_found}, Redirects created: {redirects_created}")
    print("Refresh the admin dashboard to see the result.")


if __name__ == "__main__":
    cleanup()